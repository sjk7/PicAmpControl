#!/usr/bin/env python3
"""Captures a scope-like trace of PTT/TX/TX_VCC/TX_BIAS pins across a PTT assert/release
cycle by single-stepping the MPLAB X `mdb` simulator and polling pin state at fixed
instruction intervals, then renders a logic-analyzer-style PNG.

Timing is approximate: instruction counts are converted to seconds assuming one
instruction cycle per Stepi step at _XTAL_FREQ/4 (see firmware/include/pin_map.h).
This is close enough to see the shape/order of the sequencer delays, not a cycle-exact
measurement.

Usage:
    python tools/simulate/trace_ptt_sequence.py
Requires: MPLAB X IDE (mdb), and matplotlib (pip install matplotlib) for the PNG output.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HEX_PATH = REPO_ROOT / "out" / "My_Pic_Project" / "default.hex"
DEVICE = "PIC16F18855"
XTAL_FREQ = 32_000_000
SECONDS_PER_INSTRUCTION = 4 / XTAL_FREQ  # approx; 1 instruction cycle = 4 osc clocks

STEP_SIZE = 2000
PHASES = [
    # PTT idle (inactive, active-low), coarsely stepped through the bulk of
    # the ~1s startup-inhibit wait (see g_startup_elapsed_ms in main.c).
    ("steady_coarse", "5v", 22, 180000),  # ~495ms
    # Finer-grained stepping across the 1000ms boundary (with margin for
    # init overhead: lcd_init/adc_init delays before the main loop's ms
    # clock starts) so the ~10ms SETTLE (comparator reset) pulse isn't
    # skipped between samples.
    ("steady_mid", "5v", 402, 20000),  # ~495ms -> ~1500ms, 2.5ms/sample
    ("asserted", "0v", 300, STEP_SIZE),  # PTT pressed; covers both ~20ms sequencer delays
    ("released", "5v", 100, STEP_SIZE),  # PTT released again
]
PINS = ["RC1", "RC0", "RC5", "RC6", "RC7"]
PIN_LABELS = {"RC1": "SETTLE", "RC0": "PTT", "RC5": "TX", "RC6": "TX_VCC", "RC7": "TX_BIAS"}


def find_mdb() -> Path:
    candidates = sorted(Path("C:/Program Files/Microchip/MPLABX").glob("*/mplab_platform/bin/mdb.bat"))
    if not candidates:
        candidates = sorted(Path("/Applications/microchip/mplabx").glob("*/mplab_platform/bin/mdb.sh"))
    if not candidates:
        sys.exit("error: mdb not found. Install MPLAB X IDE.")
    return candidates[-1]


def build_script() -> str:
    lines = [f"device {DEVICE}", "hwtool sim", f"program {HEX_PATH}"]
    # RA5 feeds the NTC temp ADC; left floating it reads ~0 raw, which
    # temperature_c() maps to 150C, latching a false thermal trip that blocks
    # TX for the whole run. Bias it to ~2.5V (a plausible room-temp reading).
    lines.append("write pin RA5 2.5v")
    # SWR fwd/ref, current, overdrive, and drain ADC inputs float otherwise,
    # which can read as spurious power/fault levels and latch a trip that
    # blocks TX; bias them to 0V (idle/no-fault) so PTT is free to sequence.
    for pin in ("RA0", "RA1", "RA2", "RA3", "RB1", "RB2", "RB3"):
        lines.append(f"write pin {pin} 0v")
    # RB4 is the active-high hardware overcurrent-fault input; floating it can
    # read as an asserted fault and latch a trip that blocks TX indefinitely.
    lines.append("write pin RB4 0v")
    for _, level, count, step_size in PHASES:
        lines.append(f"write pin RC0 {level}")
        for _ in range(count):
            lines.append(f"Stepi {step_size}")
            for pin in PINS:
                lines.append(f"print pin {pin}")
    lines.append("quit")
    return "\n".join(lines)


def run_mdb(mdb_path: Path, script: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".mdb", delete=False) as f:
        f.write(script)
        script_path = f.name
    try:
        result = subprocess.run(
            [str(mdb_path), script_path], capture_output=True, text=True, check=False
        )
        return result.stdout + result.stderr
    finally:
        Path(script_path).unlink(missing_ok=True)


PRINT_RE = re.compile(r"^(R[A-Z]\d+)\s+\S+\s+([\d.]+)V", re.MULTILINE)
STEPI_RE = re.compile(r"^Stepi\s+(\d+)")


def parse_trace(output: str):
    """Walks the mdb transcript in order, tracking cumulative instruction count and
    each pin's most-recently-printed value, sampling a full pin snapshot every time all
    5 pins have been reprinted (i.e. once per Stepi block)."""
    samples = []
    instr_count = 0
    pending = {}
    for line in output.splitlines():
        m_stepi = STEPI_RE.match(line.strip())
        if m_stepi:
            instr_count += int(m_stepi.group(1))
            continue
        m = PRINT_RE.match(line.strip())
        if m:
            pin, volts = m.group(1), float(m.group(2))
            pending[pin] = 1 if volts >= 2.5 else 0
            if len(pending) == len(PINS):
                samples.append((instr_count, dict(pending)))
                pending.clear()
    return samples


def main():
    if not HEX_PATH.exists():
        sys.exit(f"error: {HEX_PATH} not found - build firmware first (build_firmware.ps1/.sh)")
    mdb_path = find_mdb()
    script = build_script()
    output = run_mdb(mdb_path, script)
    samples = parse_trace(output)
    if not samples:
        sys.exit("error: no samples parsed from mdb output - dumping raw output:\n" + output[-4000:])

    out_dir = REPO_ROOT / "_build" / "My_Pic_Project" / "sim"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "ptt_trace.csv"
    with open(csv_path, "w") as f:
        f.write("time_s," + ",".join(PIN_LABELS[p] for p in PINS) + "\n")
        for instr_count, vals in samples:
            t = instr_count * SECONDS_PER_INSTRUCTION
            f.write(f"{t:.6f}," + ",".join(str(vals[p]) for p in PINS) + "\n")
    print(f"Wrote {csv_path} ({len(samples)} samples)")

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping PNG (pip install matplotlib)")
        return

    times = [s[0] * SECONDS_PER_INSTRUCTION * 1000 for s in samples]  # ms
    fig, axes = plt.subplots(len(PINS), 1, sharex=True, figsize=(10, 6))
    for ax, pin in zip(axes, PINS):
        values = [s[1][pin] for s in samples]
        ax.step(times, values, where="post")
        ax.set_ylim(-0.2, 1.2)
        ax.set_yticks([0, 1])
        ax.set_ylabel(PIN_LABELS[pin], rotation=0, labelpad=30, va="center")
        ax.grid(True, alpha=0.3)
    axes[0].set_xlim(480, times[-1])  # crop the coarse startup-inhibit wait out of view
    axes[-1].set_xlabel("time (ms, approx)")
    fig.suptitle("PTT assert/release sequencing (simulated)")
    fig.tight_layout()
    png_path = out_dir / "ptt_trace.png"
    fig.savefig(png_path, dpi=120)
    print(f"Wrote {png_path}")


if __name__ == "__main__":
    main()

