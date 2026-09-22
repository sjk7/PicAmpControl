# PIC18F47Q10 bring-up: first real simulator run

Date: 2026-09-22 · Branch: `upgrade/pic18f47q10`

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
  `SECER`. `Eeprom-changes.md` names `WREN`, `NVMCMD`, `NVMCON0bits.GO` and `INTCON0`; none of
  those exist here. Take the *procedure* from that file, the *bit names* from the DFP header.
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

