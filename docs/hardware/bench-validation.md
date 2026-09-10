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
4. If the error around the configured warning and trip points is unacceptable, select B3435 or B4250, or replace the NTC/divider with components whose datasheet matches the selected profile.
5. Confirm that increasing heatsink temperature produces a lower ADC count with the NTC connected to ground.
6. Verify temperature warning at the configured warning setting and a transmit lockout/trip at the configured trip setting.

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
4. Define the final temperature schedule. Recommended initial targets are fan off below 50 C, reduced speed from 50 C to the warning point, and full speed at or above the warning point. A temperature trip must retain full fan drive while TX remains disabled.
5. Verify that the 10 ms PTT-triggered comparator reset pulse, a fault, and PTT release leave the fan in the documented safe state.

## 3. RF Bridge and Input-Power Calibration

All detector outputs must remain within 0 to VDD at the PIC, including expected RF and transient overdrive conditions.

1. Set the regulated PIC VDD to 5.0 V and measure it at the PIC while calibrating.
2. For each bridge, inject known forward power at approximately 10%, 50%, and 100% of the selected full scale. Record the ADC result and displayed power.
3. Confirm each bridge's forward full-scale menu setting maps a 5 V detector output to the intended 500 W to 2500 W maximum.
4. With a controlled mismatch, compare calculated SWR to an external directional coupler or analyser. Verify the independent pre-filter 3:1 default trip and post-filter 2:1 default trip.
5. For input power, verify the detector/divider maps 31.62 V peak across 50 ohms, equal to 10 W PEP, to 5.0 V at ADC_OVERDRIVE. Confirm warning and trip behavior at the configured watt settings.
6. Verify PEP hold, PEP decay, RMS display, and both display bars against a known RF envelope.

## 4. Drain Divider and ADC Input Protection

1. With the amplifier disconnected, apply 0 V, 150 V, 300 V, and the maximum credible fault/transient voltage to the final drain-divider input.
2. Verify ADC_DRAIN_PEAK reads 0 V, 150 V, and 300 V at the corresponding points without exceeding VDD at RB3.
3. Confirm the drain warning/trip thresholds operate at the configured voltage values.
4. Oscilloscope-test ADC_TEMP, ADC_OVERDRIVE, and ADC_DRAIN_PEAK during RF keying, PTT transitions, and supply faults.
5. Confirm all ADC pins remain within VSS to VDD. Verify the series resistors and external clamps limit current into the PIC pin protection structures during a fault.
6. Confirm the external overcurrent comparator path asserts INPUT_OVERCURRENT_FAULT fast enough to stop the sequencer independently of ADC polling. Measure and record ADC/software response time for overdrive and drain peak.
7. Calibrate the WCS1700 zero-current offset and sensitivity at several known currents. Replace or confirm the provisional 70 A full-scale, approximately 15-counts-per-amp calibration and verify the default 40 A MCU trip against the hardware comparator threshold.

## 5. Timing and Trip Response

1. Apply controlled SWR, overdrive, and drain-threshold breaches and measure the interval from the conditioned ADC signal crossing the configured threshold to the TX outputs becoming inactive. Include the ADC conversion-complete ISR capture path in the timing record.
2. Confirm LCD refresh and AT24C256 writes do not occur before protection evaluation in the main loop.
3. Confirm the external overcurrent comparator trips independently of the Timer0 and ADC polling schedule.

## Records

Record the final NTC part number/B value, divider resistor values, detector slopes, bridge scales, comparator thresholds, fan part number/MOSFET part number, and the final TX delays in the build record. Update the pin map and firmware defaults only after those values are measured.
