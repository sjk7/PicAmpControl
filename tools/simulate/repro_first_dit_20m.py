#!/usr/bin/env python3
"""Smallest failing repro: key down, inject 14000 kHz, expect current_band == 4 (20m).

Isolates the FirstDit clause (b) failure ("the 20m first burst was never classified") with no
phases, no clauses and no invariants - just boot, PTT low, inject one frequency, and read the
classifier. Run:

    python3 tools/simulate/repro_first_dit_20m.py

Exit 0 when the band classified 20m; exit 1 when it did not (the current failure).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("PICAMP_DEVICE", "PIC18F47Q10")

import trace_ptt_sequence as t  # noqa: E402
import platform_process as procutil  # noqa: E402

FREQ_KHZ = 14000          # 20m
EXPECTED_BAND = "4"       # BAND_20M
COUNTS = FREQ_KHZ * 1000 // 400   # inverse of the firmware's pulses*2/5 scaling

# Fewer prints per sample than the full harness: ADC pins are stimulus-only, so drop them.
t.ADC_PINS = []


def sample_lines() -> str:
    return "\n".join([f"print pin {p}" for p in t.PINS] +
                     [f"print {v}" for v in t.STATE_VARS])


def inject_atomic() -> str:
    """Halt Timer1, write both bytes, restart - the merged suite's write_tmr1_count pattern."""
    return "\n".join([
        "write T1CON 0x26",
        f"write TMR1L 0x{COUNTS & 0xFF:02X}",
        f"write TMR1H 0x{(COUNTS >> 8) & 0xFF:02X}",
        "write T1CON 0x27",
    ])


def selected_pin(sample) -> int:
    """Index of the single high band-select pin (1..6), or 0 when none is selected."""
    for index, pin in enumerate(t.BAND_PINS, 1):
        if sample[1][pin] == 1:
            return index
    return 0


def write_graph(samples, path: Path) -> bool:
    """Render a timing diagram; shade the injection window red where the failure is detected."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("repro: matplotlib not installed; skipping the timing diagram")
        return False

    times = [s[0] * t.SECONDS_PER_INSTRUCTION * 1000 for s in samples]
    rows = [
        # Raw pin level: PTT is ACTIVE LOW, so the trace DROPS to 0 at key-down.
        ("RC0 / PTT (active low: 0 = keyed)", [int(s[1]["RC0"]) for s in samples]),
        ("band relay (RD2..RD7 -> 1..6)", [selected_pin(s) for s in samples]),
        ("current_band", [int(s[2].get("g_fc_status.current_band") or 0) for s in samples]),
        ("frequency_khz", [int(s[2].get("g_fc_status.frequency_khz") or 0) for s in samples]),
        ("bypass snoop", [1 if s[2].get("g_snoop_active") == "true" else 0 for s in samples]),
        ("sequence stage", [int(s[2].get("g_sequence_stage") or 0) for s in samples]),
    ]
    fig, axes = plt.subplots(len(rows), 1, sharex=True, figsize=(11, 9))
    for ax, (label, values) in zip(axes, rows):
        ax.step(times, values, where="post", color="#1e88e5")
        ax.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=8)
        ax.grid(True, alpha=0.3)
    axes[3].axhline(FREQ_KHZ, color="green", linestyle=":", alpha=0.7)
    axes[3].annotate(f"injected {FREQ_KHZ}", (times[len(times) // 2], FREQ_KHZ),
                     xytext=(0, 4), textcoords="offset points", fontsize=7, color="green")

    # The injection window: every keyed sample. This is where the 14000 kHz should be measured and
    # 20m (band 4) selected - it is not, so shade it RED and label the observed failure.
    keyed = [i for i, s in enumerate(samples) if s[2].get("g_ptt_active") == "true"]
    if keyed:
        start, end = times[keyed[0]], times[keyed[-1]]
        for ax in axes:
            ax.axvspan(start, end, color="red", alpha=0.15)
        seen = sorted({s[2].get("g_fc_status.frequency_khz") for s in samples[keyed[0]:]})
        last_band = samples[-1][2].get("g_fc_status.current_band")
        axes[0].annotate(
            f"FAIL (red): injected {FREQ_KHZ} kHz but freq_khz read {seen}, "
            f"current_band={last_band} (never {EXPECTED_BAND})",
            xy=(start, 1), xytext=(6, 34), textcoords="offset points",
            fontsize=8, color="red", fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="red"))

    axes[-1].set_xlabel("time (ms, approx)")
    fig.suptitle("repro_first_dit_20m: key down + inject 14000 kHz (20m)", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True


def main() -> int:
    script = "\n".join([
        f"device {t.DEVICE}", "hwtool sim", f"program {t.ELF_PATH}",
        # Safe idle stimulus (no SWR, mid-scale NTC, no current/overdrive/drain, encoder released).
        "write pin RA0 0v", "write pin RA1 0v", "write pin RA2 0v", "write pin RA3 0v",
        "write pin RA5 2.5v", "write pin RB1 0v", "write pin RB2 0v", "write pin RB3 0v",
        "write pin RB4 0v", "write pin RC2 5v", "write pin RB0 5v", "write pin RB6 5v",
        # Wait out the 1000 ms startup inhibit (PTT is ignored until it clears).
        t.stepi(1200), sample_lines(),
        "write pin RC0 0v",          # PTT asserted (active low)
        t.stepi(100), sample_lines(),   # let the main loop latch PTT (and clear the comp reset)
        # Hold the injected 20m across the firmware's 10 ms gate, sampling after each gate.
        f"{inject_atomic()}\n{t.stepi(10)}\n{sample_lines()}",
        f"{inject_atomic()}\n{t.stepi(10)}\n{sample_lines()}",
        f"{inject_atomic()}\n{t.stepi(10)}\n{sample_lines()}",
        f"{inject_atomic()}\n{t.stepi(10)}\n{sample_lines()}",
        "quit",
    ])

    raw = t.run_mdb(t.find_mdb(), script)
    samples = t.parse_trace(raw)
    if not samples:
        dump = Path(procutil.temp_dir()) / "repro_first_dit_20m_raw.txt"
        dump.write_text(raw, encoding="utf-8", errors="replace")
        print(f"repro: no samples parsed; raw transcript ({len(raw)} bytes) -> {dump}")
        print("repro: raw tail follows")
        print(raw[-1500:])
        return 2

    graph_path = ROOT / "_build" / "My_Pic_Project" / "sim" / "graphs" / "repro_first_dit_20m.png"
    if write_graph(samples, graph_path):
        print(f"repro: timing diagram -> {graph_path}")

    last = samples[-1]
    band = last[2].get("g_fc_status.current_band")
    freq = last[2].get("g_fc_status.frequency_khz")
    locked = last[2].get("g_fc_status.band_locked")
    ptt = last[2].get("g_ptt_active")
    seen = sorted({s[2].get("g_fc_status.frequency_khz") for s in samples
                   if s[2].get("g_ptt_active") == "true"})
    print(f"repro_first_dit_20m: injected {FREQ_KHZ} kHz -> freq_khz={freq} "
          f"current_band={band} locked={locked} ptt_active={ptt} (expected band {EXPECTED_BAND})")
    print(f"repro: frequencies seen while PTT active: {seen}")
    if ptt != "true":
        print("repro: PTT did not latch - the repro is not exercising the classifier")
        return 2
    if band == EXPECTED_BAND:
        print("repro: PASS - 20m classified")
        return 0
    print(f"repro: FAIL - the {FREQ_KHZ} kHz burst did not classify as 20m")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
