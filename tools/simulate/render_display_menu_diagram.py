#!/usr/bin/env python3
"""Render the display/menu state flow as a readable block diagram."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "_build" / "My_Pic_Project" / "sim" / "graphs" / "display_menu_state_diagram.png"


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
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_title("PIC AmpControl display, menu, and home-page state flow", fontsize=15, pad=16)

    box(ax, 0.5, 7.25, 2.1, 0.8, "Boot / reset", "#dceef7")
    box(ax, 3.2, 7.25, 2.4, 0.8, "Load EEPROM\nselected home page", "#dceef7")
    box(ax, 6.2, 7.25, 2.4, 0.8, "Home page\nSTATUS / PEP / SWR / TEMP", "#bfe3d0")
    arrow(ax, (2.6, 7.65), (3.2, 7.65))
    arrow(ax, (5.6, 7.65), (6.2, 7.65))

    box(ax, 0.6, 5.65, 2.6, 0.8, "PTT LOW request", "#ffe0b2")
    box(ax, 4.0, 5.65, 2.8, 0.8, "Save home page\nshow transient status", "#ffe0b2")
    box(ax, 7.7, 5.65, 2.8, 0.8, "PTT_RESET_PULSE\n10 ms", "#ffe0b2")
    box(ax, 11.0, 5.65, 2.3, 0.8, "TX sequence\nRELAYS -> VCC -> BIAS", "#bfe3d0")
    arrow(ax, (1.9, 7.25), (1.9, 6.45), "after startup inhibit")
    arrow(ax, (3.2, 6.05), (4.0, 6.05))
    arrow(ax, (6.8, 6.05), (7.7, 6.05))
    arrow(ax, (10.5, 6.05), (11.0, 6.05))

    box(ax, 8.1, 4.05, 2.4, 0.8, "PTT_COMPLETE\nall TX outputs active\n500 ms", "#bfe3d0")
    box(ax, 11.0, 4.05, 2.3, 0.8, "Restore home page\nwhile PTT remains LOW", "#bfe3d0")
    arrow(ax, (12.15, 5.65), (9.3, 4.85))
    arrow(ax, (10.5, 4.45), (11.0, 4.45))

    box(ax, 0.55, 3.75, 3.0, 0.8, "SWR paths\nSWR1 pair / SWR2 pair", "#ffd0d0")
    box(ax, 4.15, 3.75, 3.0, 0.8, "Software analog limits\nTEMP / AMPS / OVDR / DRAIN", "#fff0b3")
    box(ax, 7.75, 3.75, 2.7, 0.8, "Hardware comparator\nRB4 hard fault", "#ffd0d0")
    box(ax, 11.0, 3.75, 2.4, 0.8, "TRIP priority\nFAULT LCD + shutdown", "#ffd0d0")
    arrow(ax, (3.55, 4.15), (4.15, 4.15))
    arrow(ax, (7.15, 4.15), (7.75, 4.15))
    arrow(ax, (10.45, 4.15), (11.0, 4.15))
    ax.text(6.9, 4.78, "monitored continuously while TX is active", ha="center", fontsize=8, color="#b71c1c")

    box(ax, 0.7, 1.65, 2.7, 0.85, "Temperature trip", "#fff0b3")
    box(ax, 4.3, 1.65, 2.8, 0.85, "Cool below threshold\nplus 5 C hysteresis", "#fff0b3")
    box(ax, 8.0, 1.65, 2.8, 0.85, "Clear trip, reset comparator,\nre-enter TX sequence", "#bfe3d0")
    arrow(ax, (5.7, 3.75), (2.05, 2.5), "temperature only")
    arrow(ax, (3.4, 2.08), (4.3, 2.08))
    arrow(ax, (7.1, 2.08), (8.0, 2.08))

    box(ax, 11.0, 1.65, 2.3, 0.85, "Other trips\nlatched", "#ffd0d0")
    box(ax, 11.0, 0.25, 2.3, 0.85, "PTT HIGH then LOW\nor long-press clear", "#ffe0b2")
    arrow(ax, (10.8, 3.78), (11.0, 2.5))
    arrow(ax, (12.15, 1.65), (12.15, 1.1))
    arrow(ax, (11.0, 0.68), (10.8, 1.65), "clear, then re-arm")

    ax.text(0.7, 0.25,
            "Priority rule: TRIP display always overrides PTT_COMPLETE and home-page restoration until the fault is cleared.",
            fontsize=8, color="#b71c1c")
    fig.tight_layout()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
