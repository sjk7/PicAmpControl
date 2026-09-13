# Pull-Up Resistor Guidance

This note records which PIC pins need external bias resistors and which interfaces provide their own biasing. Resistor values are starting points and must be confirmed against the final schematic, connected equipment, and PIC16F18855 electrical specifications.

| Signal | Pull-up requirement |
|---|---|
| `RB0 / INPUT_MENU_ADJUST` | No external pull-up required. Firmware enables the PIC PORTB weak pull-up. The normally-open switch connects the pin to ground. |
| `RC2 / INPUT_MENU_NEXT` | **External pull-up required.** Use approximately `10 kOhm` to `+5 V`; the normally-open switch connects RC2 to ground. |
| `RC0 / INPUT_PTT` | **Requires a defined idle level.** The firmware does not enable a PORTC pull-up. Add an external pull-up, typically `10 kOhm` to `+5 V`, when the PTT source is an open switch, open-collector, or open-drain signal. A push-pull transceiver output may instead provide the required high and low levels directly. |
| `RC3/RC4 / LCD I2C` | **External I2C pull-ups required.** The PCF8574 LCD backpack often includes them. Verify the backpack and target a combined bus resistance of approximately `4.7-10 kOhm`; avoid overly strong parallel pull-ups. |
| `RB4 / INPUT_OVERCURRENT_FAULT` | No pull-up is needed if the comparator output is push-pull. If the output is open-drain or open-collector, provide a pull-up on the comparator board. |
| `MCLR/VPP` pin 1 | Use the normal external MCLR reset pull-up recommended for the PIC hardware design, typically around `10 kOhm` to `+5 V`. Add reset-capacitor circuitry only when required by the reset timing and programming/debug arrangement. |
| ADC inputs | No generic pull-ups. Use the specified detector, divider, thermistor, series-resistor, and clamp networks for each analogue input. |
| Fan output | This needs a gate pull-down rather than a pull-up. The RB5 MOSFET gate should have a gate resistor and a pull-down to ground. |

## PCB checklist

- Fit the RC2 menu-switch pull-up.
- Fit the RC0 PTT pull-up unless the connected transceiver guarantees a push-pull logic signal.
- Verify whether the LCD backpack already carries I2C pull-ups and measure the resulting combined resistance.
- Confirm the comparator output type before fitting or omitting the RB4 pull-up.
- Fit the MCLR pull-up and keep the programming/debug connection compatible with the reset circuit.
- Do not add generic pull-ups to the ADC inputs or replace the fan-gate pull-down with a pull-up.
