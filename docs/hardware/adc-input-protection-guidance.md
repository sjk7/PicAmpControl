# ADC Input Protection Guidance

This note defines the planned protection approach for the PIC16F18855 analogue inputs. Component values are starting points and must be confirmed against the final sensor circuits, source impedance, transient environment, and PIC16F18855 electrical specifications.

## Inputs requiring protection

Apply the nominal `1 kOhm` series resistor and two single-Schottky rail-clamp arrangement to physical PIC pins **2, 3, 4, 5, 7, 22, 23, and 24**. These are the eight ADC inputs listed below:

| PIC pin | Port/channel | Signal |
|---:|---|---|
| 2 | `RA0 / AN0` | `ADC_SWR1_FWD` |
| 3 | `RA1 / AN1` | `ADC_SWR1_REF` |
| 4 | `RA2 / AN2` | `ADC_SWR2_FWD` |
| 5 | `RA3 / AN3` | `ADC_SWR2_REF` |
| 7 | `RA5 / AN5` | `ADC_TEMP` |
| 22 | `RB1 / AN9` | `ADC_CURRENT` |
| 23 | `RB2 / AN10` | `ADC_OVERDRIVE` |
| 24 | `RB3 / AN11` | `ADC_DRAIN_PEAK` |

The complete sensor, divider, series-resistor, and clamp network must keep the PIC input between `VSS` and `VDD` during normal operation and credible transients. The ADC reference is the regulated `+5 V` VDD rail.

A typical arrangement is:

```text
sensor or divider output -- 1 kOhm series -- PIC ADC pin
                                           |
                              +------------+------------+
                              |                         |
                         DLOW to VSS               DHIGH to VDD
```

Two individual single Schottky diodes may be used for each ADC input. Orient `DLOW` with its anode at `VSS/GND` and cathode at the ADC pin to clamp negative excursions. Orient `DHIGH` with its anode at the ADC pin and cathode at `VDD/+5 V` to divert positive overvoltage into the 5 V rail. Suitable starting parts are a `BAT54` single Schottky or a lower-leakage `BAS70` single Schottky; verify the exact diode ratings and package pinout before selecting the production part.

Keep both diodes and their rail connections close to the PIC. Provide local VDD decoupling and verify that the rail can absorb the injected transient current. A single diode to ground only clamps negative excursions and does not protect against positive overvoltage.

## Zener and TVS guidance

Do not automatically place a conventional `5.1 V` zener directly from every ADC pin to ground. That approach can load the signal near full scale, leak current into the ADC measurement, clamp too late, and fail to protect against negative excursions.

Use a low-leakage rail-clamp arrangement or a suitably specified TVS/zener on the source side of the series resistor when the transient environment requires it. Select the clamp standoff voltage, leakage, capacitance, and pulse-current rating for the actual signal. The protection must not interfere with the required `0-5 V` measurement range.

Small-signal Schottky diodes are not energy absorbers. For `RB2`, `RB3`, PTT wiring, long cables, or any source that can deliver a high-energy transient, add a suitably rated TVS/zener on the source side of the `1 kOhm` resistor or use a proper level/protection interface. Size that device from the expected transient voltage and energy rather than choosing a nominal zener voltage alone.

## Other external interfaces

- `RC0 / INPUT_PTT`: If PTT leaves the board or comes from an open-collector, open-drain, long-cable, or non-5 V source, add series resistance and suitable clamping or use a level translator. A pull-up alone is not overvoltage protection.
- `RB4 / INPUT_OVERCURRENT_FAULT`: A clean 0-5 V push-pull comparator output does not need this ADC protection network. Protect the interface if the comparator output is exposed to cable transients or can exceed the PIC rails.
- `RC2`, `RB0`, and `RB6` rotary encoder contacts: No zener is required for a local PCB-mounted encoder. If the encoder is panel-wired, add modest series resistance and ESD/EMI protection appropriate for the cable run.
- `RC3/RC4` I2C: Do not use zeners as a substitute for the required I2C pull-ups. See [pull-up-resistor-guidance.md](pull-up-resistor-guidance.md).
- `MCLR/VPP`: Follow the reset and ICSP protection recommendations; do not add an arbitrary clamp that interferes with programming or reset timing.
- `RC1`, `RC5-RC7`, and `RB5`: Protect external driver interfaces according to their loads. The fan gate uses a gate resistor and pull-down, not this ADC network.

## PCB checklist

- Place the series resistor close to each PIC ADC pin.
- Fit two single Schottky diodes per ADC input: one from the pin to VSS and one from the pin to VDD, with the orientations specified above.
- Keep analogue clamp connections short and return them to a clean local ground or the regulated rail as appropriate.
- Verify every ADC input at zero, nominal full scale, maximum credible signal, and expected transient conditions.
- Confirm ADC source impedance and acquisition time remain compatible after adding the series resistor and clamps.
- Record final resistor and clamp part numbers in the hardware build record.
