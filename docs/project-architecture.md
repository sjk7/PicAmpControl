# Linear Amplifier Protection System Architecture

## Goal

Build a PIC18F47Q10-I/P-based linear amplifier protection controller that monitors RF power, SWR, temperature, current, and drain stress, and shuts down the amplifier safely when the system enters a fault condition.

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
   - band snoop and classification: Timer1 T1CKI frequency counter classifying 160-10 m
   - band selection: one dedicated active-high output per low-pass filter band
   - band lockout: LPF relays frozen for the whole TX cycle, released when back in RX/idle
   - formal protection state machine
   - latching fault states
   - PTT re-arm logic, gated on a valid band-snoop signal
   - amplifier enable / disable control
   - LCD status display over a 4-bit parallel interface

4. Thermal and operator management
   - temperature sensing
   - fan-speed control from temperature
   - trip thresholds
   - PTT input for transmit-cycle arming
   - single rotary-encoder LCD configuration menu

## Protection strategy

The overcurrent fault is detected by analogue comparator hardware. SWR, overdrive, and drain peak are computed directly in firmware from conditioned ADC data.

Recommended hardware protections:

- overcurrent fault
- temperature trip threshold

SWR protection is computed locally for each sensing point:

- read the forward and reflected samples for the pre-filter sensor
- compute SWR for that sensor pair
- compare against its configured threshold, default 3:1 for pre-filter and 2:1 for post-filter
- trip if the threshold is exceeded
- repeat the same logic for the post-filter sensor

This allows each SWR monitor to act independently and gives a clear, local protection decision at each stage.

SWR protection is computed entirely in firmware from the forward and reflected ADC readings at each RF point; no dedicated SWR comparator hardware is used.

The eight measurements are wired directly to dedicated ADC-capable pins. No external analog multiplexer is required; the PIC selects the dedicated ADC channels sequentially. See [docs/hardware/PIC18F47Q10_pin_map_and_setup.md](hardware/PIC18F47Q10_pin_map_and_setup.md) for the authoritative pin assignments — they are deliberately not restated here.

## User threshold configuration

The LCD configuration menu uses one EC11-style active-low rotary encoder: `INPUT_ENCODER_A` on RC2, `INPUT_ENCODER_B` on RB0, and `INPUT_ENCODER_SWITCH` on RB6. In normal display mode, rotation selects the home display page and a short press enters settings. In settings mode, rotation edits the current value, short press advances to the next saved setting, and long press exits back to the saved home page. On a trip screen, a long press clears/re-arms the latched fault when the live fault condition is safe. The operator can select and adjust an independent SWR trip ratio for each detector pair, from 1.1:1 to 5.0:1 in 0.1:1 steps. The pre-filter default is 3:1 and the post-filter default is 2:1. Each bridge has one forward full-scale setting from 500 W to 2500 W in 100 W steps, defaulting to 1500 W; its paired reflected reading uses that same setting. Temperature uses selectable B3435, B3950, or B4250 10 kOhm NTC profiles, defaulting to B3950, with a trip setting from 0 C to 150 C. Input power is adjustable from 0.0 W to 10.0 W in 0.1 W steps and defaults to a 10.0 W trip. Drain voltage is adjustable from 0 V to 300 V in 1 V steps and defaults to a 150 V trip. Setting edits are locked out during transmit. RB1 remains dedicated to current sensing.

The operator can also configure the TX-to-VCC and VCC-to-bias sequencing delays from 0 to 1000 ms in 5 ms steps; both default to 20 ms. Each operational output can be configured active-low or active-high, with active-low as the default: TX, TX_VCC, TX_BIAS, fan, and trip. The LCD interface polarity is not configurable; the RS/E/data lines are push-pull outputs.

The status pages refresh every 100 ms from the post-filter forward-power ADC reading. The default home page presents PEP with a shortened `|`/`.` peak bar and temperature in degrees C. Additional normal pages show PEP/RMS plus two-decimal SWR, SWR1/SWR2 detail, and current with peak hold. Peak hold and peak decay are user settings saved in EEPROM; factory defaults are 1200 ms hold and 100 ms decay interval.

The software trip comparison follows the displayed ratio rather than a raw ADC limit. For a configured ratio $S$, it trips when the paired measurements satisfy $R(S+1)^2 \geq F(S-1)^2$, where $F$ is forward power and $R$ is reflected power. Each bridge's single forward full-scale setting converts both its forward and reflected ADC results to physical power before this comparison. This is the standard SWR relationship expressed without floating-point arithmetic. The forward sample must exceed a small noise floor before this comparison can trip.

Overdrive and drain voltage each have a separate, conditioned ADC path. The ADC reference is VDD, so valid conversion input is 0 to the regulated nominal 5.0 V rail. The drain divider maps 5.0 V ADC full scale to 300 V, so $V_{drain}=300r/1023$, where $r$ is the ADC result. The input-power detector/divider maps 31.62 V peak at the 50-ohm input to 5.0 V ADC full scale, yielding peak-envelope power $P=10(r/1023)^2$ W. The scaling values must be recalibrated if VDD is not maintained at 5.0 V. Their menu-configured software trip limits supplement, but never replace, the analogue comparator thresholds. The overdrive, drain-peak, and overcurrent comparator outputs are combined into one active-high `INPUT_HARD_FAULT` signal; it is always a hard trip.

## LCD strategy

Use a standard low-cost 16x2 character LCD driven in **4-bit parallel** mode. There is no PCF8574 I2C backpack; the earlier I2C design was dropped in favour of the direct parallel interface.

The driver lives in `firmware/src/lcd_parallel.c` (its interface header is `firmware/include/lcd_parallel.h`). It owns the HD44780 4-bit transfers; protection and menu logic remain in `main.c`. Settings persist via the PIC's internal EEPROM (256 bytes) using the XC8 `eeprom_read`/`eeprom_write` runtime functions, wrapped by `internal_eeprom_read`/`internal_eeprom_write`. Every operator page or value change stores a versioned, checksummed record. Startup accepts only a valid record and otherwise restores compiled safe defaults. Final PCB validation must include read/write and interrupted-power recovery tests.

## State model

The system should use a formal state machine rather than ad hoc alarms.

Recommended states:

- STANDBY
- IDLE
- OPERATE
- BYPASS_SNOOP (first-dit: PTT latched, amplifier held in bypass until a band is decoded)
- TRIP
- FAULT_LATCHED
- RESET_WAIT

The main loop is paced by a Timer2 interrupt tick of approximately 1 ms rather than a blocking 5 ms delay. ADC conversion-complete interrupts capture samples and advance the channel scan, but perform no conversion math or state-machine calls. The main loop consumes the latest samples and updates protection before LCD rendering and menu/EEPROM work. EEPROM writes are deferred until 100 ms after the last menu change and only occur while receive mode is safe. This removes blocking ADC reads while keeping the ISR small enough for XC8, while the external overcurrent comparator remains the asynchronous hard-fault path.

## PTT and re-arm behavior

PTT must act as a transmit-cycle re-arm event.

Rules:

- on the PTT falling edge, the PIC must issue the 10 ms comparator reset pulse before it can clear software-latched fault state
- a live comparator fault must not be bypassed by entering PTT
- if a hardware condition is still outside limits, the amplifier must remain disabled
- when no band is known, PTT is still latched, but the amplifier stays in bypass until the first RF burst decodes the band (see [First-Dit band detection](first-dit-band-detection.md)); the controller never keys the amplifier on an unverified band
- the startup power-up interval should keep the amplifier off for about 0.5 to 1.0 seconds after applying power
- On the PTT falling edge, OUTPUT_COMP_RESET produces a 10 ms active-low pulse to clear the overcurrent comparator latch. INPUT_OVERCURRENT_FAULT must then be clear before the controller re-arms software latches or begins sequencing.

## Band selection and lockout

The band is determined from the RF snoop signal counted by Timer1 (T1CKI via PPS), not from a manual band switch or a band-decoder bus. The firmware classifies the count into one of six bands (160/80/40/20/15/10 m) on a 10 ms scheduler tick and drives one dedicated active-high output per band into the LPF relay driver. The old 74HC4514 decoder and B0-B2 address bus are gone, and there is no 6 m position.

Band lockout protects the transmit path:

- on a valid PTT request with a usable snoop measurement, the band is locked and the LPF relay selection is frozen for the whole TX cycle
- the lock is released when the amplifier returns to RX/idle, and only once every TX output is inactive, letting the relays follow the next snoop
- if no band has been decoded, PTT is latched and the amplifier is held in bypass while the operator's first RF burst is snooped for: the first dit / first syllable passes straight to the antenna, the counter decodes the band, and only then does the amplifier key on that band
- the decoded band is remembered, so the next PTT on the same band engages instantly without a fresh snoop; the memory is dropped after a period of inactivity, because the operator may have changed bands
- after the relays are commanded for a newly decoded band, the amplifier stays in bypass until the relay contacts have settled, so it is never keyed into a relay that is still moving

Bypass is always safe: the RF path is straight through to the antenna with the LDMOS bias off. The amplifier is never keyed on an unverified band, and the relay selection never moves while it is keyed. The full model, its invariants and its test evidence are in [First-Dit band detection](first-dit-band-detection.md).

The firmware interface is `freq_counter_lock_band()`, `freq_counter_unlock_band()`, `freq_counter_band_confirmed()`, `freq_counter_measured_band()` and `freq_counter_restore_locked_band()` in [firmware/include/freq_counter.h](../firmware/include/freq_counter.h). The flow is diagrammed in [docs/hardware/project_schematic_package/block_diagram.md](hardware/project_schematic_package/block_diagram.md).

## Temperature and fan strategy

Temperature uses a 10 kOhm NTC thermistor divider on the ADC input, with a 10 kOhm fixed resistor to the regulated 5 V rail and the NTC to ground. The configuration menu selects B3435, B3950, or B4250; B3950 is the default. The firmware contains compact 10 C lookup points from 0 C to 150 C for each profile. A near-full-scale ADC result is treated as 150 C so an open NTC lead produces a conservative thermal lockout. The selected profile and physical divider must be bench-calibrated before the temperature trip setting is relied upon.

Recommended behavior:

- lower threshold: fan increases speed or begins operation
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

- The overcurrent fault that requires asynchronous response must be detected in hardware first; software ADC trips have a bounded Timer0/main-loop response and must not be described as comparator-speed protection. See [docs/hardware/bench-validation.md](hardware/bench-validation.md#firmware-derived-timing-budget-computed-from-the-code-confirm-on-the-bench) for the computed reaction-time budget and its tolerances.
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
- Build firmware in CI (`.github/workflows/firmware-build.yml`, `ubuntu-latest`, XC8 v4.00 plus the PIC18F-Q_DFP pack) and publish releases from a successful `main` build artifact.

## Recommended implementation order

1. Finalize the comparator board fault assignments
2. Define pin mappings and peripheral setup
3. Create the state machine skeleton with PTT re-arm logic
4. Add ADC monitoring for temperature and diagnostic channels
5. Add warning thresholds, trip detection, and latching logic
6. Add fan control and startup inhibit timing
7. Add LCD operator display and fault messages
8. Validate against real hardware and RF conditions
