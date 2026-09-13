# ADC Input Protection Guidance

This note defines the planned protection approach for the PIC16F18855 analogue inputs. Component values are starting points and must be confirmed against the final sensor circuits, source impedance, transient environment, and PIC16F18855 electrical specifications.

## Inputs requiring protection

Each ADC signal should include a nominal `1 kOhm` series resistor before the PIC pin and suitable low-leakage clamp protection close to the PIC:

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
                                  low-leakage clamps
                                    to VSS and/or VDD
```

## Zener and TVS guidance

Do not automatically place a conventional `5.1 V` zener directly from every ADC pin to ground. That approach can load the signal near full scale, leak current into the ADC measurement, clamp too late, and fail to protect against negative excursions.

Use a low-leakage rail-clamp arrangement or a suitably specified TVS/zener on the source side of the series resistor when the transient environment requires it. Select the clamp standoff voltage, leakage, capacitance, and pulse-current rating for the actual signal. The protection must not interfere with the required `0-5 V` measurement range.

## Other external interfaces

- `RC0 / INPUT_PTT`: If PTT leaves the board or comes from an open-collector, open-drain, long-cable, or non-5 V source, add series resistance and suitable clamping or use a level translator. A pull-up alone is not overvoltage protection.
- `RB4 / INPUT_OVERCURRENT_FAULT`: A clean 0-5 V push-pull comparator output does not need this ADC protection network. Protect the interface if the comparator output is exposed to cable transients or can exceed the PIC rails.
- `RC2` and `RB0` local menu switches: No zener is required for the local switches. Optional series resistance is an ESD/EMI design choice.
- `RC3/RC4` I2C: Do not use zeners as a substitute for the required I2C pull-ups. See [pull-up-resistor-guidance.md](pull-up-resistor-guidance.md).
- `MCLR/VPP`: Follow the reset and ICSP protection recommendations; do not add an arbitrary clamp that interferes with programming or reset timing.
- `RC1`, `RC5-RC7`, and `RB5`: Protect external driver interfaces according to their loads. The fan gate uses a gate resistor and pull-down, not this ADC network.

## PCB checklist

- Place the series resistor close to each PIC ADC pin.
- Keep analogue clamp connections short and return them to a clean local ground or the regulated rail as appropriate.
- Verify every ADC input at zero, nominal full scale, maximum credible signal, and expected transient conditions.
- Confirm ADC source impedance and acquisition time remain compatible after adding the series resistor and clamps.
- Record final resistor and clamp part numbers in the hardware build record.
