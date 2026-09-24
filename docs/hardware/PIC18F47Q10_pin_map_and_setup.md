# PIC18F47Q10 — pin map and device setup

Date: 2026-09-23

This file is written for someone reading the project cold: it states, in one place, (1) what every
pin does and (2) how the PIC is configured. **The PIC18F47Q10 is the shipping target and the only
device in this project** (2026-09-23; the PIC16F18875 port was removed - see `Ai-Notes.txt`). See
`docs/hardware/q10-pinout-compatibility.md` for the pin-by-pin fit check against the old 16F board
(39 of 40 pins identical; only pin 1 differs: `VPP/MCLR/RE3` on the Q10).

---

## 1. Pin assignments

All assignments come from `firmware/include/pin_map.h`, which is the single source of truth for
functional pin roles. PDIP pin numbers are the Q10's and are taken from
`docs/hardware/q10-pinout-compatibility.md` (cross-check against the Q10 datasheet before relying
on a number in isolation).

### 1.1 Outputs (written via LAT, never PORT)

| Pin | PDIP | LAT macro | Function |
|---|---|---|---|
| RA4 | 6 | `OUTPUT_LCD_RS`  | LCD register-select |
| RA6 | 14 | `OUTPUT_LCD_E`   | LCD enable (⚠ also CLKOUT/OSC2 — see §2) |
| RA7 | 13 | `OUTPUT_LCD_D4`  | LCD data D4 |
| RC3 | 18 | `OUTPUT_LCD_D5`  | LCD data D5 |
| RC4 | 23 | `OUTPUT_LCD_D6`  | LCD data D6 |
| RD0 | 19 | `OUTPUT_LCD_D7`  | LCD data D7 |
| RC5 | 24 | `OUTPUT_TX`      | TX key output (active-low) |
| RC6 | 25 | `OUTPUT_TX_VCC`  | TX +12 V rail (active-low) |
| RC7 | 26 | `OUTPUT_TX_BIAS` | TX bias rail (active-low) |
| RC1 | 16 | `OUTPUT_COMP_RESET` | Comparator latch reset |
| RB5 | 38 | `OUTPUT_FAN_PWM` | Fan PWM |
| RB7 | 40 | `OUTPUT_TRIP_STATUS` | Trip status LED/line |
| RD2 | 21 | `OUTPUT_BAND_160M` | 160 m band relay |
| RD3 | 22 | `OUTPUT_BAND_80M`  | 80 m band relay |
| RD4 | 27 | `OUTPUT_BAND_40M`  | 40 m band relay |
| RD5 | 28 | `OUTPUT_BAND_20M`  | 20 m band relay |
| RD6 | 29 | `OUTPUT_BAND_15M`  | 15 m band relay |
| RD7 | 30 | `OUTPUT_BAND_10M`  | 10 m band relay |

All TX sequencing outputs (`OUTPUT_TX`, `OUTPUT_TX_VCC`, `OUTPUT_TX_BIAS`) are **active-low by
default**. Band-relay outputs are active-high, one dedicated pin per band.

### 1.2 Inputs (read via PORT)

| Pin | PDIP | PORT macro | Function |
|---|---|---|---|
| RC0 | 15 | `INPUT_PTT` | Push-to-talk (active-low) |
| RC2 | 17 | `INPUT_ENCODER_A` | Rotary encoder A |
| RB0 | 33 | `INPUT_ENCODER_B` | Rotary encoder B |
| RB6 | 39 | `INPUT_ENCODER_SWITCH` | Encoder push switch |
| RD1 | 20 | `INPUT_FREQ_COUNTER` | Timer1 frequency-counter input (T1CKI via PPS) |
| RB4 | 37 | `INPUT_OVERCURRENT_FAULT` | Overcurrent fault input |

### 1.3 Sense read-back (the PORT read of the TX outputs)

The firmware must confirm a relay has *actually* reached its state before it may move the next
relay or show `PTT COMPLETE`, so it reads the PORT (not LAT) of the TX lines:

| Pin | PDIP | Sense macro | Mirrors |
|---|---|---|---|
| RC5 | 24 | `SENSE_TX`     | `OUTPUT_TX` |
| RC6 | 25 | `SENSE_TX_VCC` | `OUTPUT_TX_VCC` |
| RC7 | 26 | `SENSE_TX_BIAS`| `OUTPUT_TX_BIAS` |

### 1.4 Analogue inputs (the ADCC scan)

Eight channels are scanned round-robin at one channel per 1 ms tick. Channel numbers are Q10 ADCC
channel codes (`ADPCH`), unchanged from the 16F design:

| ADC channel | Pin | PDIP | Constant | Signal |
|---|---|---|---|---|
| 0  | RA0 | 2  | `ADC_SWR1_FWD_CHANNEL`   | SWR1 forward |
| 1  | RA1 | 3  | `ADC_SWR1_REF_CHANNEL`   | SWR1 reflected |
| 2  | RA2 | 4  | `ADC_SWR2_FWD_CHANNEL`   | SWR2 forward |
| 3  | RA3 | 5  | `ADC_SWR2_REF_CHANNEL`   | SWR2 reflected |
| 5  | RA5 | 7  | `ADC_TEMP_CHANNEL`       | **Temperature (NTC)** |
| 9  | RB1 | 34 | `ADC_CURRENT_CHANNEL`    | Drain current |
| 10 | RB2 | 35 | `ADC_OVERDRIVE_CHANNEL`  | Overdrive |
| 11 | RB3 | 36 | `ADC_DRAIN_PEAK_CHANNEL` | Drain peak voltage |

Channel 4 (RA4) is deliberately skipped: RA4 is the digital `OUTPUT_LCD_RS` line. `ANSELA` keeps
RA4 digital (`ANSELA &= ~0x10`).

---

## 2. Device setup

### 2.1 Configuration words

Configuration pragmas live at the top of `firmware/src/main.c`. PIC18F47Q10 is the only device, so
they are unconditional (the 16F branches were removed on 2026-09-23). Authoritative names/values
come from the DFP's `18f47q10.cfgmap`, not from memory.

| Setting | Value (PIC18F47Q10) |
|---|---|
| FEXTOSC | `OFF` |
| RSTOSC (reset oscillator) | `HFINTOSC_64MHZ` |
| WDTE | `OFF` |
| PWRTE | `OFF` |
| CLKOUTEN | `OFF` |
| MCLRE | `EXTMCLR` |
| CP | `OFF` |
| BOREN | `ON` |
| BORV | `VBOR_190` |

(For the record, the values the removed 16F build used are preserved in
`prototype_reference/docs/hardware/PIC16F18875_pin_map.md`.)

Two Q10-only traps already hit and recorded in the skill / `bugfixes.md`:

- **`RSTOSC`**: the Q10 config map has only `HFINTOSC_64MHZ` and `HFINTOSC_1MHZ` — no `HFINT32`.
  Landing on 1 MHz runs the whole design at 1/32 clock and stretches the 1 ms tick, every
  band-settle delay and the trip response by 32×. The port selects 64 MHz and keeps the design
  clock honest at 32 MHz by feeding Timer2 from Fosc/8.
- **`CLKOUTEN`**: on the Q10 the default is *enabled*, and RA6 doubles as CLKOUT/OSC2. RA6 is
  `OUTPUT_LCD_E`, so the default silently hands the LCD enable line to the clock-output function
  and the panel never latches. `CLKOUTEN = OFF` is set unconditionally in `main.c`.

### 2.2 Clock

- Internal oscillator: **HFINTOSC at 64 MHz** (the Q10's highest internal rate).
- `_XTAL_FREQ` is kept at **32 MHz** so all existing delay/baud maths is unchanged.
- Timer2 is clocked at **Fosc/8 = 8 MHz** (`T2CLK = 0x02`), prescale 1:64 (`CKPS = 6`),
  `PR2 = 124` → a **1.000 ms system tick**.

### 2.3 Interrupts

This part needs the **priority** interrupt form:

- `INTCONbits.IPEN = 1` (priority enabled) — with `IPEN = 0` no interrupt ever reaches the ISR,
  even with the source enable and flag set.
- `IPR4bits.TMR2IP = 1` (system tick at high priority).
- Global `INTCONbits.GIE = 1`.

The single `__interrupt()` ISR services the Timer2 tick (increments `g_timer_ticks_pending`) and
the ADC conversion-complete interrupt (`PIR1bits.ADIF`), storing each sample into the
`g_adc_samples[]` ring by channel index. It is deliberately minimal — no delays, no heavy maths.

### 2.4 ADCC (analogue-to-digital converter)

The Q10 peripheral is the **ADCC** (computational ADC), not the 16F's 10-bit ADCC-less ADC. `adc_init()`
configures it as follows (this is the working-tree state on this branch, uncommitted):

```c
FVRCON = 0x00;
ANSELA = 0x2F;  ANSELA &= ~0x10;   // RA0-RA3,RA5 analogue; RA4 stays digital (LCD RS)
ANSELB = 0x0E;                     // RB1-RB3 analogue
ADCON1 = 0x20;                     // ADCC guard/precharge control - ADFM is NOT here on this part
ADPCH  = 0;
ADCON0 = 0x88;                     // ADON=1, ADCS=0 (Fosc-derived), single conversion
ADCON0bits.ADFM = 1;               // result format: right-justified (ADCON0<2>, a single bit)
PIR1bits.ADIF = 0;  PIE1bits.ADIE = 1;  INTCONbits.PEIE = 1;
__delay_us(ADC_ACQUISITION_US);
ADCON0bits.GO_nDONE = 1;
```

Q10 ADCC register layout (from `PIC18F-Q_DFP/1.30.487/xc8/pic/include/proc/pic18f47q10.h`):

| Register | Key fields |
|---|---|
| `ADCON0` | `ADON`(7), `ADCONT`(6), `ADCS`(5·4), `ADFM`(2), `ADGO`(0) |
| `ADCON1` | `ADDSEN`, `ADGPOL`, `ADIPEN`, `ADPPOL` (guard/precharge, all unused) |
| `ADCON2` | `ADMD`(2:0) mode, `ADACLR`(3), `ADCRS`(6:4) accumulator right-shift, `ADPSIS`(7) |
| `ADCON3` | `ADTMD`(2:0) threshold mode, `ADSOI`(3), `ADCALC`(6:4) accumulator |
| `ADREF` | `ADPREF`(1:0) positive ref, `ADNREF`(4) negative ref |
| `ADPCH` | `ADPCH`(5:0) channel select |
| `ADRES` | 16-bit result (`ADRESH` @ 0xF5F, `ADRESL` @ 0xF5E) |

**`ADFM` is a single bit (`ADCON0<2>`), not a 2-bit field**, and `0` means *left*-justified while `1`
means *right*-justified. The `ADCON1 = 0x20` above therefore writes guard/precharge and polarity
bits, NOT a justification field: the 16F's `ADCON1<7:6>` ADFM field does not exist on this part.

There is **no `ADREF` write and none should be added** — the Q10 reset default (`ADPREF=00`) is the
`VDD`/`VSS` reference the design assumes.

### 2.5 Other peripherals

- **Timer1** frequency counter on RD1, input routed via PPS (`T1CKIPPS = 0x19`).
- **NVM / EEPROM**: the Q10 has no `WREN` bit in `NVMCON1` (members are `RD`, `SECRD`, `WR`,
  `SECWR`, `SECER`) — see `docs/hardware/q10-bringup/README.md`.
- **Comparators** (overcurrent safety path): MPLAB X 6.35 flags `W9602-COMP` ("DAC Voltage Source
  Peripheral not yet implemented to act as input to Comparator"); not yet exercised on the model.

---

## 3. The temperature-reading fault — RESOLVED (kept as the record of how it was found)

**Fixed and verified 2026-09-22; the analysis below is history, NOT an open problem.** Two changes in
`firmware/src/main.c`, both now unconditional (the device guards were removed on 2026-09-23):
1. `adc_init()` sets `ADCON0bits.ADFM = 1` — `ADFM` is a single bit (`ADCON0<2>`) and defaults to
   LEFT-justified, which left the result sitting in `ADRES<15:6>`.
2. The ADC ISR downscales once at capture — `sample >>= 2` — because the ADCC is **12-bit** while
   every conversion function (`temperature_c()`, `drain_voltage()`, `overdrive_power_mw()`,
   `current_amperes()`, the SWR maths) treats the raw value as 10-bit. Measured: 2.5 V read 2048 raw
   and `temperature_c(2048)` returned the 150C sentinel.

The subsections below are the original bring-up notes; the transferable part is the method - read
the register back and measure the result width, do not assume it from the 16F.

### 3.1 Symptom

On the Q10, the amplifier trips as soon as PTT asserts: `g_state = STATE_TRIP(3)`,
`g_fault_latched = true`, `g_trip_reason = 0x10` (**TEMPERATURE only**), and
`g_live_temperature_c = 150` — the fault sentinel — while the temperature pin is driven to 2.5 V,
which should read ≈ 25–30 °C. Current, overdrive and drain all read 0 correctly.

### 3.2 The conversion path

`temperature_c()` assumes its `raw` argument is a **10-bit** value (0–1023):

```c
unsigned int temperature_c(unsigned int raw) {
    const unsigned char *table = g_ntc_adc[g_thresholds.temp_b_profile];
    raw >>= 2;                 // 10-bit -> 8-bit table index
    if (raw > 250) return 150; // 150 = fault sentinel
    ...
}
```

The same 0–1023 assumption is baked into `drain_voltage()` (`/1023`) and
`overdrive_power_mw()` (`/1023`).

### 3.3 Why the ADFM fix (already applied) is likely *not* sufficient

The working tree sets `ADCON0bits.ADFM = 1` (right-justified). That fixes *justification*, but the
Q10 ADCC result is **12-bit**, not 10-bit. The two problems combine:

| Justification | 2.5 V on a 12-bit ADCC | `temperature_c()` result |
|---|---|---|
| Left (ADFM=0, the bug) | `512 << 4 = 8192` in `ADRES` | `8192 >> 2 = 2048 > 250` → **150** |
| Right (ADFM=1, the fix) | `2048` in `ADRES` | `2048 >> 2 = 512 > 250` → **150** |

Both return 150. The ADFM fix corrects where the 12-bit result sits in the 16-bit `ADRES`, but it
does **not** convert the 12-bit result to the 10-bit scale the conversion functions expect.
`temperature_c(2048)` still trips.

**Confirmed by measurement** (2026-09-22, `docs/hardware/q10-bringup/temp_probe.c` run under MDB):
2.5 V on RA5 → `ADRES = 2048` (`ADRESH = 0x08`, `ADRESL = 0x00`), `ADCON0 = 0x84` (ADON=1,
ADFM=1), `ADPCH = 5`. The ADCC is 12-bit and `ADFM=1` right-justifies correctly — but the 10-bit
scaling in `temperature_c()` still trips. The fix is the right-shift below, not further
justification work.

### 3.4 The actual fix

The result must be scaled **12-bit → 10-bit** before it reaches the conversion functions. Two
equivalent options:

1. **Right-shift the raw result by 2** at the point of capture (in the ISR, or immediately after
   `ADRES` is read), so every downstream function keeps its 10-bit contract untouched:
   `sample = (unsigned int)ADRES >> 2;`
2. **Convert the functions to 12-bit**: make `temperature_c()` do `raw >>= 4` and change
   `drain_voltage()` / `overdrive_power_mw()` / `current_amperes()` / the SWR maths from `/1023`
   to `/4095`.

Option 1 is smaller and keeps the 16F path (already 10-bit, right-justified, no extra shift needed)
and the Q10 path (12-bit, shift by 2) identical in effect — a device-guarded `#if
defined(__18F47Q10__)` shift.

### 3.5 If it still reads 150 after the resolution fix — check, in order

This is the troubleshooting list for the case where the obvious fixes do not clear the trip. Work
through it with `tools/simulate/probe_q10_ptt_path.py` (extended to print `ADCON0/1/2/3`, `ADRES`,
`ADPCH`), which writes `_build/My_Pic_Project/sim/q10_ptt_probe_report.txt`.

1. **Confirm the raw `ADRES` for 2.5 V.** 10-bit ⇒ ≈512; 12-bit ⇒ ≈2048; left-justified 12-bit ⇒
   ≈32768. The number tells you exactly which of the three cases you are in — do not guess from the
   derived `g_live_temperature_c` alone.
2. **Confirm `ADCON0` justification bit.** `ADFM=1` must read back set. A reset, an accidental
   whole-register write, or a stray `ADCON0 = 0x88` *after* the `ADFM = 1` line would clobber it.
3. **Confirm the channel.** `ADPCH` must be 5 when the temperature sample is captured, and the scan
   must not have the temp channel mapped to the wrong pin. `g_adc_scan_channels[4]` must be `5`.
4. **Confirm the reference.** `ADREF` must stay at reset (`ADPREF=00` = `VDD`/`VSS`). If some code
   wrote `ADPREF=11` (`FVRCON` internal reference) while `FVRCON=0` sets the fixed reference to
   ≈1.024 V, then 2.5 V would read full-scale (or clip) on every channel.
5. **Confirm `ADCON2.ADMD` = basic mode (000).** A non-zero mode (Burst Average / Low-Pass Filter /
   Threshold / Accumulate) changes what `ADRES` holds, and `ADCRS`/`ADCALC` shift/accumulate it, so
   a "right" `ADRES` that has been filtered or accumulated will not match the raw 2.5 V prediction.
6. **Confirm the NTC table/profile.** If `g_thresholds.temp_b_profile` indexes a table whose first
   entries are above the raw value, `temperature_c()` returns 0, not 150 — so a *low* reading
   points at the profile/table, whereas a *150* reading points at the raw value exceeding 250 after
   the shift (i.e. §3.3/§3.4, or the `ADRES` reading itself being wrong).
7. **Confirm the acquisition time.** If `ADACQ`/the `__delay_us(ADC_ACQUISITION_US)` is too short
   for the Q10 at 64 MHz, the sample is taken before the S/H settles and the reading is skewed high.
8. **Floating pin artefact.** A pin reading near full-scale with no applied voltage is a probe
   artefact, not a firmware fault — the probe must drive RA5 to a defined voltage (it does, 2.5 V)
   before judging the reading.

Only treat "the simulator models the Q10 ADCC wrongly" as a hypothesis after 1–8 are each shown
correct with a positive control, in line with the discipline in `.github/skills/build-test/SKILL.md`
(two earlier Q10 verdicts blamed the simulator for configuration that had never been written).

---

## 4. Where the numbers come from

- Functional pin roles: `firmware/include/pin_map.h` (authoritative).
- Q10 register/bit names and config values: `PIC18F-Q_DFP/1.30.487` in
  `C:\Program Files\Microchip\MPLABX\v6.35\packs\Microchip\` — read `xc8/pic/include/proc/pic18f47q10.h`
  and `xc8/pic/dat/cfgmap/18f47q10.cfgmap` before changing any setup code.
- 16F pin table (historical only): `prototype_reference/docs/hardware/PIC16F18875_pin_map.md`.
- Pin-by-pin fit vs the 16F: `docs/hardware/q10-pinout-compatibility.md`.
- Bring-up measurements and simulator gotchas: `docs/hardware/q10-bringup/README.md`,
  `.github/skills/build-test/SKILL.md`, `bugfixes.md`.
