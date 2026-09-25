#!/usr/bin/env python3
"""Zoom the base (plain PTT) scenario trace to the keyed window: from PTT falling low onwards.

`trace_ptt_sequence.py` writes `_build/My_Pic_Pic_Project/sim/csv/ptt_trace.csv` on a scenario-0
failure. The whole-run graph squashes the interesting part, so this re-plots it starting at the
PTT falling edge - PTT is ACTIVE LOW, so that edge is where the operator keys the transmitter and
where every band-switch, frequency-sniff and TX-sequencing decision below must be judged.

    python3 tools/simulate/plot_ptt_from_keydown.py

Writes `_build/My_Pic_Project/sim/graphs/ptt_trace_from_keydown.png`.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "_build" / "My_Pic_Project" / "sim" / "csv" / "ptt_trace.csv"
OUT_PATH = ROOT / "_build" / "My_Pic_Project" / "sim" / "graphs" / "ptt_trace_from_keydown.png"

LANES = [
    ("RC0 / PTT (active low: 0 = keyed)", "PTT"),
    ("RC1 SETTLE", "SETTLE"),
    ("RC5 RELAYS", "RELAYS"),
    ("RC6 TX_VCC", "TX_VCC"),
    ("RC7 TX_BIAS", "TX_BIAS"),
    ("band 160m..10m (bit mask)", None),   # built from the six BAND columns
    ("sequence stage", "g_sequence_stage"),
]


def main() -> int:
    if not CSV_PATH.exists():
        print(f"no trace at {CSV_PATH} - run the suite first")
        return 1
    rows = list(csv.DictReader(CSV_PATH.open()))
    if not rows:
        print(f"{CSV_PATH} is empty")
        return 1

    times = [float(r["time_s"]) * 1000 for r in rows]
    keydown = next((i for i in range(1, len(rows))
                    if rows[i - 1]["PTT"] == "1" and rows[i]["PTT"] == "0"), None)
    if keydown is None:
        print("PTT never fell in this trace (active low: keyed = 0)")
        return 1

    band_cols = [c for c in rows[0] if c.startswith("BAND ")]
    band_mask = [sum(1 << k for k, c in enumerate(band_cols) if r[c] == "1") for r in rows]
    values = {
        "PTT": [int(r["PTT"]) for r in rows],
        "SETTLE": [int(r["SETTLE"]) for r in rows],
        "RELAYS": [int(r["RELAYS"]) for r in rows],
        "TX_VCC": [int(r["TX_VCC"]) for r in rows],
        "TX_BIAS": [int(r["TX_BIAS"]) for r in rows],
        "g_sequence_stage": [int(r["g_sequence_stage"]) for r in rows],
        None: band_mask,
    }

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(len(LANES), 1, sharex=True, figsize=(13, 10))
    t0 = times[keydown]
    for ax, (label, key) in zip(axes, LANES):
        ax.step([t - t0 for t in times], values[key], where="post", color="#1565c0")
        ax.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=8)
        ax.grid(True, alpha=0.3)
    axes[0].set_xlim(-20, times[-1] - t0)
    axes[-1].set_xlabel(f"ms since PTT fell low (t={t0:.1f} ms)")

    stages = [int(r["g_sequence_stage"]) for r in rows[keydown:]]
    transitions = [stages[0]] if stages else []
    for stage in stages[1:]:
        if stage != transitions[-1]:
            transitions.append(stage)
    seen4 = 4 in transitions
    axes[6].annotate(
        ("PASS: stage 4 observed during the release" if seen4 else
         "FAIL (red): stage 4 NEVER sampled during the release"),
        xy=(times[keydown] - t0, 4), xytext=(8, 42), textcoords="offset points",
        fontsize=9, fontweight="bold", color="green" if seen4 else "red",
        arrowprops=dict(arrowstyle="->", color="green" if seen4 else "red"))
    fig.suptitle("base scenario from PTT falling low (keyed) - stage sequence: "
                 + " -> ".join(str(s) for s in transitions), y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=120)
    plt.close(fig)
    print(f"keyed graph -> {OUT_PATH}")
    print(f"keydown at t={t0:.1f} ms; stages after the release: "
          + " -> ".join(str(s) for s in transitions))
    return 0 if seen4 else 1


if __name__ == "__main__":
    raise SystemExit(main())
