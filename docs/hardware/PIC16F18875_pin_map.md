# PIC16F18875-I/P Hardware Pin Map

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
| RA4 | 6 | GPIO | (free) | Reserved for future use (was OUTPUT_FILTER_BAND_0) |
| RA5 | 7 | Analog In | ADC_TEMP | Temperature monitoring (thermistor preamp output) |
| RA6 | 8 | GPIO | (free) | Reserved for future use (was OUTPUT_FILTER_BAND_1) |
| RA7 | 9 | GPIO | (free) | Reserved for future use (was OUTPUT_FILTER_BAND_2 / Timer1 external clock) |

## Port B (Universal I/O)

| Pin | Number | Mode | Signal | Purpose |
|-----|--------|------|--------|---------|
| RB0 | 21 | GPIO In | INPUT_ENCODER_B | Rotary encoder (quadrature phase B) |
| RB1 | 22 | Analog In | ADC_CURRENT | Drain/collector current measurement (current sense amp) |
| RB2 | 23 | GPIO | (free) | Available |
| RB3 | 24 | GPIO | (free) | Available |
| RB4 | 25 | GPIO In | INPUT_OVERCURRENT_FAULT | Comparator latch output (hardware overcurrent trip) |
| RB5 | 26 | PWM Out | OUTPUT_FAN_PWM | Fan motor PWM (active-high, 5V @ ~8A peak) |
| RB6 | 27 | GPIO In | INPUT_ENCODER_SWITCH | Rotary encoder switch (push-to-select) |
| RB7 | 28 | GPIO Out | OUTPUT_TRIP_STATUS | Trip event indicator (active-low to ground, ~20mA sink) |

## Port C (Digital I/O + Peripheral Interfaces)

| Pin | Number | Mode | Signal | Purpose |
|-----|--------|------|--------|---------|
| RC0 | 11 | GPIO In | INPUT_PTT | Push-to-talk / transmit enable (active-low) |
| RC1 | 12 | GPIO Out | OUTPUT_COMP_RESET | Comparator (CMP1) latch reset (active-high pulse) |
| RC2 | 13 | GPIO In | INPUT_ENCODER_A | Rotary encoder (quadrature phase A) |
| RC3 | 14 | GPIO I/O | OUTPUT_LCD_I2C_SCL | LCD backpack I2C clock (open-drain, 10k pull-up external) |
| RC4 | 15 | GPIO I/O | OUTPUT_LCD_I2C_SDA | LCD backpack I2C data (open-drain, 10k pull-up external) |
| RC5 | 16 | GPIO Out | OUTPUT_TX | TX enable / amplifier control (active-low, ~50mA sink) |
| RC6 | 17 | GPIO Out | OUTPUT_TX_VCC | TX VCC / amplifier supply switch (active-low, ~100mA sink) |
| RC7 | 18 | GPIO Out | OUTPUT_TX_BIAS | TX bias / amplifier idle condition (active-low, ~50mA sink) |

## Port D (New on PIC16F18875)

| Pin | Number | Mode | Signal | Purpose |
|-----|--------|------|--------|---------|
| RD0 | 29 | GPIO | (free) | Available |
| RD1 | 30 | GPIO | (free) | Available |
| RD2 | 31 | GPIO | (free) | Available |
| RD3 | 32 | GPIO | (free) | Available |
| RD4 | 33 | GPIO | (free) | Available |
| RD5 | 34 | GPIO | (free) | Available |
| RD6 | 35 | GPIO | (free) | Available |
| RD7 | 36 | GPIO | (free) | Available |

## Port E (New on PIC16F18875)

| Pin | Number | Mode | Signal | Purpose |
|-----|--------|------|--------|---------|
| RE0 | 37 | GPIO | (free) | Available |
| RE2 | 39 | GPIO | (free) | Available |
| RE3 | 40 | GPIO | (free) | Available |
| (VREF+) | 38 | Power | ADC Ref | Voltage reference for ADC (see Power & Ground section) |

## Power & Ground

| Signal | Pin Numbers | Qty |
|--------|-------------|-----|
| VDD (3.3V) | 10, 20 | 2 |
| VSS (GND) | 1, 19 | 2 |
| VREF+ (ADC ref) | 38 | 1 |

(Pin numbers assume standard PDIP-40 package conventions)

## ADC Channel Assignments

| Channel | Pin | Signal | Measurement |
|---------|-----|--------|-------------|
| 0 | RA0 | ADC_SWR1_FWD | SWR1 forward power (sensor preamp 0–5V) |
| 1 | RA1 | ADC_SWR1_REF | SWR1 reflected power (sensor preamp 0–5V) |
| 2 | RA2 | ADC_SWR2_FWD | SWR2 forward power (sensor preamp 0–5V) |
| 3 | RA3 | ADC_SWR2_REF | SWR2 reflected power (sensor preamp 0–5V) |
| 5 | RA5 | ADC_TEMP | Temperature (thermistor preamp 0–5V → °C via LUT) |
| 9 | RB1 | ADC_CURRENT | Drain/collector current (current sense amp 0–5V) |
| 10 | (N/A) | ADC_OVERDRIVE | Overdrive detection (comparator / firmware trip logic) |
| 11 | (N/A) | ADC_DRAIN_PEAK | Peak drain stress (comparator / firmware trip logic) |

(Channels 10–11 are comparator trip signals, not ADC inputs, but referenced in trip detection firmware.)

## Protection / Comparator Inputs

| Signal | Purpose |
|--------|---------|
| INPUT_OVERCURRENT_FAULT (RB4) | Hardware overcurrent latch (CMP1 output, active-low trip) |
| OUTPUT_COMP_RESET (RC1) | Active-high pulse to reset CMP1 latch after trip recovery |

## Encoder UI

| Signal | Pin | Purpose |
|--------|-----|---------|
| INPUT_ENCODER_A | RC2 | Quadrature phase A (menu navigation CW) |
| INPUT_ENCODER_B | RB0 | Quadrature phase B (menu navigation CCW) |
| INPUT_ENCODER_SWITCH | RB6 | Encoder center button (menu select / confirm) |

## Reserved Pins for Future Expansion

The following pins are now available for additional features:

- **Port A:** RA4, RA6, RA7 (3 pins freed from band selection removal)
- **Port B:** RB2, RB3 (2 additional pins)
- **Port D:** RD1–RD7 (7 pins, RD0 used for LCD D7)
- **Port E:** RE0, RE2, RE3 (3 pins; pin 38 is VREF+ ADC reference)

**Total new GPIO available:** 15 pins (plus potential VREF+ if externalized ADC reference is needed)

### Possible Future Uses
- **Filter/Band Selection (3–4 pin encoding):** Use RA4/RA6/RA7 for binary or independent relay control
- Additional sensor inputs (ADC or digital)
- Extended relay/switch control logic
- Serial communication (UART, CAN)
- MCLR decoupling if internal reset is insufficient

## KiCad Symbol Reference

The design uses KiCad's `MCU_Microchip_PIC16:PIC16F18875-xPDIP40` symbol, which preserves pin compatibility while extending port availability.

---

**Document Version:** 2.0  
**Last Updated:** 2026-09-20  
**Device Migration:** PIC16F18855-I/SP (28-pin, 8KB) → PIC16F18875-I/P (40-pin, 16KB)
