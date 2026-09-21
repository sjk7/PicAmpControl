# Linear Amplifier Protection Controller – Project Schematic Package

This folder collects all project-level resources needed to capture a complete, production-quality schematic for the PIC16F18875-based amplifier protection board.

## Contents
- `component_list.csv` — full bill of materials and symbols to place (`component_list.md` is the readable summary)
- `connection_table.csv` — **the authoritative netlist** (`connection_table.md` documents conventions only)
- `wiring_checklist.md` — step-by-step capture process
- `block_diagram.md` — high-level system structure plus the band selection/lockout flow
- `_SCHEMATIC_TEMPLATE.kicad_sch` — starter title block for new sheets

> Pin assignments are not listed in this folder. Single source of truth:
> [../PIC16F18875_pin_map.md](../PIC16F18875_pin_map.md).

## Recommended Use
1. Use the `schematic-design` MCP skill (`.agents/skills/schematic-design/SKILL.md`)
   to generate or modify the schematic under `generated/`.
2. Place each symbol from `component_list`.
3. Wire exactly per `connection_table` (nets can be copy/pasted for clarity).
4. Use `wiring_checklist.md` to verify nothing is missed before layout/PCB steps.

## Schematic Generation

Schematic generation and modification go through the `schematic-design` MCP
skill and the `mcp-server-kicad` MCP server (see `.vscode/mcp.json`). Do not
hand-edit `.kicad_sch` files or run `kicad-cli` directly; use the skill's
MCP tools instead.

The previous script-based generator has been removed. The component and
connection tables in this folder are design inputs for the MCP workflow only.

---

If you add measured/bench notes, keep them in this folder for future reference!
