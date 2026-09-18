# Linear Amplifier Protection Controller – Project Schematic Package

This folder collects all project-level resources needed to capture a complete, production-quality schematic for the PIC16F18855-based amplifier protection board.

## Contents
- `component_list.csv` and `.md` — full bill of materials and symbols to place
- `connection_table.csv` and `.md` — block-by-block netlist/wiring
- `wiring_checklist.md` — step-by-step capture process
- `block_diagram.txt` and (optionally) PNG — high-level system structure
- `_SCHEMATIC_TEMPLATE.kicad_sch` — starter title block for new sheets

## Recommended Use
1. Start a fresh KiCad schematic in your project.
2. Place each symbol from `component_list`.
3. Wire exactly per `connection_table` (nets can be copy/pasted for clarity).
4. Use `wiring_checklist.md` to verify nothing is missed before layout/PCB steps.

---

If you add measured/bench notes, keep them in this folder for future reference!
