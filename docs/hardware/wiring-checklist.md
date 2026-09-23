# Wiring Checklist – Linear Amplifier Protection Board

Wiring, pull-up/pull-down, decoupling, and driver-stage guidance for the PIC18F47Q10-I/P
protection board.

> **Pin assignments are deliberately NOT restated here.**
> The single source of truth for which signal is on which pin is
> [PIC18F47Q10_pin_map_and_setup.md](PIC18F47Q10_pin_map_and_setup.md). This file covers only what to *do* at
> each signal. If a signal appears here that is not in the pin map, the pin map wins.

Supply: regulated **5.0 V**. VDD is the ADC reference, so it must stay at 5.0 V — every
analogue scale in the firmware assumes it.

## Pull-ups and pull-downs

| Signal | Requirement |
|---|---|
| `INPUT_PTT` | 10 kOhm pull-up to VDD (active-low switch to GND) |
| `INPUT_ENCODER_A`, `INPUT_ENCODER_B` | 10 kOhm pull-up to VDD each (firmware also enables the PORTB weak pull-ups; add external ones for panel wiring) |
| `INPUT_ENCODER_SWITCH` | 10 kOhm pull-up to VDD |
| `INPUT_FREQ_COUNTER` | **No pull-up.** It is the Timer1 T1CKI clock input; it needs valid conditioning/drive, not a resistor |
| `OUTPUT_BAND_160M` … `OUTPUT_BAND_10M` | No pull-up/pull-down. Push-pull CMOS outputs into the relay driver |
| `OUTPUT_TX`, `OUTPUT_TX_VCC`, `OUTPUT_TX_BIAS` driver gates | 10 kOhm gate pull-down to GND so the outputs stay inactive while the MCU is unpowered or in reset |
| `OUTPUT_COMP_RESET` | No pull-up. Push-pull output; idles high and is asserted low for the reset window |
| `INPUT_OVERCURRENT_FAULT` | No pull-up if the comparator output is push-pull; add one if it is open-drain/open-collector. Confirm the polarity in the pin map |
| `OUTPUT_FAN_PWM` | Gate **pull-down** 10 kOhm to GND at the driver (pull-down, not pull-up) |
| `OUTPUT_TRIP_STATUS` | No pull-up; LED plus series resistor |
| ADC inputs (SWR1/SWR2 forward+reflected, temperature, current, overdrive, drain peak) | No pull-up/pull-down; driven from the conditioning network |
| LCD lines (RS, E, D4–D7) | No pull-up; push-pull CMOS outputs |
| `MCLR` | 10 kOhm pull-up to VDD; optional 100 nF to GND for EMI |

## Decoupling

- 100 nF ceramic from each VDD pin to VSS, placed at the pin
- Keep VDD clean and regulated: it is the ADC reference. If the design is later changed to
  an external VREF+, add 1 µF + 100 nF there
- 100 nF from each ADC pin to GND, placed at the PIC pad; keep analogue traces short

## Analogue input protection

Every ADC input must remain between VSS and VDD under all conditions — see
[adc-input-protection-guidance.md](adc-input-protection-guidance.md) for the series
resistance, clamping, and filtering per signal.

## LCD (16x2, 4-bit parallel)

Six PIC lines (RS, E, D4–D7) to a standard HD44780 module. **No I2C/PCF8574 backpack** —
that wiring is obsolete. The module additionally needs VSS/VDD and a contrast divider.
Confirm the exact header pinout at schematic capture.

## Rotary encoder

A and B phases into the two encoder inputs, encoder common to GND, push switch to the
switch input. Firmware enables the PORTB weak pull-ups; add external 10 kOhm pull-ups for
panel-mounted encoders.

## TX sequencing outputs

Each output drives a relay coil or a MOSFET gate. Relay coils need a flyback diode
(1N4007, cathode to +12V). MOSFET gates need a series gate resistor and a 10 kOhm gate
pull-down.

## LPF band selection

One dedicated active-high output per band (six bands: 160/80/40/20/15/10 m), each driving
one ULN2803A channel, which sinks the matching relay coil. Fit a flyback diode across each
coil. There is **no 74HC4514 decoder and no B0–B2 address bus**.

## Fan

Low-side N-MOSFET driven from the fan PWM output: series gate resistor, 10 kOhm gate
pull-down, and a flyback diode across the motor. Confirm at bench validation whether the
PWM output can use its hardware PWM alternate function; otherwise use an external driver.

## Trip indicator

LED with a series resistor from the trip status output.

## Unused pins

Port E (RE0/RE2/RE3) is unused. Tie unused inputs to a defined level rather than leaving
them floating. See the free-pin list in the pin map for the current state.
