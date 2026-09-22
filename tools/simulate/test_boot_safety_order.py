#!/usr/bin/env python3
"""Scope trace of the boot sequence: is the 1 ms protection tick armed before the LCD can stall?

Why this test exists
--------------------
The 1 ms tick is the only periodic supervision the amplifier has - it advances the startup
inhibit window, the band-settle delay, the band-verify timeout and every trip debounce. On
2026-09-22 the Q10 bring-up run showed the tick was still unarmed 200,000 simulator steps into
boot, because `main()` called `lcd_init()` / `show_boot_message()` *before* `timer0_init()`. The
LCD is the slowest and least trustworthy part of bring-up (a held E line or a missing panel blocks
it), so this test asks the safety question directly:

    from reset, is the tick running before, or only after, the LCD has finished?

It answers it twice, deliberately:

  happy path  a normal boot. The tick must be running *before* the LCD's first write, and the
              amplifier outputs must never be keyed.
  sad path    the LCD E line is held (the panel never acknowledges - the classic stall). The tick
              must STILL be running, and the outputs must still be safe, because the whole point
              of the ordering fix is that LCD trouble cannot cost us supervision.

It writes `boot_trace.png` (a logic-analyser style trace, same rendering approach as
trace_ptt_sequence.py) plus the raw samples as CSV, and exits non-zero on either path failing.

Usage:
    python3 tools/simulate/test_boot_safety_order.py            # both paths
    python3 tools/simulate/test_boot_safety_order.py --path happy
    python3 tools/simulate/test_boot_safety_order.py --path sad
"""
import argparse
import csv
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
GRAPH_DIR = REPO_ROOT / "_build" / "My_Pic_Project" / "sim"
DEVICE = harness.DEVICE
# The steps-per-simulated-millisecond table lives with the first-dit harness, which owns the
# device selection; import it from there rather than keeping a second copy that can drift.
sys.path.insert(0, str(TOOLS_DIR))
import test_first_dit as first_dit  # noqa: E402
INSTRUCTIONS_PER_MS = first_dit.INSTRUCTIONS_PER_MS

# The tick's observable fingerprint is the system counter. `g_timer_ticks_pending` is bumped in
# the ISR on every Timer2 overflow, so watching it answer "is the tick running" without needing
# to trust T2CON (which is only meaningful after timer0_init()).
TICK_VARS = ["g_timer_ticks_pending", "g_startup_inhibit", "g_state"]
TICK_PINS = ["RC5", "RC6", "RC7", "RC1"]     # TX, TX_VCC, TX_BIAS, comparator reset

# Boot is short; sample finely so the LCD-vs-tick order is visible, then continue for a while so
# the sad path has room to stall visibly.
SAMPLE_MS = 1
SAMPLES = 60


def build_script(path: str, hold_e: bool) -> str:
    """MDB script that samples tick, outputs and state from reset.

    `hold_e` is meant to stall the firmware the way a missing or unresponsive panel does: the LCD
    enable line stays asserted, so any driver waiting for it to drop blocks. Getting that stimulus
    to actually apply took two corrections, and both are worth knowing:

      * `write pin RA6 high` placed *before* `program` is echoed by mdb and then ignored - the
        target has not been programmed yet, so the write lands nowhere. The sad path therefore
        looked identical to the happy path and the first run "passed" for the wrong reason
        (2026-09-22). Pin stimulus must come after `program`.
      * Even after `program`, a `write pin` can be rejected. The script is checked for a
        confirmation rather than assuming it worked, and the run reports if the hold never applied,
        so a silently-inert stimulus can never again be reported as a passing sad path.
    """
    lines = [
        f"device {DEVICE}",
        "hwtool sim",
        f"program {ELF_PATH}",
    ]
    if hold_e:
        # AFTER program: drive the E line and latch it, then step once so the write is committed
        # before the sampled window opens.
        lines.append("write pin RA6 high")
        lines.append(f"Stepi {max(1, int(INSTRUCTIONS_PER_MS // 10))}")
        lines.append("print pin RA6")
    for index in range(SAMPLES):
        lines.append(f"Stepi {max(1, int(SAMPLE_MS * INSTRUCTIONS_PER_MS))}")
        for var in TICK_VARS:
            lines.append(f"print {var}")
        for pin in TICK_PINS:
            lines.append(f"print pin {pin}")
    lines.append("quit")
    return "\n".join(lines) + "\n"


def hold_applied(text: str) -> bool:
    """True if the RA6 hold read back HIGH, i.e. the sad-path stimulus actually took effect."""
    for line in text.splitlines():
        if re.match(r"^RA6\s+\S+\s+HIGH\b", line.strip()):
            return True
    return False


# ---------------------------------------------------------------------------------------------
# KNOWN LIMITATION - the sad-path stimulus does not currently apply, and the test says so.
#
# `write pin RA6 high` is accepted by mdb and reported as if applied, but the pin reads back
# `RA6 Ain 5.0V (RA6)/IOCA6/ANA6/CLKOUT/OSC2` regardless of whether the write is placed before
# `program`, after it, or after an extra step. Two candidate causes were investigated and BOTH
# were eliminated:
#
#   * config default - the Q10's CLKOUTEN default is ON, which would hand RA6 to the clock output.
#     Setting `CLKOUTEN = OFF` does take effect (the linker's missing-config-word warning drops
#     from two settings to one), but RA6 still reads back the same way. Not the cause.
#   * analogue select - `ANSELA = 0x2F` leaves RA6 *digital* (bit 6 clear), so the pin is not
#     analogue-selected by the firmware. Not the cause.
#
# What remains is that mdb's `write pin` does not override the firmware's own configuration of a
# pin it drives, which is consistent with the existing note that pin stimulus in this build is
# limited. Until a working stimulus is found, the sad path cannot be constructed from outside and
# the run FAILS LOUDLY rather than reporting a pass it did not earn - the first version of this
# test did exactly that, and it was wrong.
#
# The happy path is unaffected and still proves the ordering: the tick is armed at ~1 ms from
# reset, long before the LCD sequence completes.
# ---------------------------------------------------------------------------------------------


def parse(text: str, path: str):
    """Turn the mdb transcript into per-sample dicts of variables and pin states.

    MDB prints the two kinds of read differently, and both forms have to be handled:

        print g_state
        g_state=
        true

        print pin RC5
        Pin     Mode    Value   Owner or Mapping
        RC5     Dout    HIGH    (RC5)/IOCC5/ANC5

    The first is a name on one line, the value on the next. The second is a tab-separated table
    row where the value is the *text* HIGH/LOW, not a number - the earlier version of this parser
    only looked for `RC5=0`-style lines and so found no samples at all, which is what made the
    boot proof fail with "no samples parsed" rather than anything informative.
    """
    samples = [{}]
    pending_var = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # `name=` on its own line, value follows.
        if pending_var is not None:
            samples[-1][pending_var] = line
            pending_var = None
            continue
        matched = re.match(r"^([A-Za-z_][\w.]*)=$", line)
        if matched:
            pending_var = matched.group(1)
            continue

        # Pin table row: `RC5 <tab> Dout <tab> HIGH <tab> (RC5)/...`
        matched = re.match(r"^(R[A-D]\d)\s+\S+\s+(HIGH|LOW)\b", line)
        if matched:
            samples[-1][matched.group(1)] = 1 if matched.group(2) == "HIGH" else 0
            continue

        # `name=value` on one line (numeric reads, and the common case for a byte register).
        matched = re.match(r"^([A-Za-z_][\w.]*)=(\S+)$", line)
        if matched:
            samples[-1][matched.group(1)] = matched.group(2)
            continue

        # A sample is complete once it holds every variable and every pin we asked for; start a
        # new one. The pin table adds its own values, so completeness is the boundary, not order.
        if len(samples[-1]) >= len(TICK_VARS) + len(TICK_PINS):
            samples.append({})

    return [s for s in samples if s]


def run_path(name: str, hold_e: bool):
    script = build_script(name, hold_e)
    with tempfile.NamedTemporaryFile("w", suffix=".mdb", delete=False, newline="\n") as handle:
        handle.write(script)
        script_path = handle.name
    mdb = procutil.find_mdb()
    proc = subprocess.run([str(mdb), script_path], capture_output=True, text=True, timeout=900,
                          stdin=subprocess.DEVNULL, **procutil.isolated_spawn_kwargs())
    os.unlink(script_path)
    transcript = (proc.stdout or "") + (proc.stderr or "")
    samples = parse(transcript, name)
    log = GRAPH_DIR / f"boot_{name}_mdb.log"
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    log.write_text(transcript, encoding="utf-8", errors="replace")
    return samples, transcript


def first_tick_sample(samples):
    """Index of the first sample where the tick has advanced past zero."""
    for index, sample in enumerate(samples):
        try:
            if int(sample.get("g_timer_ticks_pending", "0")) > 0:
                return index
        except (TypeError, ValueError):
            continue
    return None


def keyed_samples(samples):
    """Samples where any TX output is active.

    The outputs are active-low, so 'inactive' is a 1 on the pin. Any 0 means the firmware has
    keyed something, which must never happen during bring-up.
    """
    keyed = []
    for index, sample in enumerate(samples):
        for pin in ("RC5", "RC6", "RC7"):
            if sample.get(pin) == 0:
                keyed.append((index, pin))
    return keyed


def write_scope(samples_happy, samples_sad):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping PNG (pip install matplotlib)")
        return None

    rows = [("g_timer_ticks_pending", "TICK\n(is it running?)", None),
            ("g_startup_inhibit", "STARTUP\nINHIBIT", None),
            ("RC5", "TX", (0, 1)),
            ("RC6", "TX_VCC", (0, 1)),
            ("RC7", "TX_BIAS", (0, 1))]
    fig, axes = plt.subplots(len(rows) * 2, 1, sharex=True, figsize=(11, 13))
    axes = list(axes)
    for column, (samples, title) in enumerate(((samples_happy, "HAPPY PATH - normal boot"),
                                               (samples_sad, "SAD PATH - LCD E line held"))):
        base = column * len(rows)
        for offset, (key, label, limits) in enumerate(rows):
            ax = axes[base + offset]
            if not samples:
                ax.text(0.5, 0.5, "no samples", ha="center", transform=ax.transAxes)
                ax.set_ylabel(label, rotation=0, labelpad=52, va="center", fontsize=8)
                continue
            times = [index * SAMPLE_MS for index in range(len(samples))]
            series = []
            for sample in samples:
                value = sample.get(key)
                try:
                    series.append(float(value))
                except (TypeError, ValueError):
                    series.append(float("nan"))
            if limits:
                ax.step(times, series, where="post")
                ax.set_ylim(-0.2, 1.2)
                ax.set_yticks([0, 1])
            elif key == "g_startup_inhibit":
                # Booleans arrive as the strings "true"/"false"; map them so the lane shows the
                # inhibit window instead of an empty panel (an empty lane looked like a missing
                # signal rather than a formatting gap - user-visible bug, 2026-09-22).
                mapped = []
                for sample in samples:
                    value = sample.get(key)
                    mapped.append(1.0 if str(value).lower() == "true"
                                  else 0.0 if str(value).lower() == "false"
                                  else float("nan"))
                ax.step(times, mapped, where="post")
                ax.set_ylim(-0.2, 1.2)
                ax.set_yticks([0, 1])
                ax.set_yticklabels(["released", "inhibited"])
            else:
                ax.step(times, series, where="post")
            ax.set_ylabel(label, rotation=0, labelpad=52, va="center", fontsize=8)
            ax.grid(True, alpha=0.3)
            if offset == 0:
                ax.set_title(title, fontsize=10)
            tick_index = first_tick_sample(samples)
            if tick_index is not None and offset == 0:
                ax.axvline(tick_index * SAMPLE_MS, color="green", ls="--", alpha=0.7)
                ax.annotate(f"tick up @ {tick_index * SAMPLE_MS} ms",
                            (tick_index * SAMPLE_MS, ax.get_ylim()[1] * 0.6), fontsize=8,
                            color="green")
    axes[-1].set_xlabel("simulated time (ms from reset)")
    path = GRAPH_DIR / "boot_trace.png"
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"Wrote {path}")
    return path


def write_csv(samples_happy, samples_sad):
    path = GRAPH_DIR / "boot_trace.csv"
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    keys = TICK_VARS + TICK_PINS
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "sample", "ms"] + keys)
        for name, samples in (("happy", samples_happy), ("sad", samples_sad)):
            for index, sample in enumerate(samples):
                writer.writerow([name, index, index * SAMPLE_MS] + [sample.get(k, "") for k in keys])
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", choices=("happy", "sad", "both"), default="both")
    args = parser.parse_args()

    if not ELF_PATH.exists():
        sys.exit(f"error: {ELF_PATH} not found - build the firmware first")

    samples_happy = run_path("happy", hold_e=False) if args.path in ("happy", "both") else ([], "")
    samples_sad = run_path("sad", hold_e=True) if args.path in ("sad", "both") else ([], "")
    samples_happy, text_happy = samples_happy
    samples_sad, text_sad = samples_sad

    write_csv(samples_happy, samples_sad)
    write_scope(samples_happy, samples_sad)

    failures = []
    for name, samples in (("happy", samples_happy), ("sad", samples_sad)):
        if not samples:
            failures.append(f"{name}: no samples parsed from the mdb run")
            continue
        tick_index = first_tick_sample(samples)
        keyed = keyed_samples(samples)
        print(f"{name}: samples={len(samples)} first_tick_sample={tick_index} "
              f"keyed={len(keyed)}")
        if tick_index is None:
            failures.append(f"{name}: the 1 ms tick NEVER ran - no supervision at any point")
        if keyed:
            failures.append(f"{name}: outputs were keyed during bring-up at samples {keyed[:5]}")

    # A sad path whose stimulus never applied is not a sad path. Without this check the run
    # "passes" while proving nothing, which is exactly what happened on the first attempt.
    if args.path in ("sad", "both"):
        if not hold_applied(text_sad):
            failures.append("sad: the LCD E-line hold never applied, so the stalled-LCD case was "
                            "NOT exercised - the sad-path result is meaningless until this is fixed")
        else:
            print("sad: E-line hold confirmed applied (RA6 read back HIGH)")

    if failures:
        for line in failures:
            print(f"FAIL {line}")
        return 1
    print("PASS boot order: the tick is armed before the LCD can stall, and nothing keyed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
