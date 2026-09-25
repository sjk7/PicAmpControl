#!/usr/bin/env python3
"""Smallest failing repro: PTT release never reaches sequence stage 4.

Isolates the merged suite's *base* (plain PTT) scenario failure, which reports

    AssertionError: release did not enter stage 4

in `validate_sequence()`. The suite's own trace shows why: at 5 ms sampling the firmware appears to
jump from stage 3 straight to stage 5 and then 0, so no sample ever reads stage 4.

This repro does the same thing the base scenario does - boot, clear the startup inhibit, establish
40m while UNKEYED, key with 40m held, then release with 40m held - but samples the RELEASE at 1 ms
instead of 5 ms, so a short stage cannot hide between samples. It writes a CSV and a timing diagram.

Run through the watchdog (never directly, never judged from the terminal):

    python3 tools/simulate/run_suite_with_watchdog.py --test repro-release --log /tmp/repro_rel.log

Exit 0 when a stage-4 sample is observed after PTT release; exit 1 when it is not (the current
failure); exit 2 when PTT never latched, i.e. the repro is not exercising the release at all.
"""
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("PICAMP_DEVICE", "PIC18F47Q10")

import trace_ptt_sequence as t  # noqa: E402
import platform_process as procutil  # noqa: E402

FREQ_KHZ = 7000           # 40m - the band the base scenario establishes in its preflight
COUNTS = FREQ_KHZ * 1000 // 400           # inverse of the firmware's pulses*2/5 scaling
SETTLE_CHUNKS = 4         # 4 x 10 ms gates to clear the ~1000 ms startup inhibit and settle 40m
PREFLIGHT_CHUNKS = 4      # 4 x 10 ms unkeyed gates to establish the band before keying
KEY_CHUNKS = 40           # 40 x 5 ms  = 200 ms keyed (the stage 3 engage takes ~110 ms)
RELEASE_CHUNKS = 40       # 40 x 1 ms  =  40 ms released, sampled finely enough to catch stage 4

# Fewer prints per sample than the full harness: ADC pins are stimulus-only, so drop them, and
# keep only the state the release can be judged from (mdb output is the run's wall-clock cost).
t.ADC_PINS = []
t.STATE_VARS = [
    "g_startup_inhibit", "g_ptt_active", "g_sequence_stage", "g_state",
    "g_fc_status.current_band", "g_fc_status.band_locked", "g_fc_status.frequency_khz",
    "g_snoop_active",
]


def sample_lines() -> str:
    return "\n".join([f"print pin {p}" for p in t.PINS] +
                     [f"print {v}" for v in t.STATE_VARS])


def inject_atomic() -> str:
    """Halt Timer1, write both bytes, restart.

    Byte ORDER matters: T1CON 0x27 leaves RD16 enabled, so a write to TMR1H is buffered and only
    committed when TMR1L is written. L-then-H drops the high byte (0x445C -> 0x005C).
    """
    return "\n".join([
        "write T1CON 0x26",
        f"write TMR1H 0x{(COUNTS >> 8) & 0xFF:02X}",
        f"write TMR1L 0x{COUNTS & 0xFF:02X}",
        "write T1CON 0x27",
    ])


def hold(ms: int, count: int) -> str:
    """`count` samples at `ms` apart, with the RF held present throughout."""
    return "\n".join(f"{inject_atomic()}\n{t.stepi(ms)}\n{sample_lines()}" for _ in range(count))


def write_csv(samples, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_ms", "RC0_PTT_active_low", "g_ptt_active", "g_sequence_stage",
                         "RC5_RELAYS", "RC6_TX_VCC", "RC7_TX_BIAS", "current_band",
                         "frequency_khz", "band_locked", "g_state"])
        for sample in samples:
            pins, state = sample[1], sample[2]
            writer.writerow([
                f"{sample[0] * t.SECONDS_PER_INSTRUCTION * 1000:.3f}",
                pins["RC0"], state.get("g_ptt_active"), state.get("g_sequence_stage"),
                pins["RC5"], pins["RC6"], pins["RC7"],
                state.get("g_fc_status.current_band"), state.get("g_fc_status.frequency_khz"),
                state.get("g_fc_status.band_locked"), state.get("g_state"),
            ])


def write_graph(samples, path: Path, release_at: int | None, stage4_seen: bool) -> bool:
    """Render a timing diagram; shade the release window red when stage 4 is never sampled."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("repro: matplotlib not installed; skipping the timing diagram")
        return False

    times = [s[0] * t.SECONDS_PER_INSTRUCTION * 1000 for s in samples]
    rows = [
        # Raw pin level: PTT is ACTIVE LOW, so the trace DROPS to 0 at key-down and RISES on release.
        ("RC0 / PTT (active low: 0 = keyed)", [int(s[1]["RC0"]) for s in samples]),
        ("sequence stage", [int(s[2].get("g_sequence_stage") or 0) for s in samples]),
        ("RC5 RELAYS", [int(s[1]["RC5"]) for s in samples]),
        ("RC6 TX_VCC", [int(s[1]["RC6"]) for s in samples]),
        ("RC7 TX_BIAS", [int(s[1]["RC7"]) for s in samples]),
        ("current_band", [int(s[2].get("g_fc_status.current_band") or 0) for s in samples]),
    ]
    fig, axes = plt.subplots(len(rows), 1, sharex=True, figsize=(11, 9))
    for ax, (label, values) in zip(axes, rows):
        ax.step(times, values, where="post", color="#1e88e5")
        ax.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=8)
        ax.grid(True, alpha=0.3)

    # Zoom to the release window: the ~1.2 s startup wait would otherwise squash the stages into a
    # sliver. Release is where RC0/PTT rises back to 1 after having been keyed.
    if release_at is not None:
        axes[-1].set_xlim(times[release_at] - 60, times[-1] + 10)
        for ax in axes:
            ax.axvspan(times[release_at], times[-1],
                       color="green" if stage4_seen else "red", alpha=0.15)
        note = ("stage 4 WAS sampled during release (expected)" if stage4_seen else
                "FAIL (red): release never sampled sequence stage 4 - the trace goes "
                "3 -> 5 -> 0")
        axes[1].annotate(note, xy=(times[release_at], 4), xytext=(6, 30),
                         textcoords="offset points", fontsize=8,
                         color="green" if stage4_seen else "red", fontweight="bold",
                         arrowprops=dict(arrowstyle="->",
                                         color="green" if stage4_seen else "red"))
        for stage in (4, 5):
            axes[1].axhline(stage, color="grey", linestyle=":", alpha=0.5)

    axes[-1].set_xlabel("time (ms, approx)")
    fig.suptitle(f"repro_release_stage4: key then release on {FREQ_KHZ} kHz, 1 ms sampling",
                 y=0.995)
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
        # Clear the ~1000 ms startup inhibit (PTT is ignored until it clears), then establish 40m
        # while UNKEYED, exactly as the base scenario does.
        t.stepi(1200), sample_lines(),
        "write pin RC0 5v",          # PTT idle (active low)
        hold(10, SETTLE_CHUNKS),
        hold(10, PREFLIGHT_CHUNKS),
        # Key: RF follows the key, so hold 40m present for the whole keyed window.
        "write pin RC0 0v",
        hold(5, KEY_CHUNKS),
        # Release, still holding 40m present, and sample at 1 ms so a short stage cannot be missed.
        "write pin RC0 5v",
        hold(1, RELEASE_CHUNKS),
        "quit",
    ])

    raw = t.run_mdb(t.find_mdb(), script)
    samples = t.parse_trace(raw)
    if not samples:
        dump = Path(procutil.temp_dir()) / "repro_release_stage4_raw.txt"
        dump.write_text(raw, encoding="utf-8", errors="replace")
        print(f"repro: no samples parsed; raw transcript ({len(raw)} bytes) -> {dump}")
        print("repro: raw tail follows")
        print(raw[-1500:])
        return 2

    sim_dir = ROOT / "_build" / "My_Pic_Project" / "sim"
    csv_path = sim_dir / "csv" / "repro_release_stage4.csv"
    graph_path = sim_dir / "graphs" / "repro_release_stage4.png"
    write_csv(samples, csv_path)

    keyed = [i for i, s in enumerate(samples) if s[2].get("g_ptt_active") == "true"]
    release_at = None
    release = []
    if keyed:
        release_at = keyed[-1] + 1
        release = samples[release_at:]

    stages = [s[2].get("g_sequence_stage") for s in release]
    # The ordered stage transitions across the release, so "3 -> 5 -> 0" is visible in the log.
    transitions = [stages[0]] if stages else []
    for stage in stages[1:]:
        if stage != transitions[-1]:
            transitions.append(stage)
    stage4 = [s for s in release if s[2].get("g_sequence_stage") == "4"]

    if write_graph(samples, graph_path, release_at, bool(stage4)):
        print(f"repro: timing diagram -> {graph_path}")
    print(f"repro: trace csv      -> {csv_path}")

    if not keyed:
        print("repro: PTT never latched - the repro is not exercising the release")
        return 2
    print(f"repro: keyed samples={len(keyed)} release samples={len(release)}")
    print(f"repro: release stage transitions: {' -> '.join(str(s) for s in transitions)}")
    print("repro: release window (t_ms, ptt, stage, RC5, RC6, RC7, band): " +
          " | ".join(f"{s[0] * t.SECONDS_PER_INSTRUCTION * 1000:.0f},{s[2].get('g_ptt_active')},"
                     f"{s[2].get('g_sequence_stage')},{s[1]['RC5']},{s[1]['RC6']},{s[1]['RC7']},"
                     f"{s[2].get('g_fc_status.current_band')}" for s in release[:12]))
    if stage4:
        first = stage4[0]
        print(f"repro: PASS - stage 4 sampled at "
              f"{first[0] * t.SECONDS_PER_INSTRUCTION * 1000:.0f} ms "
              f"({len(stage4)} stage-4 samples)")
        return 0
    print("repro: FAIL - the release never sampled sequence stage 4 "
          f"(observed transitions: {' -> '.join(str(s) for s in transitions)})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
