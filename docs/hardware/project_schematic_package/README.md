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

## Schematic Generation

Use SKiDL for schematic generation. SKiDL 2.3.0 is actively maintained,
supports KiCad 6 through 10, and can write editable KiCad schematics. Set the
KiCad 9 symbol directory before running a generator:

```powershell
$env:KICAD9_SYMBOL_DIR = "C:\Program Files\KiCad\9.0\share\kicad\symbols"
python -m pip install --upgrade skidl
```

This metadata is the input model for a project-specific SKiDL adapter. The
adapter must map each `device` to a real KiCad library symbol and each pin to
that symbol's actual pin name or number before generating a schematic. It must
also reject duplicate or unknown pin names; this project currently contains
duplicate MCU pin names that need hardware confirmation.

The KiCad 9 symbol mappings verified locally are:

| Project device | KiCad symbol |
| --- | --- |
| `PIC16F18855` | `MCU_Microchip_PIC16:PIC16F18855-xMV` |
| `74HC4514` | `4xxx_IEEE:4514` |
| `ULN2803A` | `Transistor_Array:ULN2803A` |
| `Relay_SPST` | `Relay:Relay_SPST-NO` |
| `NMOS_TO220` | `Device:Q_NMOS` |
| `NTC_10k` | `Device:Thermistor_NTC` |
| `Button` | `Switch:SW_Push` |
| `Conn_01x04` | `Connector_Generic:Conn_01x04` |
| `Fan` | `Motor:Fan` |

The five `fp-lib-table` warnings from SKiDL are non-fatal for schematic output;
they mean footprints have not been assigned. Add project footprints before PCB
layout. The adapter must still handle pin aliases such as `Vdd` to `VDD`,
`IN1` to `I1`, and `OUT1` to `O1`, and must explicitly account for the
4514's latch and enable pins.

## ASG Note

The installed Python package named `asg` is a SPICE-to-schematic generator. It
does not read the `.asg.toml` file in this folder, and it only accepts SPICE
input files with the `.spc` extension. The `.asg.toml` file is project planning
metadata for this package, not an ASG CLI input file.

For KiCad Eeschema output, pass a single symbol library file:

```powershell
python -m asg path\to\circuit.spc "C:\Program Files\KiCad\9.0\share\kicad\symbols\Device.kicad_sym" -f eeschema
```

For Xschem output, pass the Xschem symbol directory instead:

```powershell
python -m asg path\to\circuit.spc path\to\xschem\symbols -f xschem
```

The current KiCad `.net` file is not a `.spc` SPICE source file and cannot be
used as ASG input without conversion. The Python environment can be checked
with `python -m pip check`; ASG 1.1.0 and its parser dependency `lark` must be
installed in the same interpreter used to run `python -m asg`.

---

If you add measured/bench notes, keep them in this folder for future reference!
