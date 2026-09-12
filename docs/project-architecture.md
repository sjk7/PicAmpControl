# Linear Amplifier Protection System Architecture

## Goal

Build a PIC16F18855-I/SP-based linear amplifier protection controller that monitors RF power, SWR, temperature, current, and drain stress, and shuts down the amplifier safely when the system enters a fault condition.

## High-level blocks

1. RF and power sensing
   - forward power detector
   - reflected power detector
   - overdrive detector
   - drain peak detector
   - overcurrent sensor handling

2. Comparator protection stage
   - overcurrent comparator
   - active-high overcurrent fault output to the PIC

3. Microcontroller logic
   - direct ADC monitoring of four SWR detector outputs, temperature, overdrive, and drain voltage
   - formal protection state machine
   - latching fault states
   - PTT re-arm logic
   - amplifier enable / disable control
   - LCD status display over I2C backpack

4. Thermal and operator management
   - temperature sensing
   - fan-speed control from temperature
   - warning and trip thresholds
   - PTT input for transmit-cycle arming
   - two-switch LCD configuration menu

## Protection strategy

The overcurrent fault is detected by analogue comparator hardware. SWR, overdrive, and drain peak are computed directly in firmware from conditioned ADC data.

Recommended hardware protections:

- overcurrent fault
- temperature warning and final trip threshold

SWR protection is computed locally for each sensing point:

- read the forward and reflected samples for the pre-filter sensor
- compute SWR for that sensor pair
- compare against its configured threshold, default 3:1 for pre-filter and 2:1 for post-filter
- trip if the threshold is exceeded
- repeat the same logic for the post-filter sensor

This allows each SWR monitor to act independently and gives a clear, local protection decision at each stage.

The earlier SWR comparator channels are no longer required in the active design. Their former input pins are assigned to configuration-menu switches.

Eight planned measurements are wired directly to ADC-capable pins: RA0-RA3 for the two SWR pairs, RA5 for temperature, RB1 for current, RB2 for overdrive, and RB3 for drain voltage. No external analog multiplexer is required; the PIC selects the dedicated ADC channels sequentially.

## User threshold configuration

The LCD configuration menu uses two active-low switches: `INPUT_MENU_NEXT` on RC2 and `INPUT_MENU_ADJUST` on RB0. A short adjust press increases the selected value; holding it for 500 ms then decreases the value repeatedly every 100 ms. The operator can select and adjust an independent SWR trip ratio for each detector pair, from 1.1:1 to 5.0:1 in 0.1:1 steps. The pre-filter default is 3:1 and the post-filter default is 2:1. Each bridge has one forward full-scale setting from 500 W to 2500 W in 100 W steps, defaulting to 1500 W; its paired reflected reading uses that same setting. Temperature uses selectable B3435, B3950, or B4250 10 kOhm NTC profiles, defaulting to B3950, with warning/trip settings from 0 C to 150 C. Input power is adjustable from 0.0 W to 10.0 W in 0.1 W steps and defaults to a 10.0 W trip. Drain voltage is adjustable from 0 V to 300 V in 1 V steps and defaults to a 150 V trip. Changes are locked out during transmit. RB1 remains a spare input.

The operator can also configure the TX-to-VCC and VCC-to-bias sequencing delays from 0 to 1000 ms in 5 ms steps; both default to 20 ms. Each operational output can be configured active-low or active-high, with active-low as the default: TX, TX_VCC, TX_BIAS, fan, warning, and trip. LCD I2C signalling remains fixed as open-drain bus logic and is driven by the dedicated software-I2C module.

The status pages refresh every 100 ms from the post-filter forward-power ADC reading. The primary page presents a smoothed RMS or PEP peak-hold value on row one and a full-width PEP bar on row two. A second page presents `PEP ------------` on row one with temperature in degrees C on row two. The common bar renderer uses `-` for measured PEP and `.` for unused capacity, filling all remaining horizontal columns after each label. The PEP hold decays by one watt per configured interval, adjustable from 50 to 2000 ms and defaulting to 500 ms.

The software trip comparison follows the displayed ratio rather than a raw ADC limit. For a configured ratio $S$, it trips when the paired measurements satisfy $R(S+1)^2 \geq F(S-1)^2$, where $F$ is forward power and $R$ is reflected power. Each bridge's single forward full-scale setting converts both its forward and reflected ADC results to physical power before this comparison. This is the standard SWR relationship expressed without floating-point arithmetic. The forward sample must exceed a small noise floor before this comparison can trip.

Overdrive and drain voltage each have a separate, conditioned ADC path. The ADC reference is VDD, so valid conversion input is 0 to the regulated nominal 5.0 V rail. The drain divider maps 5.0 V ADC full scale to 300 V, so $V_{drain}=300r/1023$, where $r$ is the ADC result. The input-power detector/divider maps 31.62 V peak at the 50-ohm input to 5.0 V ADC full scale, yielding peak-envelope power $P=10(r/1023)^2$ W. The scaling values must be recalibrated if VDD is not maintained at 5.0 V. Their menu-configured software warning and trip limits supplement, but never replace, the analogue comparator thresholds. The overdrive, drain-peak, and overcurrent comparator outputs are combined into one active-high `INPUT_HARD_FAULT` signal; it is always a hard trip.

## LCD strategy

Use a standard low-cost 16x2 or 20x4 character LCD fitted with a PCF8574-based I2C backpack.

The PIC16F18855-I/SP implementation uses a dedicated `lcd_i2c.c` software-I2C module on RC3/RC4. The module owns the PCF8574 transfers and HD44780 character commands; protection and menu logic remain in `main.c`. Settings persist via the PIC's internal EEPROM (256 bytes) using the XC8 `eeprom_read`/`eeprom_write` runtime functions, wrapped by `internal_eeprom_read`/`internal_eeprom_write`. Every operator page or value change stores a versioned, checksummed record. Startup accepts only a valid record and otherwise restores compiled safe defaults. The final PCB validation must include read/write and interrupted-power recovery tests.

Benefits:

- saves GPIO pins compared with a parallel LCD interface
- cheap and widely available
- simple software interface
- leaves more MCU pins for comparator inputs and control outputs

## State model

The system should use a formal state machine rather than ad hoc alarms.

Recommended states:

- STANDBY
- IDLE
- OPERATE
- WARNING
- TRIP
- FAULT_LATCHED
- RESET_WAIT

The main loop is paced by a Timer0 interrupt tick of approximately 1 ms rather than a blocking 5 ms delay. ADC conversion-complete interrupts capture samples and advance the channel scan, but perform no conversion math or state-machine calls. The main loop consumes the latest samples and updates protection before LCD rendering and menu/EEPROM work. EEPROM writes are deferred until 100 ms after the last menu change and only occur while receive mode is safe. This removes blocking ADC reads while keeping the ISR small enough for XC8, while the external overcurrent comparator remains the asynchronous hard-fault path.

## PTT and re-arm behavior

PTT must act as a transmit-cycle re-arm event.

Rules:

- on the PTT falling edge, the PIC must issue the 10 ms comparator reset pulse before it can clear software-latched fault state
- a live comparator fault must not be bypassed by entering PTT
- if a hardware condition is still outside limits, the amplifier must remain disabled
- the startup power-up interval should keep the amplifier off for about 0.5 to 1.0 seconds after applying power
- On the PTT falling edge, OUTPUT_COMP_RESET produces a 10 ms active-low pulse to clear the overcurrent comparator latch. INPUT_OVERCURRENT_FAULT must then be clear before the controller re-arms software latches or begins sequencing.

## Temperature and fan strategy

Temperature uses a 10 kOhm NTC thermistor divider on the ADC input, with a 10 kOhm fixed resistor to the regulated 5 V rail and the NTC to ground. The configuration menu selects B3435, B3950, or B4250; B3950 is the default. The firmware contains compact 10 C lookup points from 0 C to 150 C for each profile. A near-full-scale ADC result is treated as 150 C so an open NTC lead produces a conservative thermal lockout. The selected profile and physical divider must be bench-calibrated before the temperature warning/trip settings are relied upon.

Recommended behavior:

- warning threshold: fan increases speed or begins operation
- higher threshold: fan speed increases further
- critical threshold: amplifier trips and disables output

The selected fan design is a 12 V fan driven by a low-side logic-level N-MOSFET from OUTPUT_FAN_PWM. The final PCB must confirm whether RB5 can provide the required hardware PWM alternate function; otherwise use an external PWM driver. The required circuit and test procedure are in [docs/hardware/bench-validation.md](hardware/bench-validation.md).

## Overcurrent sensor handling

The current sensor described as 2.5 V at max current, dropping toward 0 V as current increases, is an inverse current-monitor signal.

The protection logic should be implemented as:

- compare the sensor voltage against a threshold
- treat drop below threshold as overcurrent
- allow the comparator to latch the fault if the limit is crossed

This is a valid analog threshold scheme, but the reference must be chosen carefully using the real sensor transfer curve.

## Safety rules

- The overcurrent fault that requires asynchronous response must be detected in hardware first; software ADC trips have a bounded Timer0/main-loop response and must not be described as comparator-speed protection.
- Every ADC voltage input must be scaled, clamped, and filtered to remain between $0$ and $V_{DD}$.
- Software latches must not override comparator faults.
- Fault states should remain latched until conditions are safe and the system is re-armed.
- Alarm output behavior must match actual hardware response and startup timing.
- Fault conditions must be visible on the LCD and reflected in the amplifier enable logic.

## Design principles

- Keep the hardware map explicit in one file.
- Keep the firmware state machine separate from the MCU pin definitions.
- Use named constants instead of raw magic numbers.
- Treat the prototype folder as the measurement/reference implementation, not the final protection controller.
- Build firmware on a self-hosted Windows runner with the XC8 toolchain and PIC16Fxxx device pack installed; publish releases only from an explicitly selected successful build artifact.

## Recommended implementation order

1. Finalize the comparator board fault assignments
2. Define pin mappings and peripheral setup
3. Create the state machine skeleton with PTT re-arm logic
4. Add ADC monitoring for temperature and diagnostic channels
5. Add warning thresholds, trip detection, and latching logic
6. Add fan control and startup inhibit timing
7. Add LCD operator display and fault messages
8. Validate against real hardware and RF conditions
