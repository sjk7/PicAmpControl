# Frequency Counter Next Steps

## Goal
Add an approximate RF frequency measurement to select the correct low-pass filter while preserving the existing overdrive amplitude ADC measurement.

## Verified direction
Use a conditioned digital square-wave signal on a spare GPIO and count edges with a hardware timer. Do not count frequency from the overdrive ADC directly: the ADC is sampled periodically and does not preserve zero crossings.

Recommended signal path:

```text
RF sample -> overdrive detector -> RB2/AN10 ADC amplitude
          -> limiter/comparator -> spare GPIO -> Timer1 external clock
```

The PIC16F18855 header exposes `T1CKIPPS`, so Timer1 can receive an external clock through PPS. Candidate spare pins are RA6, RA7, or RB6, subject to the final schematic and PPS routing choice. RB6 is currently used only as a simulator scenario marker by the Python trace tool and is not used by firmware hardware behavior.

## Measurement method

Use Timer2's approximately 1 ms scheduler as the gate timer and Timer1 as the edge counter:

- 100 ms gate: frequency approximately `edge_count * 10`
- 1 s gate: frequency approximately `edge_count`
- Formula: `frequency_hz = edge_count / gate_seconds`

A 100 ms gate gives fast updates; a 1 s gate gives finer low-frequency resolution.

## Hardware requirements

Do not connect raw RF or an unconditioned detector node to a PIC GPIO. Add an external conditioning stage with:

- attenuation appropriate to the RF/detector signal
- limiter or comparator output constrained to 0-5 V
- hysteresis for clean switching
- input clamps and series resistance
- edge rate suitable for the selected PIC input

Confirm the overdrive detector branch can be shared without disturbing the RB2/AN10 amplitude measurement.

## Current firmware context

- ADC current/WCS1700 input: RB1/AN9
- Overdrive ADC input: RB2/AN10
- Current spare GPIOs documented: RA4, RA6, RA7, RB6
- Timer2 drives the approximately 1 ms system tick
- EEPROM-backed menu settings and LCD lifecycle are already implemented

## Next implementation steps

1. Confirm the schematic net available for the conditioned frequency signal.
2. Select the spare GPIO and confirm its `T1CKIPPS` PPS code from the PIC16F18855 datasheet/header.
3. Add Timer1 external-clock initialization and a Timer2-gated frequency measurement routine.
4. Add a frequency display/menu page and low-pass filter selection thresholds.
5. Add simulator stimulus and a CTest scenario using a digital square-wave input.
6. Validate the measured frequency and filter selection on hardware with a known RF source.
