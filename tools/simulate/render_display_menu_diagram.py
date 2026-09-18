#!/usr/bin/env python3
"""Render the display/menu state flow as a readable block diagram."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "_build" / "My_Pic_Project" / "sim" / "graphs" / "lcd" / "display_menu_state_diagram.png"


def box(ax, x, y, width, height, text, color):
    patch = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        linewidth=1.4, edgecolor="#263238", facecolor=color,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height / 2, text, ha="center", va="center",
            fontsize=9, color="#172027", wrap=True)


def arrow(ax, start, end, label=None, color="#455a64"):
    ax.annotate("", xy=end, xytext=start,
                arrowprops={"arrowstyle": "-|>", "lw": 1.3, "color": color})
    if label:
        ax.text((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + 0.12,
                label, ha="center", va="center", fontsize=7, color=color)


def main():
    fig, ax = plt.subplots(figsize=(18, 10.5))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 10.5)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_title("PIC AmpControl display, menu, and home-page state flow", fontsize=15, pad=16)

    ax.text(0.7, 9.65, "Normal TX display flow", fontsize=11, color="#1565c0", weight="bold")
    box(ax, 0.7, 8.55, 2.1, 0.82, "Boot / reset", "#dceef7")
    box(ax, 3.25, 8.55, 2.4, 0.82, "Load EEPROM\nselected home page", "#dceef7")
    box(ax, 6.1, 8.55, 3.1, 0.82, "Home page\nSTATUS / PEP / SWR / AMPS / TEMP", "#bfe3d0")
    box(ax, 9.85, 8.55, 2.25, 0.82, "PTT LOW\nrequest", "#ffe0b2")
    box(ax, 12.75, 8.55, 2.25, 0.82, "PTT_RESET_PULSE\n10 ms", "#ffe0b2")
    box(ax, 15.45, 8.55, 1.85, 0.82, "TX sequence\nRELAYS -> VCC -> BIAS", "#bfe3d0")
    arrow(ax, (2.8, 8.96), (3.25, 8.96))
    arrow(ax, (5.65, 8.96), (6.1, 8.96))
    arrow(ax, (9.2, 8.96), (9.85, 8.96), "after startup inhibit")
    arrow(ax, (12.1, 8.96), (12.75, 8.96))
    arrow(ax, (15.0, 8.96), (15.45, 8.96))

    box(ax, 12.0, 7.1, 2.5, 0.82, "PTT_COMPLETE\nall TX outputs active\n500 ms", "#bfe3d0")
    box(ax, 15.0, 7.1, 2.3, 0.82, "Restore home page\nwhile PTT remains LOW", "#bfe3d0")
    arrow(ax, (16.35, 8.55), (13.25, 7.92))
    arrow(ax, (14.5, 7.51), (15.0, 7.51))

    ax.text(0.7, 6.45, "Trip decision inputs", fontsize=11, color="#b71c1c", weight="bold")
    box(ax, 0.7, 5.35, 2.8, 0.82, "SWR detectors\nSWR1 pair / SWR2 pair", "#ffd0d0")
    box(ax, 4.25, 5.35, 3.0, 0.82, "ADC limits\nTEMP / AMPS / OVDR / DRAIN", "#fff0b3")
    box(ax, 8.0, 5.35, 2.7, 0.82, "Hardware comparator\nRB4 hard fault", "#ffd0d0")
    box(ax, 11.45, 5.35, 2.55, 0.82, "Protection check\nevery main-loop pass", "#ffe0b2")
    box(ax, 14.75, 5.35, 2.55, 0.82, "TRIP priority\nFAULT LCD + shutdown", "#ffd0d0")
    arrow(ax, (3.5, 5.76), (4.25, 5.76))
    arrow(ax, (7.25, 5.76), (8.0, 5.76))
    arrow(ax, (10.7, 5.76), (11.45, 5.76))
    arrow(ax, (14.0, 5.76), (14.75, 5.76))
    ax.text(9.0, 4.85,
        "Converging arrows mean independent fault sources feed one trip decision, not overlapping display states.",
        ha="center", fontsize=8, color="#546e7a")

    ax.text(0.7, 3.9, "Recovery and re-arm", fontsize=11, color="#2e7d32", weight="bold")
    box(ax, 0.7, 2.8, 2.8, 0.82, "Temperature trip", "#fff0b3")
    box(ax, 4.3, 2.8, 3.0, 0.82, "Cool below threshold\nplus 5 C hysteresis", "#fff0b3")
    box(ax, 8.1, 2.8, 3.0, 0.82, "Clear trip\nreset comparator", "#bfe3d0")
    box(ax, 12.0, 2.8, 2.5, 0.82, "Re-enter\nTX sequence", "#bfe3d0")
    arrow(ax, (3.5, 3.21), (4.3, 3.21))
    arrow(ax, (7.3, 3.21), (8.1, 3.21))
    arrow(ax, (11.1, 3.21), (12.0, 3.21))

    box(ax, 0.7, 1.25, 2.8, 0.82, "SWR / hardware /\ncurrent / overdrive / drain", "#ffd0d0")
    box(ax, 4.3, 1.25, 3.0, 0.82, "Latched until\noperator re-arms", "#ffd0d0")
    box(ax, 8.1, 1.25, 3.0, 0.82, "PTT HIGH then LOW\nor long-press clear", "#ffe0b2")
    arrow(ax, (3.5, 1.66), (4.3, 1.66))
    arrow(ax, (7.3, 1.66), (8.1, 1.66))
    arrow(ax, (11.1, 1.66), (12.0, 2.8), "clear, then sequence")

    ax.text(0.7, 0.35,
        "Priority rule: TRIP display overrides PTT_COMPLETE and home-page restoration until the fault is cleared.",
        fontsize=8, color="#b71c1c")
    fig.tight_layout()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
