---
description: "Use when editing PicAmpControl firmware C sources or headers under firmware/: bare-metal PIC18 register rules, ISR discipline, config words and device facts, and the hardware traps that have already cost debug cycles."
applyTo: "firmware/**"
---
# Firmware rules (PIC18F47Q10, XC8)

Merged from `deepseek-pic.md` (another agent's checklist, deleted 2026-09-24) plus the traps this
project has paid for. These apply when firmware source is edited or written; none of it can affect a
build or a test, because XC8 is invoked directly and needs none of it.

## Registers

- **Write outputs through `LAT`, read inputs from `PORT`.** `pin_map.h` holds the write macros, and the
  three TX outputs also carry `SENSE_TX*` pin-level read macros, used by the two checks that must
  confirm the hardware actually reached a state (`release_band_if_cold()`, and the `PTT COMPLETE`
  condition) rather than trusting the latch.
- **Never write a whole port.** On PORTC the relay lines share a port with the LCD data lines, so a
  `PORTCx` read-modify-write can clobber a relay latch from an unrelated write. Do not reintroduce
  `PORTxbits` writes for outputs.
- **Never guess a register or bit name.** Take both names and values from the installed DFP
  (`PIC18F-Q_DFP/1.30.487`): `xc8/pic/include/proc/pic18f47q10.h` for members, and
  `xc8/pic/dat/cfgmap/18f47q10.cfgmap` for configuration values. `NVMCON1` has no `WREN` bit on this
  part; writing one fails to compile, which is how the `NVMCON1`/`NVMCON0` bit-name mistake was caught.
- `main.c` clears `ANSELC` explicitly so RC0 and RC3-RC7 behave as digital I/O. Keep that
  initialisation whenever the port map changes.

## Interrupts

- Keep every ISR minimal: clear the flag, update a `volatile` global, and nothing else. No
  `__delay_*`, no heavy maths, no peripheral re-arming.
- Every global written in an ISR and read in the main loop MUST be `volatile`.
- The ~1 ms scheduler tick runs on Timer2. Re-arming a conversion inside the tick ISR has already
  starved the main loop once (the ADC conversion-complete re-arm); if the CPU looks stuck at the
  interrupt vector, that class of bug is back.

## Clock and config

- The clock chain is fixed and deliberate: `RSTOSC = HFINTOSC_64MHZ` (the internal oscillator's
  maximum - the part has no 32 MHz setting), Timer2 `T2CLK = Fosc/8` (8 MHz) with `PR2 = 124` for the
  1.000 ms tick, and `_XTAL_FREQ = 64000000UL` in `pin_map.h` matching the real core (it had been
  left at 32 MHz; fixed 2026-09-24).
- XC8 compiles `__delay_us`/`__delay_ms` from `_XTAL_FREQ`, so it must match the 64 MHz core or the
  LCD init, page-clear and ADC-acquisition delays run at the wrong length. It now does.
- Never guess a configuration word. Derive it from the DFP's cfgmap, and leave the pragma block at the
  top of `main.c` as the one place they are declared.
