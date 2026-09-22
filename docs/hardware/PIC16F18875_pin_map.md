# PIC16F18875-I/P Hardware Pin Map

> **Single source of truth for MCU pin assignments.**
>
> This file is the one authoritative pin assignment table for the project. Every other
> document — README, architecture, schematic package, checklists, guidance notes — must
> **link here instead of restating pin assignments**. Duplicating this table is what caused
> the band-select, LCD, and comparator-reset drift found on 2026-09-21.
>
> Rule: `firmware/include/pin_map.h` and this document must agree. If they disagree, the
> code wins and this document gets corrected in the same change.
>
> Physical pin numbers are for the PDIP-40 package. Firmware addresses ports/bits by name
> (e.g. `PORTCbits.RC0`) and is unaffected by physical numbering; only the
> schematic/netlist/PCB need the numbers.

This document captures the current hardware understanding for the PIC16F18875-I/P and keeps the MCU pin layout tied directly to the amplifier protection design.

## Device Overview

- Device: PIC16F18875-I/P (upgraded from PIC16F18855)
- Package: PDIP-40 (vs PDIP-28 for PIC16F18855)
- Program Memory: 16 KB (doubled from 8 KB)
- RAM: 1024 B (doubled from 512 B)
- GPIO Pins: ~32 (vs ~24 on PIC16F18855)
- Oscillator: 32 MHz HFINTOSC internal (maximum); 20 MHz external if crystal used
- Compiler: XC8 4.00+

**Pin Compatibility:** The PIC16F18875 extends the PIC16F18855 with additional Port D and Port E pins. All Port A/B/C pin numbers remain identical, ensuring firmware compatibility. Existing peripheral assignments (ADC channels, Timer, UART, I2C, PWM) are preserved.

## Port A (Analog/Digital Flexible I/O)

| Pin | Number | Mode | Signal | Purpose |
|-----|--------|------|--------|---------|
| RA0 | 2 | Analog In | ADC_SWR1_FWD | SWR1 forward detection (sensor preamp output) |
| RA1 | 3 | Analog In | ADC_SWR1_REF | SWR1 reflected detection (sensor preamp output) |
| RA2 | 4 | Analog In | ADC_SWR2_FWD | SWR2 forward detection (sensor preamp output) |
| RA3 | 5 | Analog In | ADC_SWR2_REF | SWR2 reflected detection (sensor preamp output) |
| RA4 | 6 | GPIO Out | OUTPUT_LCD_RS | Parallel LCD register-select |
| RA5 | 7 | Analog In | ADC_TEMP | Temperature monitoring (thermistor preamp output) |
| RA6 | 14 | GPIO Out | OUTPUT_LCD_E | Parallel LCD enable/strobe |
| RA7 | 13 | GPIO Out | OUTPUT_LCD_D4 | Parallel LCD data bit 4 |

## Port B (Universal I/O)

| Pin | Number | Mode | Signal | Purpose |
|-----|--------|------|--------|---------|
| RB0 | 33 | GPIO In | INPUT_ENCODER_B | Rotary encoder (quadrature phase B) |
| RB1 | 34 | Analog In | ADC_CURRENT | Drain/collector current measurement (current sense amp) |
| RB2 | 35 | Analog In | ADC_OVERDRIVE | Overdrive detection input |
| RB3 | 36 | Analog In | ADC_DRAIN_PEAK | Peak drain stress input |
| RB4 | 37 | GPIO In | INPUT_OVERCURRENT_FAULT | Comparator latch output (hardware overcurrent trip) |
| RB5 | 38 | PWM Out | OUTPUT_FAN_PWM | Fan motor PWM (active-high, 5V @ ~8A peak) |
| RB6 | 39 | GPIO In | INPUT_ENCODER_SWITCH | Rotary encoder switch (push-to-select), ICSPCLK |
| RB7 | 40 | GPIO Out | OUTPUT_TRIP_STATUS | Trip event indicator (active-low to ground, ~20mA sink), ICSPDAT |

## Port C (Digital I/O + Peripheral Interfaces)

| Pin | Number | Mode | Signal | Purpose |
|-----|--------|------|--------|---------|
| RC0 | 15 | GPIO In | INPUT_PTT | Push-to-talk / transmit enable (active-low) |
| RC1 | 16 | GPIO Out | OUTPUT_COMP_RESET | Comparator (CMP1) latch reset (active-high pulse) |
| RC2 | 17 | GPIO In | INPUT_ENCODER_A | Rotary encoder (quadrature phase A) |
| RC3 | 18 | GPIO Out | OUTPUT_LCD_D5 | Parallel LCD data bit 5 |
| RC4 | 23 | GPIO Out | OUTPUT_LCD_D6 | Parallel LCD data bit 6 |
| RC5 | 24 | GPIO Out | OUTPUT_TX | TX enable / amplifier control (active-low, ~50mA sink) |
| RC6 | 25 | GPIO Out | OUTPUT_TX_VCC | TX VCC / amplifier supply switch (active-low, ~100mA sink) |
| RC7 | 26 | GPIO Out | OUTPUT_TX_BIAS | TX bias / amplifier idle condition (active-low, ~50mA sink) |

## Port D (New on PIC16F18875)

| Pin | Number | Mode | Signal | Purpose |
|-----|--------|------|--------|---------|
| RD0 | 19 | GPIO Out | OUTPUT_LCD_D7 | Parallel LCD data bit 7 |
| RD1 | 20 | GPIO In | INPUT_FREQ_COUNTER | Timer1 external clock (T1CKI via PPS), frequency counter input |
| RD2 | 21 | GPIO | OUTPUT_BAND_160M | Active-high LPF band-select output for 160 m |
| RD3 | 22 | GPIO | OUTPUT_BAND_80M | Active-high LPF band-select output for 80 m |
| RD4 | 27 | GPIO | OUTPUT_BAND_40M | Active-high LPF band-select output for 40 m |
| RD5 | 28 | GPIO | OUTPUT_BAND_20M | Active-high LPF band-select output for 20 m |
| RD6 | 29 | GPIO | OUTPUT_BAND_15M | Active-high LPF band-select output for 15 m |
| RD7 | 30 | GPIO | OUTPUT_BAND_10M | Active-high LPF band-select output for 10 m |

> Pull-up notes for Port D:
> - `RD1 / INPUT_FREQ_COUNTER` is a Timer1 clock input, not a switch input. It should not get a generic pull-up; it needs a valid external clock signal or proper conditioning. If the source is open-circuit or weakly driven, the fix belongs in the signal source/conditioning network, not a random pull-up.
> - `RD2`-`RD7` are output pins driving the LPF relay/band-select bus and are not meant to be pulled up or read as switches. They are push-pull CMOS outputs; no pull-up/pull-down resistors are required.

## Port E (New on PIC16F18875)

| Pin | Number | Mode | Signal | Purpose |
|-----|--------|------|--------|---------|
| RE0 | 8 | GPIO | (free) | Available |
| RE1 | 9 | GPIO | (free) | Available |
| RE2 | 10 | GPIO | (free) | Available |
| RE3 | 1 | Reset | VPP/MCLR/RE3 | Master clear / programming voltage; not free GPIO while `MCLRE = ON` |

## Power & Ground

| Signal | Pin Numbers | Qty |
|--------|-------------|-----|
| VDD | 11, 32 | 2 |
| VSS (GND) | 12, 31 | 2 |

Pin numbers are the PDIP-40 numbers from the PIC16(L)F18855/75 datasheet (DS40001802H), taken
from the 40-pin PDIP pin diagram and cross-checked against Table 3 (40/44-pin allocation table).
There is **no dedicated VREF+ pin**: VREF+ is an alternate function of RA3, and the ADC is
VDD-referenced (`firmware/src/main.c`, FVR off), so the design does not consume it.

## ADC Channel Assignments

| Channel | Pin | Signal | Measurement |
|---------|-----|--------|-------------|
| 0 | RA0 | ADC_SWR1_FWD | SWR1 forward power (sensor preamp 0–5V) |
| 1 | RA1 | ADC_SWR1_REF | SWR1 reflected power (sensor preamp 0–5V) |
| 2 | RA2 | ADC_SWR2_FWD | SWR2 forward power (sensor preamp 0–5V) |
| 3 | RA3 | ADC_SWR2_REF | SWR2 reflected power (sensor preamp 0–5V) |
| 5 | RA5 | ADC_TEMP | Temperature (thermistor preamp 0–5V → °C via LUT) |
| 9 | RB1 | ADC_CURRENT | Drain/collector current (current sense amp 0–5V) |
| 10 | RB2 | ADC_OVERDRIVE | Overdrive detection (sensor preamp 0–5V) |
| 11 | RB3 | ADC_DRAIN_PEAK | Peak drain stress (sensor preamp 0–5V) |

## Protection / Comparator Inputs

| Signal | Purpose |
|--------|---------|
| INPUT_OVERCURRENT_FAULT (RB4) | Hardware overcurrent latch (CMP1 output, active-low trip) |
| OUTPUT_COMP_RESET (RC1) | Active-low pulse to reset CMP1 latch: idles high, driven low for the reset/settle window (10 ms on PTT entry, 1000 ms at startup) |

## Encoder UI

| Signal | Pin | Purpose |
|--------|-----|---------|
| INPUT_ENCODER_A | RC2 | Quadrature phase A (menu navigation CW) |
| INPUT_ENCODER_B | RB0 | Quadrature phase B (menu navigation CCW) |
| INPUT_ENCODER_SWITCH | RB6 | Encoder center button (menu select / confirm) |

## Reserved Pins for Future Expansion

The following pins are genuinely free (not claimed by any `pin_map.h` define):

- **Port D:** none — RD0-RD7 are all claimed (RD0 = LCD_D7, RD1 = frequency counter, RD2-RD7 = the six LPF band-select outputs).
- **Port E:** RE0, RE1, RE2 (3 pins). RE2 is also the only Port E pin with a second function worth noting.
- **RE3 is not free GPIO.** `firmware/src/main.c` sets `#pragma config MCLRE = ON`, so RE3 is the MCLR/VPP pin and is input-only general purpose at best (the datasheet lists it as "general purpose input only when MCLR is disabled").
- `VREF+` is **not a dedicated pin** on this device: it is an alternate function of **RA3** (datasheet: `RA3/ANA3/C1IN1+/VREF+/MDCARL`). The ADC uses VDD as its reference (`firmware/src/main.c`, FVR off), so no VREF+ pin is consumed by the design.

**Total free GPIO available:** 3 pins (RE0, RE1, RE2). RE3 is claimed by MCLR and RA3 can supply an
external VREF+ if a ratiometric reference is ever needed, but neither is currently free.

### Possible Future Uses
- **Filter/Band Selection:** One output pin per RF band (6 bands: 160/80/40/20/15/10m) fits within RD2–RD7 with no bit-encoding needed; RE0/RE1/RE2 remain spare
- Additional sensor inputs (ADC or digital)
- Extended relay/switch control logic
- Serial communication (UART, CAN)
- MCLR decoupling if internal reset is insufficient

---

**Document Version:** 2.3  
**Last Updated:** 2026-09-22  
**Device Migration:** PIC16F18855-I/SP (28-pin, 8KB) → PIC16F18875-I/P (40-pin, 16KB)
