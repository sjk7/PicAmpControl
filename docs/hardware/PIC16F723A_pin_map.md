# PIC16F723A Hardware Pin Map

This document captures the current hardware understanding for the PIC16F723A and keeps the MCU pin layout tied directly to the amplifier protection design.

## MCU

- Device: PIC16F723A
- Clock: 20 MHz crystal on OSC1/OSC2
- Core purpose: measure RF power, monitor SWR, control amplifier protection state, and report faults on the LCD

## Approved project signal map

This is the current approved signal map for the protection controller. The only I2C peripheral in the design is the 1602 LCD backpack.

| PIC pin | Port | Project name | Direction | Function |
|---|---|---|---|---|
| 11 | RC0 | INPUT_PTT | Input | Transmit request / key-down input |
| 12 | RC1 | INPUT_FAULT_ACK | Input | Fault clear / reset trigger |
| 13 | RC2 | spare | Input | Reserved if a separate hardware signal is needed later |
| 14 | RC3 | OUTPUT_LCD_I2C_SCL | Output | LCD backpack clock line |
| 15 | RC4 | OUTPUT_LCD_I2C_SDA | Output | LCD backpack data line |
| 16 | RC5 | OUTPUT_TX | Output | First TX sequencing driver |
| 17 | RC6 | OUTPUT_TX_VCC | Output | Second TX sequencing driver |
| 18 | RC7 | OUTPUT_TX_BIAS | Output | Final TX sequencing driver |
| 2 | RA0 | ADC_SWR1_FWD | Input | Pre-filter SWR forward power ADC |
| 3 | RA1 | ADC_SWR1_REF | Input | Pre-filter SWR reflected power ADC |
| 4 | RA2 | ADC_SWR2_FWD | Input | Post-filter SWR forward power ADC |
| 5 | RA3 | ADC_SWR2_REF | Input | Post-filter SWR reflected power ADC |
| 6 | RA4 | ADC_TEMP | Input | Temperature sensor input |
| 9,10 | OSC1, OSC2 | XTAL_IN/OUT | Input/Output | 20 MHz crystal |
| 1 | MCLR/VPP | RESET | Input | Master clear reset |
| 19 | RB0 | INPUT_SPARE_1 | Input | Free spare input; no SWR comparator required |
| 20 | RB1 | INPUT_SPARE_2 | Input | Free spare input; no SWR comparator required |
| 21 | RB2 | INPUT_COMP_OVERDRIVE | Input | Overdrive comparator |
| 22 | RB3 | INPUT_COMP_DRAIN_PEAK | Input | Drain peak comparator |
| 23 | RB4 | INPUT_COMP_OVERCURRENT | Input | Overcurrent comparator |
| 24 | RB5 | OUTPUT_FAN_PWM | Output | Fan speed control |
| 25 | RB6 | OUTPUT_WARNING_STATUS | Output | Warning status output |
| 26 | RB7 | OUTPUT_TRIP_STATUS | Output | Trip status output |
| 4,6,7,8,27,28 | VSS/VDD/NC | Power / support | Power | Follow datasheet decoupling rules |

## Functional grouping

### ADC measurement paths

- pre-filter forward power sense: RA0 / AN0
- pre-filter reflected power sense: RA1 / AN1
- post-filter forward power sense: RA2 / AN2
- post-filter reflected power sense: RA3 / AN3
- temperature sense: RA4 / AN4
- each sensor is wired directly to its own ADC pin; no external analog multiplexer is used

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

- overdrive detection
- drain peak voltage trip
- overcurrent fault (inverse current sense)
- optional spare comparator input for future fault expansion

The SWR protection channels are not required in hardware because each SWR pair is measured in firmware from the forward and reflected ADC readings at each RF point.

## Wiring notes

- This map intentionally keeps the 1602 display on the PIC hardware I2C pins and does not use the LCD on a parallel bus.
- The LCD backpack is assumed to be a common PCF8574-style I2C adapter board.
- No other I2C devices are included in this design to keep the hardware simple and predictable.
- The comparator board is deliberately separate from the PIC so that the critical analog faults are hardware-protected before the MCU state machine can act.
- SWR is evaluated in firmware from the forward/reflected ADC pairs; no dedicated SWR comparator is required.
- The five planned analog measurements have dedicated PIC ADC pins, so no external analog multiplexer is required.
- PTT is treated as a re-arm event for software fault latches, but it must never override a live hardware comparator fault.
- Any future expansion should be planned before wiring, so the MCU I/O map does not become inconsistent.

## Safety and reset behavior

- When PTT is asserted, the controller should re-arm or clear its software latching state after a short settle time.
- A comparator trip must remain active until the analog condition is restored.
- Startup should hold the amplifier disabled for approximately 0.5 to 1.0 seconds after power-up.
- Temperature monitoring should drive warning and trip states, with fan speed increasing as temperature rises.

## Ownership rule

When the amplifier protection design changes, update this file first so the firmware and physical wiring remain aligned.
