# PIC18F47Q10 hardware fit: PDIP-40 pinout comparison

Date: 2026-09-22 · Branch: `upgrade/pic18f47q10`

## Question

Does the PIC18F47Q10 fit the existing PIC16F18875-I/P board, or does the board need a respin?

## Method

Both pinouts were read from the part's own documentation, not from memory or from a family
assumption:

- **Q10**: the pin diagram in `PIC16(L)F18855-75-Data-Sheet-40001802H.pdf` (the 40-pin
  SPDIP/PDIP diagram), extracted with `pypdf`.
- **16F18875**: `docs/hardware/PIC16F18875_pin_map.md`, the project's authoritative pin table.

Compared pin by pin, positions 1-40.

## Result

**39 of 40 pins are identical.** The single difference is pin 1:

| Pin | PIC16F18875-I/P | PIC18F47Q10-I/P |
|-----|-----------------|-----------------|
| 1 | RE3 | VPP/MCLR/RE3 |

Both parts use pin 1 as RE3; the Q10 additionally exposes the programming voltage and master
clear on that pin. The project drives MCLR as `MCLRE = EXTMCLR` on Q10 against `MCLRE = ON` on
16F, and pin 1 is the only pin whose *function* differs.

Every pin the design actually uses maps to the same physical position:

| Function | 16F pin | Q10 pin |
|---|---|---|
| LCD RS / E / D4 | RA4 (6) / RA6 (14) / RA7 (13) | same |
| LCD D5 / D6 / D7 | RC3 (18) / RC4 (23) / RD0 (19) | same |
| TX / TX_VCC / TX_BIAS + SENSE | RC5 (24) / RC6 (25) / RC7 (26) | same |
| PTT | RC0 (15) | same |
| Encoder A / B / switch | RC2 (17) / RB0 (33) / RB6 (39) | same |
| Frequency counter T1CKI | RD1 (20) | same |
| Comparator reset | RC1 (16) | same |
| Fan PWM / trip status | RB5 (38) / RB7 (40) | same |
| Overcurrent fault In | RB4 (37) | same |
| Band relays 160m-10m | RD2-RD7 (21,22,27,28,29,30) | same |
| ADC channels (5 analog) | RA0-RA3, RA5, RB1-RB3 | same |

The ADC channel *numbers* are unchanged too, so `ADC_*_CHANNEL` constants in `pin_map.h` stay
valid on Q10.

## Conclusion

The Q10 is a **pin-compatible drop-in for the 40-pin PDIP footprint**, with one caveat on pin 1's
extra programming/MCLR function. No board respin is required for the pinout.

## What this does NOT establish

Pin *positions* matching does not mean every peripheral behaves the same. Specifically still
unverified on Q10:

- **PPS output routing** for the band relays. All the pins the design uses do have PPS output
  registers on Q10 (`RD0PPS`..`RD7PPS`, `RC0PPS`..`RC7PPS`, `RB0PPS`/`RB5PPS`/`RB7PPS` all
  exist), but the design currently drives the relays as plain LAT outputs, and the Q10's
  *input* code for T1CKI was `0x19` while its *output* code space is a different table that has
  not been checked. If any relay path is moved to PPS, its code must come from the Q10's
  output-source table, not the 16F's.
- **Analog accuracy**: the Q10's ADC and the two comparators, including the DAC gap recorded
  against `W9602-COMP`.
- **Drive strength and electrical limits** per pin, which is a datasheet-reading exercise against
  the actual relay/LCD loads (see `docs/hardware/bench-validation.md`).
