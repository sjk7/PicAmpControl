#!/usr/bin/env python3
"""Positive control: can mdb stimulus reach the firmware's own view of a pin on Q10?

Why this exists
---------------
The Q10 suite reports **0 keyed runs** - PTT is never seen. That is the same signature the skill
records for the abandoned 18877 attempt, and the skill's own rule is that a negative simulator
finding needs a **positive control**: without one, "the firmware never sees PTT" and "the test
cannot assert PTT" are indistinguishable.

The Q10 boot test already produced one suspicious result in this area: `write pin RA6 high` was
accepted and echoed, yet the pin read back as `Ain` regardless. So this test settles the question
for the pin that actually matters - RC0, INPUT_PTT - with the smallest possible experiment:

  1. read PORTC (what the firmware sees) and LATC (what is driven)
  2. `write pin RC0 0v`   (assert PTT: the line is active-low)
  3. read PORTC and LATC again

If PORTC bit 0 goes to 0, mdb stimulus reaches the firmware and the suite's 0-keyed-runs result is
a genuine firmware finding. If PORTC does not change, the stimulus is inert and the Q10 suite
result is a test artefact that must not be reported as a firmware defect.

Run: python tools/simulate/test_stimulus_positive_control.py
Writes its transcript and verdict to files; exits non-zero if the control is inconclusive.
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

# RC0 is INPUT_PTT. It is an input at reset, and the firmware enables its weak pull-up
# (WPUCbits.WPUC0 = 1), so the idle read is 1 and an assert should read 0.
PIN = "RC0"
PORT_REG = "PORTC"
TRIS_REG = "TRISC"
ANSEL_REG = "ANSELC"


def build_script() -> str:
    return "\n".join([
        f"device {DEVICE}",
        "hwtool sim",
        f"program {ELF_PATH}",
        # Let the firmware run far enough to have configured ports and pull-ups.
        "Stepi 200000",
        f"print {PORT_REG}",
        f"print {TRIS_REG}",
        f"print {ANSEL_REG}",
        f"print pin {PIN}",
        # Assert PTT (active-low) and give the firmware a step or two to sample it.
        f"write pin {PIN} low",
        "Stepi 20000",
        f"print {PORT_REG}",
        f"print pin {PIN}",
        # Release it again.
        f"write pin {PIN} high",
        "Stepi 20000",
        f"print {PORT_REG}",
        f"print pin {PIN}",
        "quit",
    ]) + "\n"


def reads(text: str):
    """Pull the ordered (PORTC, pin-block) readings out of the transcript."""
    out = []
    lines = text.splitlines()
    for index, raw in enumerate(lines):
        if raw.strip() == f"print {PORT_REG}":
            for follow in lines[index + 1:index + 4]:
                matched = re.match(r"^PORTC=(\d+)$", follow.strip())
                if matched:
                    out.append(("PORTC", int(matched.group(1))))
                    break
        elif raw.strip() == f"print pin {PIN}":
            for follow in lines[index + 1:index + 4]:
                matched = re.match(r"^RC0\s+\S+\s+(HIGH|LOW)\b", follow.strip())
                if matched:
                    out.append(("pin", matched.group(1)))
                    break
    return out


def main() -> int:
    if not ELF_PATH.exists():
        sys.exit(f"error: {ELF_PATH} not found - build the {DEVICE} firmware first")

    script = build_script()
    with tempfile.NamedTemporaryFile("w", suffix=".mdb", delete=False, newline="\n") as handle:
        handle.write(script)
        script_path = handle.name
    mdb = procutil.find_mdb()
    proc = subprocess.run([str(mdb), script_path], capture_output=True, text=True, timeout=900,
                          stdin=subprocess.DEVNULL, **procutil.isolated_spawn_kwargs())
    os.unlink(script_path)

    transcript = (proc.stdout or "") + (proc.stderr or "")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "stimulus_control_mdb.log").write_text(transcript, encoding="utf-8",
                                                      errors="replace")

    reading = reads(transcript)
    report = [f"device={DEVICE}", f"elf={ELF_PATH}", ""]
    for kind, value in reading:
        report.append(f"  {kind} = {value}")

    ports = [v for k, v in reading if k == "PORTC"]
    pins = [v for k, v in reading if k == "pin"]
    report.append("")
    report.append(f"PORTC readings: {ports}")
    report.append(f"pin readings:   {pins}")

    verdict = "INCONCLUSIVE"
    if len(ports) >= 3:
        idle, asserted, released = ports[0], ports[1], ports[2]
        # RC0 is bit 0 of PORTC. (An earlier revision read bit 1 and so reported "inert" from a
        # 229 -> 228 -> 229 transition that was in fact a perfect demonstration that the stimulus
        # works - the arithmetic was wrong, not the experiment.)
        bit = 0
        idle_bit = (idle >> bit) & 1
        asserted_bit = (asserted >> bit) & 1
        released_bit = (released >> bit) & 1
        report.append(f"RC0 bit: idle={idle_bit} asserted={asserted_bit} released={released_bit}")
        if idle_bit == 1 and asserted_bit == 0 and released_bit == 1:
            verdict = "STIMULUS-WORKS"
            report.append("mdb pin stimulus DOES reach the firmware: asserting RC0 low changed the "
                          "value the firmware reads, and releasing it restored the value. A "
                          "0-keyed-runs result on Q10 is therefore a genuine firmware finding, "
                          "not a test artefact.")
        elif idle_bit == 1 and asserted_bit == 1:
            verdict = "STIMULUS-INERT"
            report.append("Asserting RC0 low did NOT change what the firmware reads. mdb pin "
                          "stimulus does not reach this pin on this device, so a 0-keyed-runs "
                          "Q10 result must NOT be reported as a firmware defect until the "
                          "stimulus method is replaced.")
        else:
            verdict = "INCONCLUSIVE"
            report.append(f"Unrecognised pattern idle={idle_bit} asserted={asserted_bit} "
                          f"released={released_bit}; inspect the transcript before concluding.")

    report.append("")
    report.append(f"VERDICT {verdict}")
    (OUT_DIR / "stimulus_control_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    return 0 if verdict == "STIMULUS-WORKS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
