#!/usr/bin/env python3
"""Render the firmware LCD lifecycle as isolated 16x2 LCD panels."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "_build" / "My_Pic_Project" / "sim" / "graphs" / "lcd_lifecycle_16x2.png"

PANELS = [
    ("BOOT / EEPROM", "P=   0W SWR=1.0", "----------------", "Loaded saved home page; example STATUS page"),
    ("HOME PAGE: PEP", "P=   0W SWR=1.0", "----------------", "User-selected home page remains saved"),
    ("HOME PAGE: TEMP", "PEP ------------", "TEMP  25C", "Other selectable home page example"),
    ("PTT LOW REQUEST", "P=   0W SWR=1.0", "----------------", "Firmware saves the selected home page; no fault text"),
    ("PTT RESET PULSE", "P=   0W SWR=1.0", "----------------", "RC1/SETTLE pulses LOW for 10 ms; LCD page is unchanged"),
    ("PTT_COMPLETE", "PTT COMPLETE    ", "TX ACTIVE       ", "Shown only after RELAYS, TX_VCC, and TX_BIAS are all active"),
    ("HOME PAGE RESTORED", "P=   0W SWR=1.0", "----------------", "Restored 500 ms after PTT_COMPLETE"),
    ("TRIP: TEMPERATURE", "FAULT:          ", "TEMP            ", "Fault display has priority and remains until temperature recovery"),
    ("TRIP: ALL-FAULT EXAMPLE", "FAULT: ALL TRIPS", "S1 S2 HW A T O D ", "16x2 shorthand: SWR1, SWR2, HWFLT, AMPS, TEMP, OVDR, DRN"),
    ("TEMP RECOVERY", "P=   0W SWR=1.0", "----------------", "After hysteresis: comparator reset, then TX can sequence again"),
]


def lcd_panel(ax, x, y, title, line1, line2, note, accent):
    cell_width = 0.39
    screen_width = cell_width * 16
    width, height = screen_width + 0.72, 2.05
    line1 = line1[:16].ljust(16)
    line2 = line2[:16].ljust(16)
    ax.add_patch(FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.04,rounding_size=0.08",
                                linewidth=1.4, edgecolor="#263238", facecolor="#263238"))
    screen_x, screen_y = x + 0.36, y + 0.38
    for row, text in enumerate((line1, line2)):
        for column, character in enumerate(text):
            cell = Rectangle((screen_x + column * cell_width, screen_y + (1 - row) * 0.5),
                             cell_width, 0.5, linewidth=0.35,
                             edgecolor="#91ae78", facecolor="#b9d59b")
            ax.add_patch(cell)
            if character != " ":
                ax.text(screen_x + (column + 0.5) * cell_width,
                        screen_y + (1 - row) * 0.5 + 0.25,
                        character, ha="center", va="center", fontsize=15,
                        family="monospace", color="#1d2b1e")
    ax.text(x + width / 2, y + height + 0.16, title, ha="center", va="bottom", fontsize=11,
            color=accent, weight="bold")
    ax.text(x + width / 2, y + 0.14, note, ha="center", va="center", fontsize=7, color="#455a64")


def main():
    fig, ax = plt.subplots(figsize=(18, 15))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 15.5)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_title("PIC AmpControl LCD lifecycle: exact 16x2 display states", fontsize=16, pad=18)

    positions = [(0.55 + (index % 2) * 7.85, 12.15 - (index // 2) * 2.55)
                 for index in range(len(PANELS))]
    for index, ((title, line1, line2, note), (x, y)) in enumerate(zip(PANELS, positions)):
        accent = "#b71c1c" if title.startswith("TRIP") else "#1565c0" if "PTT" in title else "#2e7d32"
        lcd_panel(ax, x, y, title, line1, line2, note, accent)
        if index > 0:
            prev_x, prev_y = positions[index - 1]
            if index % 2:
                start = (prev_x + 7.2, prev_y + 1.02)
                end = (x, y + 0.86)
            else:
                start = (prev_x + 3.6, prev_y)
                end = (x + 3.6, y + 2.05)
            ax.annotate("", xy=end, xytext=start,
                        arrowprops={"arrowstyle": "-|>", "lw": 1.1, "color": "#607d8b"})
    ax.text(0.6, 0.35,
            "Priority: TRIP text overrides PTT_COMPLETE and home-page restoration until the fault is cleared.",
            fontsize=9, color="#b71c1c")
    fig.tight_layout()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
