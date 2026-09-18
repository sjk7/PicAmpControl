# Schematic Workflow (KiCad MCP Skill)

This is the current and only supported way to generate or modify the KiCad
schematic in this repository.

## What we use now

- **Skill:** `schematic-design`, installed at
  [.agents/skills/schematic-design/SKILL.md](../../.agents/skills/schematic-design/SKILL.md).
  Tracked by [skills-lock.json](../../skills-lock.json), sourced from
  `productofamerica/mcp-server-kicad`.
- **MCP server:** `mcp-server-kicad`, configured in
  [.vscode/mcp.json](../../.vscode/mcp.json). It exposes ~109 MCP tools for
  reading/writing `.kicad_sch`/`.kicad_pcb`/`.kicad_sym` files, running
  ERC/DRC, and exporting.
- **Target schematic:**
  `docs/hardware/project_schematic_package/generated/mcp-final/pic_amp_protection.kicad_sch`
  (the MCP-created project root).

There is no legacy generator to run. The component and connection tables under
`docs/hardware/project_schematic_package/` are reference inputs for planning.

## Rule: never hand-edit KiCad files

Never use Read/Write/Edit tools directly on `.kicad_sch`, `.kicad_pcb`,
`.kicad_sym`, `.kicad_mod`, `.kicad_pro`, or `.kicad_prl` files, and never run
`kicad-cli` directly. All KiCad file changes must go through the MCP tools
the `schematic-design` skill uses. This rule is stated in the skill file
itself; it is repeated here so it survives even if the skill file is
regenerated.

## Getting the skill/server working in a new session

1. Confirm the skill is installed:
   ```powershell
   npx --yes skills list --json
   ```
   Expect an entry named `schematic-design` with `path` under
   `.agents\skills\schematic-design`.
2. Run the setup script — safe to re-run any time, including while the MCP
   server is already running:
   ```powershell
   powershell -File tools\setup_schematic_skill.ps1
   ```
   It checks/installs Node.js (must already be present), the
   `schematic-design` skill, `uv`/`uvx`, `kicad-cli`, and writes
   `.vscode\mcp.json`.
  On another Windows machine, run this from the repository root after
  installing KiCad 9.x or 10.x.
3. Start the MCP server in VS Code:
   - Command Palette → `MCP: List Servers` → `kicad` → `Start`.
   - Accept the trust prompt if this is the first start.
4. Ask for the skill by name, e.g.:
   - "Use the `schematic-design` skill in modification mode to add a
     decoupling cap to U1."
   - "Use the `schematic-design` skill in plan mode to execute
     `specs/schematic-plan.md`."

The checked-in `.vscode/mcp.json` points to `generated/mcp-final`. Do not open
the similarly named legacy schematic directly under `generated/`.

## Troubleshooting

- Server not in `MCP: List Servers`: reload the VS Code window
  (`Developer: Reload Window`), then open `.vscode/mcp.json` and use its
  inline `Start` action.
- `uvx` missing: `tools/setup_schematic_skill.ps1` installs it via
  `python -m pip install --user uv`; it is not always placed on `PATH`, so
  `.vscode/mcp.json` references its full path directly.
- `kicad-cli` missing: install KiCad 9.x or 10.x; ERC/DRC/exports need it,
  but read/write tools work without it.
