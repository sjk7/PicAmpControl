# PIC16F723A Hardware Pin Map

This document captures the current hardware understanding for the PIC16F723A and keeps the MCU pin layout tied directly to the amplifier protection design.

## MCU

- Device: PIC16F723A
- Clock: 20 MHz crystal on OSC1/OSC2
- Core purpose: measure RF power, monitor SWR, control amplifier protection state, and report faults on the LCD

## Approved project signal map

This is the current approved signal map for the protection controller. The 1602 LCD backpack and AT24C256 EEPROM share software I2C on RC3/RC4.

| PIC pin | Port | Project name | Direction | Function |
|---|---|---|---|---|
| 11 | RC0 | INPUT_PTT | Input | Transmit request / key-down input |
| 12 | RC1 | OUTPUT_COMP_RESET | Output | Active-low 10 ms comparator-latch reset pulse on PTT entry |
| 13 | RC2 | INPUT_MENU_NEXT | Input | Config-menu page select switch |
| 14 | RC3 | OUTPUT_LCD_I2C_SCL | Output | LCD backpack clock line |
| 15 | RC4 | OUTPUT_LCD_I2C_SDA | Output | LCD backpack data line |
| 16 | RC5 | OUTPUT_TX | Output | First TX sequencing driver |
| 17 | RC6 | OUTPUT_TX_VCC | Output | Second TX sequencing driver |
| 18 | RC7 | OUTPUT_TX_BIAS | Output | Final TX sequencing driver |
| 2 | RA0 | ADC_SWR1_FWD | Input | Pre-filter SWR forward power ADC |
| 3 | RA1 | ADC_SWR1_REF | Input | Pre-filter SWR reflected power ADC |
| 4 | RA2 | ADC_SWR2_FWD | Input | Post-filter SWR forward power ADC |
| 5 | RA3 | ADC_SWR2_REF | Input | Post-filter SWR reflected power ADC |
| 7 | RA5 | ADC_TEMP | Input | Temperature sensor ADC |
| 9,10 | OSC1, OSC2 | XTAL_IN/OUT | Input/Output | 20 MHz crystal |
| 1 | MCLR/VPP | RESET | Input | Master clear reset |
| 19 | RB0 | INPUT_MENU_ADJUST | Input | Menu adjust: short press increase, hold decrease |
| 20 | RB1 | INPUT_SPARE_1 | Input | Freed spare input |
| 21 | RB2 | ADC_OVERDRIVE | Input | Scaled overdrive-sense ADC |
| 22 | RB3 | ADC_DRAIN_PEAK | Input | Scaled drain-peak-sense ADC |
| 23 | RB4 | INPUT_OVERCURRENT_FAULT | Input | Active-high overcurrent comparator fault |
| 24 | RB5 | OUTPUT_FAN_PWM | Output | 12 V fan low-side MOSFET control; confirm hardware-PWM alternate-function routing |
| 25 | RB6 | OUTPUT_WARNING_STATUS | Output | Warning status output |
| 26 | RB7 | OUTPUT_TRIP_STATUS | Output | Trip status output |
| 6 | RA4 | unused | Input | Reserved; not an ADC channel in this design |
| 8,27 | VSS | GND | Power | Ground return |
| 28 | VDD | +5 V | Power | Decouple locally per datasheet |

## Functional grouping

### ADC measurement paths

- pre-filter forward power sense: RA0 / AN0, 0-5 V detector output; configurable full scale from 500 W to 2500 W, default 1500 W
- pre-filter reflected power sense: RA1 / AN1, 0-5 V detector output; shares the pre-filter forward full-scale setting
- post-filter forward power sense: RA2 / AN2, 0-5 V detector output; configurable full scale from 500 W to 2500 W, default 1500 W
- post-filter reflected power sense: RA3 / AN3, 0-5 V detector output; shares the post-filter forward full-scale setting
- temperature sense: RA5 / AN4, 10 kOhm NTC divider output; selectable B3435/B3950/B4250 profile, default B3950. The firmware uses 10 C lookup points from 0 C to 150 C.
- overdrive sense: RB2 / AN7, conditioned peak-envelope detector input scaled so the regulated nominal 5.0 V ADC full scale represents 10.0 W into 50 ohms
- drain-peak sense: RB3 / AN8, conditioned divider scaled so the regulated nominal 5.0 V ADC full scale represents 300 V drain voltage
- each sensor is wired directly to its own ADC pin; no external analog multiplexer is used

### LCD interface

- I2C bus for the 1602 LCD backpack and AT24C256 EEPROM module
- SCL: RC3
- SDA: RC4
- LCD address: `0x27`
- AT24C256 address: `0x50` when A0, A1, and A2 are grounded
- Connect AT24C256 VCC to regulated 5 V, GND to common ground, and WP to ground to permit firmware writes

### Protection outputs

- WARNING_OUT: RC6
- TRIP_OUT: RC7
- AMP_ENABLE: RC5

The TX, fan, warning, and trip outputs each default active-low but are individually configurable active-low or active-high in the configuration menu. They are forced to their configured inactive levels for a fault, startup inhibit, or receive mode.

The selected fan topology is a 12 V two-wire fan with a low-side logic-level N-MOSFET. RB5 drives the MOSFET gate through a resistor with a gate pull-down to ground. Confirm RB5 PWM routing before relying on internal hardware PWM; an external PWM driver is required if it is not a PWM-capable alternate-function pin.

### Operator controls

- PTT_IN: RC0
- COMP_RESET: RC1
- MENU_NEXT: RC2
- MENU_ADJUST: RB0

The menu switches are normally open and active-low, wired from the input pin to ground. RB0 uses a PORTB weak pull-up; RC2 needs an external pull-up resistor. The firmware accepts menu input only while PTT is inactive. RB1 is available as a spare input.

### Comparator board interface

The comparator board should include the hardware protection channel for:

- overcurrent fault (inverse current sense)
- an active-high fault output on RB4

The SWR protection channels are not required in hardware because each SWR pair is measured in firmware from the forward and reflected ADC readings at each RF point.

## Wiring notes

- This map intentionally keeps the 1602 display on the PIC hardware I2C pins and does not use the LCD on a parallel bus.
- The LCD backpack is assumed to be a common PCF8574-style I2C adapter board; I2C is implemented in firmware on RC3/RC4 and shared with the AT24C256 module.
- The LCD and EEPROM modules may both have I2C pull-ups. Avoid overly strong parallel pull-ups; target a combined bus pull-up resistance of approximately 4.7-10 kOhm.
- Overdrive and drain sense nodes are split after their scaling/protection networks: one branch feeds the external comparator and the other feeds the designated ADC input. Neither raw high voltage nor unconditioned RF detector output may reach the PIC.
- The ADC uses VDD as its reference and accepts conversion inputs from 0 to VDD. VDD must be maintained at 5.0 V for the specified scales. The input-power detector/divider must map 31.62 V peak at the 50-ohm input to 5.0 V at RB2. The drain divider must map 300 V to 5.0 V at RB3. Every analogue path needs a series resistor and clamps so the PIC input stays between VSS and VDD under normal operation.
- The comparator board is deliberately separate from the PIC so that the critical analog faults are hardware-protected before the MCU state machine can act.
- SWR is evaluated in firmware from the forward/reflected ADC pairs; no dedicated SWR comparator is required.
- The seven planned analog measurements have dedicated PIC ADC pins, so no external analog multiplexer is required.
- The three former spare inputs are assigned to the LCD configuration menu; no unallocated GPIO remains in this pin map.
- On the falling PTT edge, RC1 outputs a 10 ms active-low pulse to reset the comparator latch network. The controller then checks INPUT_HARD_FAULT before enabling a TX sequence.
- The comparator outputs must combine into one active-high hard-fault signal at RB4. This input remains digital; RB2 and RB3 are dedicated to analogue sensing.
- Any future expansion should be planned before wiring, so the MCU I/O map does not become inconsistent.

## Safety and reset behavior

- When PTT is asserted, the controller must output a 10 ms active-low comparator reset pulse before re-arming software latches.
- A comparator trip must remain active until the analog condition is restored.
- Startup should hold the amplifier disabled for approximately 0.5 to 1.0 seconds after power-up.
- Temperature monitoring uses the selected 10 kOhm NTC B-value profile to display degrees C and drive warning/trip states; the divider and lookup result require final bench calibration.

## Ownership rule

When the amplifier protection design changes, update this file first so the firmware and physical wiring remain aligned.
