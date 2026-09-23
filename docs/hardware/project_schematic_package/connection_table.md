# Functional Netlist – Amplifier Protection Board

The machine-readable netlist is **[connection_table.csv](connection_table.csv)**. That CSV is
the single authoritative component-to-component connection list for this board.

> **Do not restate the netlist or pin assignments in prose.** Pin assignments live in
> [../PIC18F47Q10_pin_map_and_setup.md](../PIC18F47Q10_pin_map_and_setup.md); nets live in the CSV. Duplicating
> either is what allowed the band-select, LCD, and comparator-reset drift found on 2026-09-21.

## Using the CSV

Columns are `From,To,Net,Notes`.

- `From` and `To` are `RefDes.Pin` (for example `U1.RD2`, `U2.IN1`, `K1.1`)
- `Net` is the net label to use during schematic capture
- `Notes` carries intent that is not obvious from the net name

## Conventions

- Power nets: `+12V`, `+5V`, `GND`
- Band select: one MCU output per band, nets `BAND_160M` … `BAND_10M`. No decoder, no B0–B2 address bus
- Relay coils: nets `COIL_160M` … `COIL_10M`
- Flyback diode rows are listed per relay
- The band-snoop input is the Timer1 T1CKI signal; it takes no pull-up

## Related

- Component list: [component_list.csv](component_list.csv)
- Capture order: [wiring_checklist.md](wiring_checklist.md)
- Pin assignments (single source of truth): [../PIC18F47Q10_pin_map_and_setup.md](../PIC18F47Q10_pin_map_and_setup.md)
