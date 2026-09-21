#!/usr/bin/env python3
"""Render the firmware LCD lifecycle as isolated 16x2 LCD panels."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

REPO_ROOT = Path(__file__).resolve().parents[2]
LCD_GRAPH_DIR = REPO_ROOT / "_build" / "My_Pic_Project" / "sim" / "graphs" / "lcd"
OUTPUT = LCD_GRAPH_DIR / "lcd_lifecycle_16x2.png"
FAULT_OUTPUT = LCD_GRAPH_DIR / "lcd_fault_screens_16x2.png"
NORMAL_OUTPUT = LCD_GRAPH_DIR / "lcd_normal_screens_16x2.png"
SETTINGS_OUTPUT = LCD_GRAPH_DIR / "settings" / "lcd_settings_navigation_16x2.png"

PANELS = [
    ("BOOT / DEFAULT", "P=   0W ........", "TEMP  25C", "Default home page is the PEP / temperature display"),
    ("HOME PAGE: PEP", "P=   0W ........", "TEMP  25C", "Default home page remains saved unless the user selects another"),
    ("HOME PAGE: TEMP", "P=   0W ........", "TEMP  25C", "Other selectable home page example"),
    ("PTT LOW REQUEST", "P=   0W SWR=1.00", "................", "Firmware saves the selected home page; no fault text"),
    ("PTT RESET PULSE", "P=   0W SWR=1.00", "................", "RC1/SETTLE pulses LOW for 10 ms; LCD page is unchanged"),
    ("PTT_COMPLETE", "PTT COMPLETE    ", "TX ACTIVE       ", "Shown only after RELAYS, TX_VCC, and TX_BIAS are all active"),
    ("HOME PAGE RESTORED", "P=   0W ........", "TEMP  25C", "Restored 500 ms after PTT_COMPLETE"),
    ("TEMP RECOVERY", "P=   0W ........", "TEMP  25C", "After hysteresis: comparator reset, then TX can sequence again"),
]
FAULT_PANELS = [
    ("TRIP: TEMPERATURE", "TEMP 101/100C   ", "MAX 100C        ", "Measured temperature / EEPROM trip limit"),
    ("TRIP: SWR1", "FLTR?? CHECK LPF", "SWR1 > 10:1     ", "Extreme SWR1 suggests wrong output filter selection"),
    ("TRIP: SWR2", "SWR2 2.1/2.0    ", "MAX 2.0:1       ", "Measured SWR2 / EEPROM trip limit"),
    ("TRIP: HARDWARE", "FAULT:          ", "HWFLT           ", "Hardware comparator fault"),
    ("TRIP: CURRENT", "AMPS 41/40A     ", "MAX 40A         ", "Measured current / EEPROM trip limit"),
    ("TRIP: OVERDRIVE", "OVDR 11/10W     ", "MAX 10W         ", "Measured overdrive / EEPROM trip limit"),
    ("TRIP: DRAIN", "DRN 151/150V    ", "MAX 150V        ", "Measured drain / EEPROM trip limit; ADC 5 V = 300 V"),
    ("TRIP: ALL-FAULT EXAMPLE", "FAULT: ALL TRIPS", "S1 S2 HW A T O D ", "S1/S2/HW/AMPS/TEMP/OVDR/DRN shorthand"),
]
NORMAL_PANELS = [
    ("TX STATUS: PEP", "P=1125W SWR=1.23", "||||||||||||....", "3/4 of 1500 W full scale; STATUS shows post-filter SWR to hundredths"),
    ("TX STATUS: RMS", "R=1125W SWR=1.23", "||||||||||||....", "Same STATUS page with RMS mode selected"),
    ("PEP / TEMPERATURE", "P=1125W ||||||..", "TEMP  50C       ", "Peak hold and decay are user settings saved in EEPROM"),
    ("SWR METER", "SWR1   SWR=1.74", "SWR2   SWR=1.23", "SWR readouts use the firmware's two-decimal display resolution"),
    ("CURRENT METER", "A= 30A PK= 30A  ", "||||||||||||....", "Peak holds for 1.2 s, then decays smoothly with the configured peak interval"),
    ("PTT_COMPLETE", "PTT COMPLETE    ", "TX ACTIVE       ", "Transient normal TX confirmation; no trip is latched"),
]
SETTINGS_PANELS = [
    ("01 PRESS", "SWR1 TRIP      ", "3.0:1           ", "Rotate changes SWR1 trip threshold"),
    ("02 PRESS", "SWR2 TRIP      ", "2.0:1           ", "Rotate changes SWR2 trip threshold"),
    ("03 PRESS", "SWR1 FWD       ", "1500W           ", "Rotate changes SWR1 forward full scale"),
    ("04 PRESS", "SWR2 FWD       ", "1500W           ", "Rotate changes SWR2 forward full scale"),
    ("05 PRESS", "NTC B          ", "3950C           ", "Rotate cycles NTC profile"),
    ("06 PRESS", "TEMP TRIP      ", "100C            ", "Rotate changes thermal trip point"),
    ("07 PRESS", "INPUT TRIP     ", "10.0W           ", "Rotate changes overdrive trip point"),
    ("08 PRESS", "DRAIN TRIP     ", "150V            ", "Rotate changes drain voltage trip point"),
    ("09 PRESS", "CURR TRIP      ", " 40A            ", "Rotate changes current trip point"),
    ("10 PRESS", "TX-VCC DLY     ", "  20ms          ", "Rotate changes RELAYS to TX_VCC delay"),
    ("11 PRESS", "TX-BIAS DLY    ", "  20ms          ", "Rotate changes TX_VCC to TX_BIAS delay"),
    ("12 PRESS", "TX ACTIVE      ", "LOW             ", "Rotate toggles TX output polarity"),
    ("13 PRESS", "TX-VCC POL     ", "LOW             ", "Rotate toggles TX_VCC output polarity"),
    ("14 PRESS", "TX-BIAS POL    ", "LOW             ", "Rotate toggles TX_BIAS output polarity"),
    ("15 PRESS", "FAN POL        ", "LOW             ", "Rotate toggles fan output polarity"),
    ("16 PRESS", "TRIP POL       ", "LOW             ", "Rotate toggles trip-status output polarity"),
    ("17 PRESS", "POWER MODE     ", "PEP             ", "Rotate toggles STATUS power mode"),
    ("18 PRESS", "NET POWER      ", "FWD             ", "Rotate toggles forward/net power display"),
    ("19 PRESS", "PK HOLD        ", "1200ms          ", "Rotate changes saved peak hold time"),
    ("20 PRESS", "PK DECAY       ", " 100ms          ", "Rotate changes saved peak decay interval"),
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


def render_page(panels, output, title, accent_default,
                footer_text="TRIP text overrides PTT_COMPLETE and home-page restoration until the fault is cleared.",
                footer_color="#b71c1c", columns=2, snake=False):
    rows = (len(panels) + columns - 1) // columns
    row_step = 3.05
    column_step = 7.85
    panel_width = 0.39 * 16 + 0.72
    top_y = 1.0 + (rows - 1) * row_step
    x_max = 0.55 + columns * column_step
    fig, ax = plt.subplots(figsize=(max(18, columns * 8.5), max(10, rows * 3.15)))
    ax.set_xlim(0, x_max)
    ax.set_ylim(0, top_y + 2.65)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_title(title, fontsize=16, pad=18)

    positions = []
    for index in range(len(panels)):
        row = index // columns
        column = index % columns
        if snake and row % 2:
            column = columns - 1 - column
        positions.append((0.55 + column * column_step, top_y - row * row_step))
    for index, ((panel_title, line1, line2, note), (x, y)) in enumerate(zip(panels, positions)):
        accent = "#b71c1c" if panel_title.startswith("TRIP") else accent_default
        lcd_panel(ax, x, y, panel_title, line1, line2, note, accent)
        if index > 0:
            prev_x, prev_y = positions[index - 1]
            if y == prev_y:
                if x > prev_x:
                    start = (prev_x + panel_width, prev_y + 1.02)
                    end = (x, y + 1.02)
                else:
                    start = (prev_x, prev_y + 1.02)
                    end = (x + panel_width, y + 1.02)
            else:
                start = (prev_x + panel_width / 2, prev_y)
                end = (x + panel_width / 2, y + 2.05)
            ax.annotate("", xy=end, xytext=start,
                        arrowprops={"arrowstyle": "-|>", "lw": 1.1, "color": "#607d8b"})
    ax.text(0.6, 0.35, footer_text, fontsize=9, color=footer_color)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {output}")


def render_settings_navigation(plt):
    render_page(SETTINGS_PANELS, SETTINGS_OUTPUT,
                "PIC AmpControl settings navigation: press advances, rotate edits, hold exits",
                "#6a1b9a",
                "Short press steps through saved settings; rotate edits the shown value; long press or idle timeout returns to the saved home page.",
                "#6a1b9a", columns=4, snake=True)


def main():
    render_page(PANELS, OUTPUT, "PIC AmpControl LCD lifecycle: exact 16x2 display states", "#1565c0")
    render_page(FAULT_PANELS, FAULT_OUTPUT, "PIC AmpControl LCD fault screens: exact 16x2 examples", "#2e7d32")
    render_page(NORMAL_PANELS, NORMAL_OUTPUT, "PIC AmpControl normal TX LCD screens: 1125 W, SWR1 1.74:1, SWR2 1.23:1, 50 C", "#1565c0")
    render_settings_navigation(plt)


if __name__ == "__main__":
    main()
