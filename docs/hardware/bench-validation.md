# Bench Validation Procedure

This procedure covers the measurements that cannot be established from firmware alone. Perform them before relying on the controller for amplifier protection.

## Test equipment

- regulated 5.0 V controller supply, measured at the PIC VDD pin
- isolated variable DC source for the 300 V drain-divider input
- 50 ohm RF source/load arrangement and calibrated power meter
- DMM and oscilloscope with suitable high-voltage probes
- temperature reference and controlled heat source for the heatsink sensor
- 12 V fan and the final low-side MOSFET drive circuit

## 1. Temperature Sensor Calibration

Hardware configuration:

```text
+5 V -- 10 kOhm 1% resistor -- ADC_TEMP -- 10 kOhm NTC -- GND
```

1. Select the intended NTC B-value profile in the menu. Start with B3950.
2. Measure the heatsink temperature and ADC_TEMP voltage at 20 C, 40 C, 60 C, 70 C, 80 C, 100 C, and 120 C.
3. Compare each displayed temperature to the reference temperature.
4. If the error around the configured trip point is unacceptable, select B3435 or B4250, or replace the NTC/divider with components whose datasheet matches the selected profile.
5. Confirm that increasing heatsink temperature produces a lower ADC count with the NTC connected to ground.
6. Verify a transmit lockout/trip at the configured trip setting.

Acceptance criteria:

- the selected B-value profile is recorded with the physical NTC part number
- display error around 70 C and 100 C is within the chosen protection tolerance
- a disconnected ADC_TEMP lead is treated as a fault or a conservative high-temperature condition before final release

## 2. Fan Drive

Selected topology:

```text
12 V fan positive -- +12 V
12 V fan negative -- drain of logic-level N-MOSFET
MOSFET source -- GND
RB5 OUTPUT_FAN_PWM -- gate resistor -- MOSFET gate
MOSFET gate -- pull-down resistor -- GND
```

Use a logic-level N-MOSFET with a specified low RDS(on) at VGS = 4.5 V. A flyback diode is required for a two-wire brushless fan only if the fan manufacturer does not already provide internal suppression. Confirm the fan datasheet before fitting one.

1. Confirm the actual PIC alternate-function mapping before using RB5 for hardware PWM. Until that is confirmed, treat RB5 as a logic output and use a PWM-capable external driver only if PWM is required.
2. With the fan disconnected, verify the inactive and active gate voltages for both configured output polarities.
3. With the fan connected, verify startup, current, MOSFET temperature, and electrical noise at 0%, 50%, and 100% drive.
4. Define the final temperature schedule. Recommended initial targets are fan off below 50 C, reduced speed from 50 C upward, and full speed near the trip point. A temperature trip must retain full fan drive while TX remains disabled.
5. Verify that the 10 ms PTT-triggered comparator reset pulse, a fault, and PTT release leave the fan in the documented safe state.

## 3. RF Bridge and Input-Power Calibration

All detector outputs must remain within 0 to VDD at the PIC, including expected RF and transient overdrive conditions.

1. Set the regulated PIC VDD to 5.0 V and measure it at the PIC while calibrating.
2. For each bridge, inject known forward power at approximately 10%, 50%, and 100% of the selected full scale. Record the ADC result and displayed power.
3. Confirm each bridge's forward full-scale menu setting maps a 5 V detector output to the intended 500 W to 2500 W maximum.
4. With a controlled mismatch, compare calculated SWR to an external directional coupler or analyser. Verify the independent pre-filter 3:1 default trip and post-filter 2:1 default trip.
5. For input power, verify the detector/divider maps 31.62 V peak across 50 ohms, equal to 10 W PEP, to 5.0 V at ADC_OVERDRIVE. Confirm trip behavior at the configured watt setting.
6. Verify PEP hold, PEP decay, RMS display, and both display bars against a known RF envelope.

## 4. Drain Divider and ADC Input Protection

1. With the amplifier disconnected, apply 0 V, 150 V, 300 V, and the maximum credible fault/transient voltage to the final drain-divider input.
2. Verify ADC_DRAIN_PEAK reads 0 V, 150 V, and 300 V at the corresponding points without exceeding VDD at RB3.
3. Confirm the drain trip threshold operates at the configured voltage value.
4. Oscilloscope-test ADC_TEMP, ADC_OVERDRIVE, and ADC_DRAIN_PEAK during RF keying, PTT transitions, and supply faults.
5. Confirm all ADC pins remain within VSS to VDD. Verify the series resistors and external clamps limit current into the PIC pin protection structures during a fault.
6. Confirm the external overcurrent comparator path asserts INPUT_OVERCURRENT_FAULT fast enough to stop the sequencer independently of ADC polling. Measure and record ADC/software response time for overdrive and drain peak.
7. Calibrate the WCS1700 zero-current offset and sensitivity at several known currents. Replace or confirm the provisional 70 A full-scale, approximately 15-counts-per-amp calibration and verify the default 40 A MCU trip against the hardware comparator threshold.

## 5. Timing and Trip Response

1. Apply controlled SWR, overdrive, and drain-threshold breaches and measure the interval from the conditioned ADC signal crossing the configured threshold to the TX outputs becoming inactive. Include the ADC conversion-complete ISR capture path in the timing record.
2. Confirm LCD refresh and internal EEPROM writes do not occur before protection evaluation in the main loop.
3. Confirm the external overcurrent comparator trips independently of the Timer0 and ADC polling schedule.

### Firmware-derived timing budget (computed from the code; confirm on the bench)

These figures come directly from the clock/register configuration in `firmware/src/main.c`, at the configured `_XTAL_FREQ = 32,000,000` Hz (internal HFINTOSC, `RSTOSC = HFINT32`). Bench-confirm all of them, especially anything marked "typical", since HFINTOSC accuracy (datasheet electrical characteristics, on the order of a few percent over the full temperature/voltage range) proportionally scales every number below.

- **Timer0 tick period:** `T0CS = Fosc/4` (8 MHz instruction clock, 125 ns/instruction), prescaler `T0CKPS = 1:32` (4 us/count), `TMR0L` reloaded to 6 each interrupt (250 counts to overflow) => 250 x 4 us = **1.000 ms nominal**. This governs PEP decay, TX sequencing delays, the comparator-reset pulse, and startup-inhibit timing - it does **not** gate the trip decision itself (see below).
- **ADC clock (TAD):** `ADCON1` selects `ADCS = Fosc/32` => TAD = 32/32,000,000 Hz = **1.0 us**. This is at or near the minimum TAD most PIC16F1xxxx ADC modules specify across temperature - confirm the PIC16F18855 electrical characteristics table before relying on this at temperature extremes.
- **Per-channel conversion time:** using the typical Microchip 10-bit conversion timing of ~11 TAD, each channel takes ~11 us to convert, plus an explicit **5 us acquisition delay** (`ADC_ACQUISITION_US` in `firmware/src/main.c`) inserted after switching `ADPCH` and before starting the conversion, so the sample-and-hold cap settles to the newly-selected channel first - **~16 us/channel** total. The ISR round-robins 8 channels (`g_adc_scan_channels`), so any one channel is at most **~128 us stale** when `update_protection_state()` reads it. Confirm the 5 us figure against the datasheet's acquisition-time formula for each detector's actual source impedance; it is a common conservative industry baseline, not yet bench-verified for this board.
- **Acquisition delay applied in the ISR itself:** the `__delay_us(5)` runs inside the ADC-conversion-complete interrupt, so it briefly (5 us) delays servicing of any other pending interrupt (e.g. Timer0) - negligible next to the 1 ms tick period, and far preferable to converting on an unsettled sample.
- **Trip-decision cadence:** `update_protection_state()` runs on every main-loop pass, unconditionally - it is not gated by the 1 ms Timer0 tick. So the software decision latency is bounded only by ADC staleness above, plus however long the main loop is blocked elsewhere before it loops back.
- **LCD writes are queued, not blocking.** `lcd_write_byte()` in `lcd_i2c.c` enqueues into a 56-entry ring buffer instead of bit-banging immediately; the main loop drains it via `lcd_service(2)` (2 bytes per pass, ~780 us worst case) after `update_protection_state()` has already run that pass. Each byte still costs ~390 us to actually transmit (2 nibbles x 2 I2C byte-writes x (8 bits x ~10 us/bit-cell + ~10 us ACK)), so a full ~34-byte STATUS-page redraw still takes ~13 ms of *wall-clock* time to fully appear, spread across ~17 loop passes - but `update_protection_state()` is no longer starved for more than ~2 bytes' worth (~780 us) between checks. The one exception is the LCD "Clear Display" command on an actual page/state transition (`lcd_write_byte_now()` + a mandatory 2 ms settle delay per the HD44780 timing spec) - that one remains a real, synchronous block, but it only happens on a transition, not on every periodic refresh.
- **Combined worst-case firmware reaction time:** ADC staleness (<= ~0.13 ms) + LCD queue drain (~0.8 ms between `update_protection_state()` calls, or up to ~2 ms including a page-transition clear) => **low single-digit milliseconds**, no longer dominated by a ~13 ms LCD stall. This applies both to ADC-based software trips and to how quickly firmware can act on the external overcurrent comparator's output (`INPUT_OVERCURRENT_FAULT`) - the comparator itself trips asynchronously in hardware, but cutting `OUTPUT_TX`/`OUTPUT_TX_VCC`/`OUTPUT_TX_BIAS` in response still goes through this same main-loop path.
- Measure item 1 above with this budget in mind: if the bench-measured interval is markedly larger than a few milliseconds, suspect an unexpectedly slow loop iteration or a stuck LCD transaction rather than the ADC/Timer0 configuration.

## Records

Record the final NTC part number/B value, divider resistor values, detector slopes, bridge scales, comparator thresholds, fan part number/MOSFET part number, and the final TX delays in the build record. Update the pin map and firmware defaults only after those values are measured.
