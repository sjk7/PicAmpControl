# Linear Amplifier Protection Controller – Project Schematic Package

This folder collects all project-level resources needed to capture a complete, production-quality schematic for the PIC18F47Q10-based amplifier protection board.

## Contents
- `component_list.csv` — full bill of materials and symbols to place (`component_list.md` is the readable summary)
- `connection_table.csv` — **the authoritative netlist** (`connection_table.md` documents conventions only)
- `wiring_checklist.md` — step-by-step capture process
- `block_diagram.md` — high-level system structure plus the band selection/lockout flow

> Pin assignments are not listed in this folder. Single source of truth:
> [../PIC18F47Q10_pin_map_and_setup.md](../PIC18F47Q10_pin_map_and_setup.md).

## Recommended Use
1. Place each symbol from `component_list` in the schematic tool of your choice.
2. Wire exactly per `connection_table` (nets can be copy/pasted for clarity).
3. Use `wiring_checklist.md` to verify nothing is missed before layout/PCB steps.

## Scope

This folder is a set of design inputs for capture by hand. The script- and
MCP-based schematic generators that used to drive it have been removed, so
there is no automated path from these tables to a schematic file, and no
tool-specific artifacts live here.

---

If you add measured/bench notes, keep them in this folder for future reference!
