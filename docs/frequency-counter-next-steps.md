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

## LPF band selection bus

The PIC has only four spare GPIOs available for this feature, so the implementation should use them as a 4-bit coarse band code instead of trying to drive one relay per band directly from the MCU. The intended control bus is:

- RA4 = B0
- RA6 = B1
- RA7 = B2
- RB6 = B3

This bus drives an external decode/relay driver stage that energizes the correct low-pass filter for the active band. The firmware should keep the band code in a simple lookup table and only use it for coarse band selection, not for precision frequency readout.

Band-code mapping for the LPF selector:

- 0x1: 160m
- 0x2: 80m
- 0x3: 40m
- 0x4: 20m
- 0x5: 15m
- 0x6: 10m
- 0x7: 6m
- 0x0: all filters off / default

## Hardware requirements

Do not connect raw RF or an unconditioned detector node to a PIC GPIO. Add an external conditioning stage with:

- attenuation appropriate to the RF/detector signal
- limiter or comparator output constrained to 0-5 V
- hysteresis for clean switching
- input clamps and series resistance
- edge rate suitable for the selected PIC input

Confirm the overdrive detector branch can be shared without disturbing the RB2/AN10 amplitude measurement.

## Limitations and scope

This counter is intentionally not a general-purpose RF frequency meter. It is only a coarse band detector whose job is to tell the controller which amateur band is active so the correct output low-pass filter can be selected. It should never be treated as a precision frequency measurement tool, and it is not suitable for tuning, channel discrimination, or any application that requires accurate kHz-level or Hz-level resolution.

The design is limited by several real constraints:

- The PIC16F18855 is not a high-speed frequency-measurement engine. Timer1 counts edges, but it is still a small MCU with limited register width and interrupt overhead.
- The hardware signal must be cleaned by a comparator/limiter stage before it reaches a PIC pin; any analog noise, threshold uncertainty, or ringing will distort the counts.
- A 100 ms or 1 s gate is good for coarse band categorization, but it does not provide precision across a band. The measurement error is dominated by gate duration and by the fact that the band window is much wider than the exact operating frequency of a signal.
- The RF source may vary in frequency or drift within a ham band. A band detector only needs to know, for example, whether the signal is around 3.5 MHz, 7 MHz, 14 MHz, 21 MHz, 28 MHz, or 50 MHz, not whether it is exactly 14.200 MHz.
- The low-pass filter bank itself is also coarse. The correct filter is selected by band range, and the filter network is tolerant to moderate frequency spread within each band. That makes a rough frequency estimate sufficient for the control objective.
- Any analog detector or ADC-based method is worse for this purpose because ADC sampling does not preserve zero crossings and therefore cannot reliably recover the actual RF cycle count. The counter must use a conditioned digital square wave on a spare GPIO, not the overdrive ADC path.

## Why this is only for band detection

The output filter bank is selected by band, not by exact tune frequency. The amplifier only needs to know which low-pass filter range is appropriate for the current RF spectrum. A few hundred hertz or a few kilohertz of uncertainty in the measurement does not change the correct filter choice as long as the measured frequency clearly falls into the correct band bucket.

This is why the design should be implemented with hysteresis and band thresholds rather than exact frequency calibration. For example:

- 160 m: below roughly 2 MHz
- 80 m: roughly 3.5 to 4 MHz
- 40 m: roughly 7 MHz
- 20 m: roughly 14 MHz
- 15 m: roughly 21 MHz
- 10 m: roughly 28 MHz
- 6 m: roughly 50 MHz

These are separated by large enough margins that a coarse timer count is sufficient. The purpose is switching the correct output filter, not publishing an RF frequency display or using the value for fine-grained control.

If a future design needs exact frequency readout, a dedicated measurement subsystem with a more stable reference, better gating, and a calibrated signal path would be required. For the present amplifier controller, the frequency counter is only a band-classification aid and should remain scoped to that use.

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
