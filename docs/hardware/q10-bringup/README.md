# PIC18F47Q10 bring-up: first real simulator run

Date: 2026-09-22 · updated 2026-09-23 (the Q10 is now the only device; the branch named below is gone)

## rate_probe_macos.mdb - measure the simulator's instructions per firmware millisecond

Run it with:

```
python tools/simulate/run_mdb_probe.py docs/hardware/q10-bringup/rate_probe_macos.mdb
```

**Why it exists.** The harnesses convert "advance N simulated milliseconds" into a `Stepi` count
using a constant (`INSTRUCTIONS_PER_MS`), and the constants in the repo do not agree:
`trace_ptt_sequence.py` / `first_dit_invariants.py` use 1625, `test_first_dit.py` uses 1887, and the
Windows-era probe recorded ~8000 for the 16F at 32 MHz. A wrong constant does not mis-time an
assertion slightly - it changes how much firmware time each sample advances, which is exactly what
makes a 40 x 1 ms assertion window pass on one host and fail on another.

**The clock is part of the question** (user instruction, 2026-09-23): this part runs a 64 MHz core
(`RSTOSC = HFINTOSC_64MHZ`) with Timer2 fed from Fosc/8, 1:64 prescale, `PR2 = 124`, and that is what
makes the firmware's tick 1.000 ms. The simulator's steps-per-simulated-ms is a property of the MDB
model, not of the datasheet clock, so it must be *measured* - but the script prints the clock chain
(`OSCCON1`, `OSCFRQ`, `T2CLK`, `PR2`) into the same log, so a mismatch between what the firmware
configured and what the model assumes is visible rather than inferred.

**Method.** Read the firmware's own 1 ms counter, step a known number of instructions, read it again.
Two independent counters are used - `g_band_cache_idle_ms` across four bracketed `Stepi` blocks, and
the 1000 ms startup inhibit - so one wrong reading cannot carry the answer on its own.

**`.mdb` scripts have NO comment syntax.** A `;` line is executed as a command and MDB fails with
`Undefined command` (exit 255). Keep these scripts comment-free and document them here.

### Result, macOS 2026-09-23

Read after stepping past init (`Stepi 300000`), so these are the firmware's values and not the reset
defaults (reading them immediately after `program` answers `T2CLK=0`, `PR2=255`, which reads like a
configuration that never took effect):

| Register | Value | Meaning |
|---|---|---|
| `T2CLK` | 2 | Fosc/8, as `timer0_init()` writes |
| `PR2` | 124 | as written, `(124+1) * 64 / 8 MHz` = 1.000 ms |
| `OSCCON1` | 0 | not conclusive: the model does not report the oscillator selection |
| `OSCFRQ` | 0 | same |

Rate, from `g_startup_inhibit` (clears 1000 firmware-ms after the tick starts) bracketed by eight
`Stepi 250000` blocks: it was still `true` at 1.80M instructions and `false` at 2.05M, i.e. the
1000 ms boundary lies between 1.50M and 1.75M instructions after the init step.

**~1500-1750 instructions per firmware millisecond**, which corroborates the 1625 in
`trace_ptt_sequence.py` and does NOT support the 1887 in `test_first_dit.py` - those two constants
disagree by ~16%, and a 16% error in the conversion is enough to move a 40 x 1 ms assertion window's
end past or short of the event it is waiting for. Note also that `g_band_cache_idle_ms` is NOT a
1 ms counter (it climbs ~4 counts per firmware-ms once it is running) and stays at 0 until the band
cache exists, so it is the wrong counter to bracket.

## tick_rate_probe.mdb - the tick rate, measured (2026-09-24)

Run it with:

```
python tools/simulate/run_mdb_probe.py docs/hardware/q10-bringup/tick_rate_probe.mdb
```

`rate_probe_macos.mdb` above bracketed a *boolean* (`g_startup_inhibit`) and could only say the
1000 ms boundary lay somewhere in a 250,000-step window. This probe brackets the firmware's own tick
**counter** instead - `g_startup_elapsed_ms`, incremented once per Timer2 interrupt the main loop
drains - so every reading is a tick count, not a yes/no.

Result, macOS 2026-09-24, against `out/My_Pic_Project_18F47Q10/default.elf`:

| Steps | `g_startup_elapsed_ms` | ticks in that block |
|---|---|---|
| 300,000 | 0 | tick not yet running (LCD boot precedes `timer0_init()`) |
| 600,000 | 381 | 381 |
| 900,000 | 559 | 178 |
| 1,200,000 | 734 | 175 |
| 1,500,000 | 912 | 178 |
| 1,800,000 | 1000 (capped) | inhibit cleared |

**531 ticks per 900,000 steps = 1694.9 `Stepi` steps per firmware millisecond** (~1695, ±1% block to
block). `T2CON` read back `224` = `ON`, `CKPS = 6`, `OUTPS = 0`, so the tick really is 1.000 ms and
the steps are the only unknown. This replaces both disputed constants: 1625 is ~4% low, 1887 ~11%
high, and the 16.5M-step `BOOT_STEPS` in `probe_q10_ptt_path.py` is ~10x too large.

**Do not use `TMR2` as a clock in the simulator.** It advanced only ~16 counts per 300,000 steps
(177 firmware-ms) - impossible for the configured Fosc/8 and 1:64 - even though the overflow
interrupt arrives on schedule. The interrupt count is trustworthy; the model's timer *count* is not.

## Why this exists

The Q10 port had been through several rounds of "the simulator can't do it" verdicts, each of
which turned out to be firmware configuration nobody had written (an assumed `T2CLKCON` value,
then a missing `IPEN`/priority enable). Nothing in the port had ever actually *run* on the Q10
model - the image only linked. This probe ran it.

`q10_probe.c` writes only values read out of `PIC18F-Q_DFP/1.30.487`'s `pic18f47q10.h`, never
from memory, and sets up the same six things the firmware depends on. `probe.mdb` drives it;
`probe_results.log` is the raw MDB transcript it produced.

## What was measured

| Assumption carried in the firmware | Measured on the PIC18F47Q10 model | Verdict |
|---|---|---|
| `T2CLK = 0x01` (Fosc/4) makes Timer2 count | `T2TMR` moved 33 → 409 → … across `Stepi` steps | holds |
| `IPEN = 1` + `IPR4bits.TMR2IP = 1` dispatches interrupts | `g_isr_any` 0 → 2 → 5 as the tick ran | holds |
| `PR2 = 124` with `CKPS = 6` gives a 1.000 ms tick | 3 ticks per 40000 `Stepi` steps ≈ 13.3 k steps/tick | holds |
| `T1CKIPPS = 0x19` is accepted for RD1 | read back `25` | holds |
| PTT on RC0: `ANSELCbits.ANSELC0 = 0`, pull-up on | `ANSELC = 254` (bit 0 cleared), `WPUC = 1` | holds |
| The NVM unlock + `WR` sequence completes | `g_nvm_done = 1`, `NVMDATL` read back `165` (0xA5) | holds |

Reproduce with:

```powershell
$dfp = 'C:\Program Files\Microchip\MPLABX\v6.35\packs\Microchip\PIC18F-Q_DFP\1.30.487\xc8'
& 'C:\Program Files\Microchip\xc8\v4.00\bin\xc8-cc.exe' -mcpu=18F47Q10 "-mdfp=$dfp" `
  -O1 -gdwarf-3 -std=c99 q10_probe.c -o q10_probe.elf
& 'C:\Program Files\Microchip\MPLABX\v6.35\mplab_platform\bin\mdb.bat' probe.mdb
```

## Findings worth keeping

- **`NVMCON1` has no `WREN` bit on this device.** Its members are `RD`, `SECRD`, `WR`, `SECWR`,
  `SECER`. The (since deleted) `Eeprom-changes.md` draft named `WREN`, `NVMCMD`, `NVMCON0bits.GO`
  and `INTCON0`; none of those exist here. Take the *procedure* from the corrected
  `firmware/src/nvm.c`, the *bit names* from the DFP header.
  Writing `NVMCON1bits.WREN` fails to compile - which is how this got caught, twice.
- **MDB scripts may not contain comments.** `//` and `;` are both reported as
  `Undefined command` and MDB exits `-1` before executing a single line, which looks exactly like
  a broken toolchain. Put the explanation in the `.c` file. The working template is
  `_build/spike_q10_retest/ab.mdb`: `device`, `hwtool sim`, `program`, then `Stepi` (capital S).
- **XC8 ignores `-o foo.o`** and always emits `<stem>.p1` beside the output, so a link step must
  name the `.p1` intermediates.
- **Instruction rate needs recalibrating for Q10.** `tools/simulate/test_first_dit.py` assumes 8000
  instructions/ms from the 16F era. The probe measured roughly 6000-6900 instructions per
  simulated tick against a 1.000 ms `PR2` tick, so the Q10 figure is lower and must be measured
  before any Q10 timing assertion is trusted.

## What this does *not* establish

The probe ran six specific assumptions, not the firmware. The full image has still never been
executed on the Q10, and none of the analogue path (comparators, DAC gap flagged by
`W9602-COMP`), the ADC scan, or the PPS *output* assignments for the band relays has been
exercised on this device. The probe is the positive control those findings now need.

## Follow-up: the full firmware image, on Q10 (2026-09-22, later the same day)

`q10_firmware.elf` in this directory is the **actual firmware** - all four translation units,
`-mcpu=18F47Q10`, 317Ah / 12,666 bytes - and `firmware_run.mdb` / `firmware_run_results.log` are
the script that stepped it on the model and the transcript it produced.

It boots. It reaches `g_state = 5` (`STATE_RESET_WAIT`) through the main loop without crashing, and
the analogue-select and direction registers come up exactly as the 16F design intends
(`ANSELA = 47`, `ANSELB = 14`, `ANSELC = 0`, `ANSELD = 0`, `TRISC = 5`). So the port's
initialisation sequence survives contact with the device.

It also surfaced something worth acting on. After 200,000 steps the timer registers read
`T2CON = 0`, `PR2 = 255`, `T2CLK = 0`, `OSCCON1 = 0`: **the system tick is not running yet.**
That is an ordering fact, not a port defect - `main()` calls `adc_init()`, `load_settings()`,
`lcd_init()` and `show_boot_message()` *before* `timer0_init()`, and the LCD boot path is slow
enough that the sample lands first. Two things follow:

1. When asking "does the tick run" of any early sample, sample past `timer0_init()` - a zero
   `T2CON` early means "not initialised", not "broken".
2. More importantly, on the real product the 1 ms protection tick is armed *after* the LCD boot
   sequence. A stall in `lcd_init()`/`show_boot_message()` therefore leaves the amplifier with no
   periodic supervision during startup. That ordering deserves a deliberate review on hardware,
   independently of the Q10 port.

Still not exercised on Q10: the ADC scan, the PPS input path's *effect* (only the register
write was checked), the band-settle and trip timing under the real 64 MHz clock, and the LCD
timing itself.

