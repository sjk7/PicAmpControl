# Pull-Up Resistor Guidance

This note records which signals need external bias resistors and which interfaces provide their own biasing. Resistor values are starting points and must be confirmed against the final schematic, connected equipment, and PIC18F47Q10 electrical specifications.

> Pin assignments are not restated here. Single source of truth: [PIC18F47Q10_pin_map_and_setup.md](PIC18F47Q10_pin_map_and_setup.md).

| Signal | Pull-up requirement |
|---|---|
| `INPUT_ENCODER_A` | Firmware enables the PIC PORTC weak pull-up. For a front-panel encoder or wiring longer than a short PCB run, also fit an external pull-up around `10 kOhm` to `+5 V`; the encoder contact connects the pin to ground. |
| `INPUT_ENCODER_B` | Firmware enables the PIC PORTB weak pull-up. For a front-panel encoder or wiring longer than a short PCB run, also fit an external pull-up around `10 kOhm` to `+5 V`; the encoder contact connects the pin to ground. |
| `INPUT_ENCODER_SWITCH` | Firmware enables the PIC PORTB weak pull-up. For a front-panel encoder or wiring longer than a short PCB run, also fit an external pull-up around `10 kOhm` to `+5 V`; the push switch connects the pin to ground. |
| `INPUT_PTT` | **Requires a defined idle level.** The firmware does not enable a PORTC pull-up. Add an external pull-up, typically `10 kOhm` to `+5 V`, when the PTT source is an open switch, open-collector, or open-drain signal. A push-pull transceiver output may instead provide the required high and low levels directly. |
| `INPUT_FREQ_COUNTER` | **No pull-up.** It is the Timer1 T1CKI clock input, not a switch input; it needs valid conditioning/drive, not a bias resistor. |
| `INPUT_OVERCURRENT_FAULT` | No pull-up is needed if the comparator output is push-pull. If the output is open-drain or open-collector, provide a pull-up on the comparator board. |
| `MCLR/VPP` | Use the normal external MCLR reset pull-up recommended for the PIC hardware design, typically around `10 kOhm` to `+5 V`. Add reset-capacitor circuitry only when required by the reset timing and programming/debug arrangement. |
| LCD lines (RS / E / D4-D7) | No pull-ups; push-pull CMOS outputs. The LCD is 4-bit parallel, so no I2C bus pull-ups are needed. |
| ADC inputs | No generic pull-ups. Use the specified detector, divider, thermistor, series-resistor, and clamp networks for each analogue input. |
| Fan output | This needs a gate pull-down rather than a pull-up. The fan PWM MOSFET gate should have a gate resistor and a pull-down to ground. |

## PCB checklist

- Fit the encoder pull-ups if the encoder is panel-wired rather than directly on the controller PCB.
- Fit the PTT pull-up unless the connected transceiver guarantees a push-pull logic signal.
- Do not fit I2C pull-ups for the LCD: the display is 4-bit parallel, not an I2C backpack.
- Confirm the comparator output type before fitting or omitting the overcurrent-fault pull-up.
- Fit the MCLR pull-up and keep the programming/debug connection compatible with the reset circuit.
- Do not add generic pull-ups to the ADC inputs, the band-select outputs, or the Timer1 clock input, and do not replace the fan-gate pull-down with a pull-up.
