# Schematic Generation Rules

These rules apply to every generated KiCad schematic in this repository.

## Toolchain

- Use SKiDL with the installed KiCad symbol libraries.
- Use `kicad-sch-api` for topology-safe structured component movement and KiCad file operations. Install with `python -m pip install --upgrade kicad-sch-api`.
- Do not use the Python package `asg` for this project metadata. ASG accepts SPICE `.spc` input and is not the project schematic generator.
- Generate an editable KiCad `.kicad_sch` hierarchy, not a PCB file or a block diagram.
- Open the root file `docs/hardware/project_schematic_package/generated/pic_amp_protection.kicad_sch` in KiCad. Child sheets are referenced from that root.

## Circuit Structure

- The output must be a real electrical circuit diagram with symbols, pins, wires, junctions, power symbols, and net labels.
- Group circuitry by electrical meaning and size:
  - MCU/control sheet: PIC16F18855, power, decoupling, fan MOSFET/fan, temperature sensor, and LCD connector.
  - Separate sheets: band decoder, relay driver, and relay bank/flyback diodes.
- Small MCU-adjacent circuits belong on the MCU sheet. Do not create tiny standalone sheets for a fan or temperature sensor.
- Keep nets local to their owning sheet. Only nets that cross sheets should be root/hierarchical nets.
- Do not invent connections to resolve visual clutter. Use the approved firmware and hardware pin maps as the source of truth.
- The default generator path must preserve the electrically safe SKiDL hierarchy and use `kicad-sch-api` for any component movement. Raw S-expression wire or symbol translation is experimental and must not be enabled by default.

## Placement and Routing

- Placement and routing must be automatic and general. Do not accumulate per-wire or per-component coordinate hacks.
- Wires must be orthogonal. Never emit diagonal wire segments.
- Never route through an IC body, pin field, or the clearance margin around an IC.
- Treat every IC body plus all of its pins and a clearance margin as a protected routing envelope. Unrelated wires must route around it.
- A wire may enter the protected envelope only to connect to its own pin.
- Use Manhattan detours with clearance when a route would enter an IC envelope.
- Avoid wire, label, and text overlaps. Label spacing must be dynamic:
  - Start each label tail at least 10 mm from its pin.
  - Add clearance based on rendered label width.
  - Advance by 2.54 mm or more until estimated label boxes do not overlap.
- Do not leave wire endpoints floating. Do not transform symbol positions or wire endpoints independently in a way that changes electrical topology.
- Prefer physical wires for same-sheet connections such as temperature, fan, decoupling, and I2C. Use labels for genuine cross-sheet connections or intentionally external signals.
- If a geometric postprocessor cannot preserve topology, it must be disabled rather than producing a visually attractive but electrically wrong schematic. A moved component must be saved and revalidated through KiCad before it is accepted.

## IC Text and Symbols

- IC bodies should show only the designator and IC name/value.
- Keep the designator and name inside the IC body when they fit.
- If they do not fit, place them directly above the IC, centered and clear of pins.
- Preserve enough right-side margin for the full IC name/value to remain readable; never let the name be clipped by the body edge, pin field, or nearby wire/label.
- When pin numbers are shown inside an IC body, reserve a clear right-side margin so the numbers remain legible and do not collide with the IC name or pin wires.
- Hide pin-name annotations when they make the IC body unreadable; pin identity remains available in KiCad and the netlist.
- Use the physical pin numbers from the device datasheet and verified KiCad package symbol as the authoritative pin mapping. Do not infer connectivity from pin-name order alone.
- For every IC, lay out physical pin numbers sequentially around the symbol with pin 1 at the upper-left, pin 2 directly below pin 1, pin 3 directly below pin 2, and so on down that side before continuing around the package. Follow the datasheet/package orientation consistently.
- Exception: when a matching built-in KiCad symbol exists, use the built-in symbol rather than creating a custom visual pin arrangement. In that case, verify its physical pin numbers and connectivity against the datasheet/package and preserve KiCad's native symbol geometry.
- Use real KiCad 9 symbol mappings and explicit footprints. Do not silently substitute a different device with incompatible pins.

## Intentional No-Connects

- Mark only genuinely unused pins as no-connects.
- Never use no-connect handling to hide a failed route or an unknown connection.
- Unused decoder outputs, unused driver channels, and intentionally unused relay contacts may be no-connects when confirmed by the design.

## Required Validation

Every generation run must perform all of these checks:

1. Compile the generator with `python -m py_compile tools/generate_schematic.py`.
2. Run the generator from the repository root.
3. Have KiCad CLI render the root schematic to PDF. Generation fails if KiCad cannot load any hierarchical child sheet.
4. Run KiCad ERC through the CLI with `--exit-code-violations`. Electrical pin, power, short, and dangling-wire violations fail generation; known external-interface and KiCad embedded-library diagnostics must remain visible in the report and must not be silently suppressed.
5. Check for grey ERC/dangling markers. Unexpected unconnected pins, dangling wire endpoints, undriven power pins, and unconnected labels must fail generation. Intentional no-connect markers are allowed only for pins explicitly marked unused in the source model.
6. Export a KiCad netlist and inspect critical nets and components, especially:
   - PIC16F18855 pin assignments
   - FAN_PWM -> Q1 gate
   - Q1 drain -> FAN1 negative
   - FAN1 positive -> +12V
   - Q1 source -> GND
   - TEMP_ADC between the MCU and thermistor divider
7. Reject unresolved references such as `U?`, `R?`, or `C?` in placed instances.
8. Reject diagonal wire segments.
9. Reject overlapping label bounding boxes.
10. Reject labels inside IC protected envelopes.
11. Reject IC reference/value fields outside the body or directly-above placement rule.
12. Confirm all generated child sheets are present and referenced by the root sheet.
13. Load and save moved sheets through `kicad-sch-api`, then rerun KiCad PDF export, ERC, and netlist validation.

ERC alone is insufficient. ERC validates electrical topology, but it does not detect wires crossing symbol graphics, labels overlapping text, diagonal routing, poor placement, or unreadable page layout. KiCad CLI rendering and the visual geometry checks are mandatory.
