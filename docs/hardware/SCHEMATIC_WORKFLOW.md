# Schematic Generation & Validation Workflow

## Overview

This workflow generates EasyEDA Pro schematics directly from a YAML specification, with automatic SVG visualization in VS Code Insiders for validation.

### Flow Diagram

```
pic_amp_control_full.yaml
       ↓
easyeda_pro_generator.py ──→ out/picampcontrol_easyeda_agent.json
       ↓
svg_renderer.py ──────────→ out/picampcontrol_schematic.svg
       ↓
visual_validator.py ──────→ Validation report
       ↓
[Open in VS Code + SVG Viewer] ──→ Visual inspection
```

## Quick Start

### 1. Generate Schematic Specification

```bash
python tools/easyeda_pro_generator.py
```

Outputs:
- `out/picampcontrol_easyeda_agent.json` - For easyeda-agent CLI
- `out/picampcontrol_easyeda_copilot.json` - For easyeda-copilot MCP

### 2. Render to SVG

```bash
python tools/svg_renderer.py
```

Outputs:
- `out/picampcontrol_schematic.svg` - Visual schematic preview

### 3. Validate Layout

```bash
python tools/visual_validator.py
```

Reports:
- Component counts and grouping
- Dense placement warnings
- Missing power nets
- Layout density analysis

### 4. View in VS Code

```bash
code-insiders out/picampcontrol_schematic.svg
```

Install **SVG Viewer** extension (renjie.svg-viewer) for syntax highlighting and preview.

## Continuous Development

### Watch Mode (Auto-regenerate on changes)

```bash
python tools/watch_and_render.py
```

Monitors:
- `tools/easyeda_pro_generator.py` - If changed, regenerate specs
- `out/picampcontrol_easyeda_agent.json` - If changed, regenerate SVG

The SVG preview in VS Code will refresh automatically.

### Full Build (All steps)

```bash
python tools/easyeda_pro_generator.py && python tools/svg_renderer.py && python tools/visual_validator.py
```

## Component Specification Format

### YAML Input (`pic_amp_control_full.yaml`)

```yaml
instances:
  U1:
    part_number: "PIC16F18875-I/SP"
    value: ""
    position: [x, y]
  R1:
    part_number: "R0603"
    value: "10k"
    position: [x, y]
```

### JSON Output (`picampcontrol_easyeda_agent.json`)

```json
{
  "title": "PicAmpControl - Amplifier Protection",
  "components": [
    {
      "uuid": "...",
      "part_number": "PIC16F18875-I/SP",
      "designator": "U1",
      "value": "",
      "x": 0.10,
      "y": 0.15,
      "lcsc_part": "C1128"
    }
  ],
  "nets": [
    {"name": "+12V_RAW", "color": "#000000"},
    {"name": "+5V", "color": "#FF0000"}
  ]
}
```

## Component Functional Grouping

Components are automatically organized into:

1. **Power Supply** - Input connector, regulator, bulk capacitors
2. **MCU** - Microcontroller and support (MCLR, decoupling)
3. **ADC Conditioning** - Pre-filter, post-filter, temperature/current/drain sensing
4. **Comparator** - Fault detection (LM339)
5. **Digital Outputs** - TX, TX_VCC, TX_BIAS, TRIP pull-downs
6. **Fan Control** - Gate driver, MOSFET, fan connector
7. **Interfaces** - I2C pull-ups, encoder pull-ups, PTT input

## Validation Rules

### Placement Checks

- ❌ **Overlap Detection** - Components must not overlap
- ⚠️ **Spacing Warnings** - Recommend >= 0.08" between component centers
- ✓ **Required Nets** - +12V_RAW, +5V, GND must be defined

### Component Count

- Expected: 88 total components across all blocks
- Current: 52 (initial block implementation)

### Grouping Validation

- Power supply isolated (prevents accidental shorts)
- Analog sections grouped (ADC pre/post filters, sensing)
- Digital section separate (MCU, outputs, interfaces)
- Fan control isolated (high current switching)

## Integration with EasyEDA Pro

### Option 1: easyeda-agent CLI

```bash
npm install -g @easyeda/easyeda-agent
easyeda sch create --spec out/picampcontrol_easyeda_agent.json
```

### Option 2: easyeda-copilot MCP

Use the easyeda-copilot MCP server with Claude:

1. Enable EasyEDA Pro external interactions
2. Start MCP server: `node easyeda-copilot.js`
3. Pass `picampcontrol_easyeda_copilot.json` to Claude with MCP enabled
4. Ask: "Create this circuit in EasyEDA Pro"

### Option 3: Custom Extension

Build a `.eext` extension using official SDK:

```bash
npm install @jlceda/pro-api-sdk
npm run build
```

See [EasyEDA Pro API Guide](https://prodocs.easyeda.com/en/api/guide/) for details.

## File Locations

```
tools/
  ├── easyeda_pro_generator.py    # Generate component specs
  ├── svg_renderer.py             # Render specs to SVG
  ├── visual_validator.py         # Validate layout
  └── watch_and_render.py         # Auto-regenerate on changes

out/
  ├── picampcontrol_easyeda_agent.json      # Agent-compatible format
  ├── picampcontrol_easyeda_copilot.json    # Copilot-compatible format
  └── picampcontrol_schematic.svg           # Visual preview

docs/
  └── hardware/
      └── project_schematic_package/
          └── SCHEMATIC_WORKFLOW.md         # This file
```

## Common Workflows

### Add a New Component

1. Update `tools/easyeda_pro_generator.py`:
   ```python
   sch.add_component("R0603", "R123", "10k", 0.30, 0.50)
   ```

2. Run generator:
   ```bash
   python tools/easyeda_pro_generator.py
   ```

3. SVG auto-updates (if using watch mode)

4. Review in VS Code Insiders

5. Validate:
   ```bash
   python tools/visual_validator.py
   ```

### Adjust Component Placement

1. Edit coordinates in `easyeda_pro_generator.py`
2. Generator regenerates automatically
3. Watch script detects change
4. SVG refreshes in VS Code
5. Visual validation updates

### Check Layout Issues

```bash
python tools/visual_validator.py
```

Reports:
- Dense placement (spacing < 0.08")
- Missing nets
- Component grouping summary
- Part count by type

### Export to EasyEDA Pro

After visual validation passes:

```bash
# Using easyeda-agent
easyeda sch create --spec out/picampcontrol_easyeda_agent.json

# OR using easyeda-copilot (MCP)
# Pass JSON to Claude with easyeda-copilot MCP enabled
```

## Design Rules Checklist

- ✅ All power nets defined (+12V_RAW, +5V, GND)
- ✅ Components grouped by function
- ✅ No overlapping component symbols
- ✅ Spacing recommendations met (>= 0.08" typical)
- ⏳ Wire routing (not yet implemented in SVG)
- ⏳ Pin connectivity (validated in EasyEDA Pro)

## Next Steps

1. **Expand to 88 Components** - Add all ADC channels, additional outputs
2. **Wire Routing** - Implement net connectivity in SVG visualization
3. **Hierarchical Subcircuits** - Split into 8 functional modules
4. **PCB Layout** - Export from EasyEDA Pro for placement/routing
5. **Manufacturing Data** - Generate Gerbers, BOM, placement files

## Troubleshooting

### SVG doesn't update in VS Code

- Install SVG Viewer extension: `renjie.svg-viewer`
- Manually reload file: `Ctrl+Shift+P` → "Reload"
- Check watch mode terminal for errors

### Component count doesn't match

Run visual_validator.py to see breakdown:
```bash
python tools/visual_validator.py | grep "Total components"
```

### Layout has dense placement warnings

Review placement coordinates in `easyeda_pro_generator.py` and increase distances.

### JSON generation fails

Check YAML format in `pic_amp_control_full.yaml` and run:
```bash
python -c "import yaml; yaml.safe_load(open('pic_amp_control_full.yaml'))"
```

## References

- [EasyEDA Pro API Documentation](https://prodocs.easyeda.com/en/api/guide/)
- [easyeda-agent Repository](https://github.com/zhoushoujianwork/easyeda-agent)
- [easyeda-copilot Repository](https://github.com/biosshot/easyeda-copilot)
- [Official SDK](https://github.com/easyeda/pro-api-sdk)
