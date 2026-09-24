#!/usr/bin/env python3
"""Where does PTT get lost on the Q10? A minimal, staged probe.

Context: the Q10 Release suite reports **0 keyed runs** in 552 samples. A positive control
(`test_stimulus_positive_control.py`) has since shown that `write pin RC0 low` *does* reach the
firmware - `PORTC` bit 0 flips - so the failure is downstream of the pin and is a genuine firmware
finding. This probe walks that path one stage at a time so the failure has an address instead of a
symptom:

  1. after boot, is the firmware alive and past its startup inhibit?      (g_state, g_startup_inhibit)
  2. with PTT idle, what does the firmware think PTT is?                  (g_ptt_active, PORTC)
  3. assert PTT and step: does the firmware latch it?                     (g_ptt_active)
  4. if latched, does it enter bypass-snoop?                              (g_state, g_snoop_active)

Stages 3 and 4 are the interesting ones. If PTT never latches, the fault is in the sampling or the
pin configuration; if it latches but never snoops, the fault is in the band / startup logic.

Run: python tools/simulate/probe_q10_ptt_path.py
Writes a report and the raw transcript; exits non-zero if the path stalls before snoop.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent.parent
sys.path.insert(0, str(TOOLS_DIR))
import platform_process as procutil  # noqa: E402
import trace_ptt_sequence as harness  # noqa: E402

ELF_PATH = harness.ELF_PATH
DEVICE = harness.DEVICE
OUT_DIR = REPO_ROOT / "_build" / "My_Pic_Project" / "sim"

VARS = ["g_state", "g_startup_inhibit", "g_ptt_active", "g_snoop_active",
        "g_band_established", "g_fault_latched", "g_trip_reason"]

# Physical ADC pins (MDB reads them as voltages) and the firmware's computed globals, which are the
# numbers the trip thresholds are compared against each main-loop pass.
ADC_PINS = ["RA0", "RA1", "RA2", "RA3", "RA5", "RB1", "RB2", "RB3"]
LIVE_VARS = ["g_live_temperature_c", "g_live_current_a", "g_live_overdrive_mw"]
# Trip thresholds straight from the settings struct. Reading them proves whether a trip is
# "threshold loaded as 0/garbage" (the NVM suspicion) versus "genuine reading over a sane limit".
THRESHOLD_VARS = ["g_thresholds.temp_trip_c", "g_thresholds.current_trip_a",
                  "g_thresholds.drain_trip_v", "g_thresholds.overdrive_trip_tenths_w",
                  "g_thresholds.swr1_trip_tenths", "g_thresholds.swr2_trip_tenths"]

# The startup inhibit must expire before PTT can do anything. It is a 1000 ms settle delay counted
# in main-loop passes, and it is counted in SIMULATED time - which on the Q10 is much faster in
# wall-clock terms than the step count suggests:
#
#   Q10 at 64 MHz = 16 MIPS, so one instruction is 62.5 ns.
#   1000 ms needs ~16,000,000 steps.
#
# An earlier revision used 800,000 steps, which is only 50 ms of simulated time - 20x too early.
# The probe then reported "startup inhibit never expired" as a firmware fault, when it was purely
# the probe cutting off before the gate. That wrong conclusion is recorded in the skill; this
# constant is the correction (from the 2026-09-22 blockers note, since deleted - see bugfixes.md
# 2026-09-24).
#
# WARNING - this constant and the harnesses' INSTRUCTIONS_PER_MS disagree by ~10x, and that is
# UNRESOLVED (2026-09-24). The arithmetic above says 1000 ms = 16,000,000 steps at 16 MIPS, but the
# direct probe found the same 1000 ms boundary at ~1.5-1.75M steps, i.e. ~1625 steps per firmware-ms
# (bugfixes.md 2026-09-23). Both cannot be right. Nothing was changed: see the build-test skill.
BOOT_STEPS = 16_500_000


def script() -> str:
    lines = [
        f"device {DEVICE}",
        "hwtool sim",
        f"program {ELF_PATH}",
    ]
    # Drive every analogue input to a safe, in-range value before boot, exactly as the suite does.
    # Without this the ADC pins float and read near full-scale, which trips TEMP and CURRENT by
    # itself - a probe artefact, not a firmware finding. (The first probe run omitted this and
    # reported temp=150C / current=8905A from floating pins.)
    lines += [
        "write pin RA0 0v", "write pin RA1 0v", "write pin RA2 0v", "write pin RA3 0v",
        "write pin RA5 2.5v", "write pin RB1 0v", "write pin RB2 0v", "write pin RB3 0v",
        "write pin RB4 0v", "write pin RC2 5v", "write pin RB0 5v", "write pin RB6 5v",
    ]
    lines.append(f"Stepi {BOOT_STEPS}")
    lines.append("print PORTC")
    lines.append("print ANSELC")
    for var in VARS:
        lines.append(f"print {var}")
    # Thresholds do not change after load_settings(); read them once.
    for var in THRESHOLD_VARS:
        lines.append(f"print {var}")
    # Assert PTT and step; re-read after each step so a latch/trip appearing late is caught.
    lines.append("write pin RC0 low")
    for _ in range(4):
        lines.append(f"Stepi {200_000}")
        lines.append("print PORTC")
        for var in VARS:
            lines.append(f"print {var}")
        for pin in ADC_PINS:
            lines.append(f"print pin {pin}")
        for var in LIVE_VARS:
            lines.append(f"print {var}")
    lines.append("quit")
    return "\n".join(lines) + "\n"


def collect(text: str):
    """Return a list of {var: value} snapshots, one per step, in transcript order.

    MDB prints `print <var>` as `<var>=` on one line and the value on the next, `print PORTC`
    as `PORTC=<decimal>` inline, and `print pin X` as `X  <level|volts>`."""
    blocks = []
    current = {}
    pending = None
    pin_re = re.compile(r"^(R[A-Z]\d+)\s+\S+\s+(?:(HIGH|LOW)|([\d.]+)V)$")
    for raw in text.splitlines():
        line = raw.strip()
        if pending is not None:
            current[pending] = line
            pending = None
            continue
        m = re.match(r"^([A-Za-z_][\w.]*)=$", line)
        if m:
            pending = m.group(1)
            continue
        m = re.match(r"^PORTC=(\d+)$", line)
        if m:
            if current and "PORTC" in current:
                blocks.append(current)
                current = {}
            current["PORTC"] = m.group(1)
            continue
        m = re.match(r"^ANSELC=(\d+)$", line)
        if m:
            current["ANSELC"] = m.group(1)
            continue
        m = pin_re.match(line)
        if m:
            current["pin_" + m.group(1)] = m.group(2) if m.group(2) else m.group(3) + "V"
            continue
    if current:
        blocks.append(current)
    return blocks


def decode_trip_reason(value: str) -> str:
    try:
        bits = int(value)
    except ValueError:
        return value
    names = [name for bit, name in harness.TRIP_REASON_BITS if bits & bit]
    return ("|".join(names) if names else "none") + f" ({bits})"


def main() -> int:
    if not ELF_PATH.exists():
        sys.exit(f"error: {ELF_PATH} not found - build the {DEVICE} firmware first")
    with tempfile.NamedTemporaryFile("w", suffix=".mdb", delete=False, newline="\n") as handle:
        handle.write(script())
        script_path = handle.name
    mdb = procutil.find_mdb()
    proc = subprocess.run([str(mdb), script_path], capture_output=True, text=True, timeout=1800,
                          stdin=subprocess.DEVNULL, **procutil.isolated_spawn_kwargs())
    os.unlink(script_path)
    transcript = (proc.stdout or "") + (proc.stderr or "")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "q10_ptt_probe_mdb.log").write_text(transcript, encoding="utf-8", errors="replace")

    blocks = collect(transcript)
    report = [f"device={DEVICE}", f"elf={ELF_PATH}", f"blocks={len(blocks)}", ""]
    for index, block in enumerate(blocks):
        report.append(f"--- step {index} ---")
        for key in ["PORTC", "ANSELC"] + VARS:
            if key in block:
                report.append(f"    {key:22s} = {block[key]}")
        for key in THRESHOLD_VARS:
            if key in block:
                report.append(f"    {key:22s} = {block[key]}")
        for pin in ADC_PINS:
            if "pin_" + pin in block:
                report.append(f"    pin {pin:20s} = {block['pin_' + pin]}")
        for key in LIVE_VARS:
            if key in block:
                report.append(f"    {key:22s} = {block[key]}")
        if "g_trip_reason" in block:
            report.append(f"    trip reason: {decode_trip_reason(block['g_trip_reason'])}")

    failures = []
    if not blocks:
        failures.append("no readable state blocks - probe itself is broken")
    else:
        first = blocks[0]
        if first.get("g_startup_inhibit") == "true":
            failures.append("stage 1: startup inhibit never expired, so PTT cannot act yet - "
                            "increase BOOT_STEPS or investigate the inhibit timer")
        ptt_latched = any(b.get("g_ptt_active") == "true" for b in blocks[1:])
        snooped = any(b.get("g_snoop_active") == "true" or b.get("g_state") == "6"
                      for b in blocks[1:])
        tripped = any(b.get("g_fault_latched") == "true" or b.get("g_state") == "3"
                      for b in blocks[1:])
        report.append("")
        report.append(f"PTT latched at any step: {ptt_latched}")
        report.append(f"bypass-snoop entered:   {snooped}")
        report.append(f"fault latched / TRIP:   {tripped}")
        if not ptt_latched:
            failures.append("stage 3: PTT never latched. The pin reads correctly under stimulus "
                            "(positive control passes), so the fault is in the firmware's sampling "
                            "of INPUT_PTT or its configuration on this device.")
        elif tripped:
            reason = next((b.get("g_trip_reason") for b in blocks[1:]
                           if b.get("g_fault_latched") == "true"), "0")
            failures.append(f"stage 5: PTT latched, snoop entered, then the amplifier TRIPPED - "
                            f"g_trip_reason = {decode_trip_reason(reason)}. Read the ADC pin and "
                            f"live-value lines in the block above to see which reading crossed "
                            f"which threshold.")
        elif not snooped:
            failures.append("stage 4: PTT latched but bypass-snoop never entered. The fault is "
                            "downstream of the pin: look at the band/startup gating, not at PTT.")

    report.append("")
    report.append("VERDICT " + ("PASS" if not failures else "FAIL"))
    for line in failures:
        report.append(f"  {line}")
    (OUT_DIR / "q10_ptt_probe_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
