# PIC16F723A Hardware Pin Map

This document captures the current hardware understanding for the PIC16F723A and keeps the MCU pin layout tied directly to the amplifier protection design.

## MCU

- Device: PIC16F723A
- Clock: 20 MHz crystal on OSC1/OSC2
- Core purpose: measure RF power, monitor SWR, control amplifier protection state, and report faults on the LCD

## Approved project signal map

This is the current approved signal map for the protection controller. The only I2C peripheral in the design is the 1602 LCD backpack.

| PIC pin | Port/Signal | Project function | Direction | Notes |
|---|---|---|---|---|
| 11 | RC0 | MODE_SWITCH | Input | Mode / operator selection input |
| 12 | RC1 | FAULT_ACK | Input | Fault acknowledge or reset trigger |
| 13 | RC2 | PTT_IN | Input | PTT assertion for transmit start; re-arms protection on entry |
| 14 | RC3 | I2C_SCL | Output | LCD backpack clock line |
| 15 | RC4 | I2C_SDA | Bidirectional | LCD backpack data line |
| 16 | RC5 | AMP_ENABLE | Output | Enable / disable drive to amplifier chain |
| 17 | RC6 | WARNING_OUT | Output | Warning-level alarm output |
| 18 | RC7 | TRIP_OUT | Output | Trip-level alarm output |
| 2 | RA0 | FWD_ADC_INPUT | Input | Forward power ADC |
| 3 | RA1 | REF_ADC_INPUT | Input | Reflected power ADC |
| 5 | RA3 | TEMP_ADC_INPUT | Input | Temperature sensor input |
| 9,10 | OSC1, OSC2 | XTAL_IN/OUT | Input/Output | 20 MHz crystal |
| 1 | MCLR/VPP | RESET | Input | Master clear reset |
| 19-26 | RB0-RB7 | Comparator fault + fan + status | IO | RB0..RB7 reserved for comparator trip status, fan PWM, or future fault inputs |
| 4,6,7,8,27,28 | VSS/VDD/NC | Power / support | Power | Follow datasheet decoupling rules |

## Functional grouping

### ADC measurement paths

- forward power sense: RA0 / AN0
- reflected power sense: RA1 / AN1
- temperature sense: RA3 / AN3
- optional spare diagnostic input can be moved to another ADC-capable pin if needed

### LCD interface

- I2C bus only for the 1602 LCD backpack
- SCL: RC3
- SDA: RC4
- No other I2C devices are planned in the design

### Protection outputs

- WARNING_OUT: RC6
- TRIP_OUT: RC7
- AMP_ENABLE: RC5

### Operator controls

- MODE_SWITCH: RC0
- FAULT_ACK: RC1
- PTT_IN: RC2

### Comparator board interface

The comparator board should include the hardware protection channels for:

- SWR protection 1: pre-filter or PA output
- SWR protection 2: post-filter or antenna output
- overdrive detection
- drain peak voltage trip
- overcurrent fault (inverse current sense)
- optional spare comparator input for future fault expansion

These comparator outputs are expected to be read by the PIC on selected RB pins or dedicated digital inputs.

## Wiring notes

- This map intentionally keeps the 1602 display on the PIC hardware I2C pins and does not use the LCD on a parallel bus.
- The LCD backpack is assumed to be a common PCF8574-style I2C adapter board.
- No other I2C devices are included in this design to keep the hardware simple and predictable.
- The comparator board is deliberately separate from the PIC so that the critical RF and power faults are hardware-protected before the MCU state machine can act.
- PTT is treated as a re-arm event for software fault latches, but it must never override a live hardware comparator fault.
- Any future expansion should be planned before wiring, so the MCU I/O map does not become inconsistent.

## Safety and reset behavior

- When PTT is asserted, the controller should re-arm or clear its software latching state after a short settle time.
- A comparator trip must remain active until the analog condition is restored.
- Startup should hold the amplifier disabled for approximately 0.5 to 1.0 seconds after power-up.
- Temperature monitoring should drive warning and trip states, with fan speed increasing as temperature rises.

## Ownership rule

When the amplifier protection design changes, update this file first so the firmware and physical wiring remain aligned.
