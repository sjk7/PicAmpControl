# Linear Amplifier Protection System Architecture

## Goal

Build a PIC16F723A-based linear amplifier protection controller that monitors RF power, SWR, temperature, current, and drain stress, and shuts down the amplifier safely when the system enters a fault condition.

## High-level blocks

1. RF and power sensing
   - forward power detector
   - reflected power detector
   - overdrive detector
   - drain peak detector
   - overcurrent sensor handling

2. Comparator protection stage
   - SWR protection 1: pre-filter or PA-output side
   - SWR protection 2: post-filter or antenna-output side
   - overdrive fault comparator
   - drain peak voltage comparator
   - overcurrent comparator
   - optional spare comparator input for expansion

3. Microcontroller logic
   - ADC monitoring of temperature, power, and diagnostic channels
   - formal protection state machine
   - latching fault states
   - PTT re-arm logic
   - amplifier enable / disable control
   - LCD status display over I2C backpack

4. Thermal and operator management
   - temperature sensing
   - fan-speed control from temperature
   - warning and trip thresholds
   - fault acknowledge / reset input
   - PTT input for transmit-cycle arming

## Protection strategy

The critical faults should be detected by analog comparator hardware, not only by PIC software.

Recommended hardware protections:

- SWR fault channel 1
- SWR fault channel 2
- overdrive fault
- drain peak fault
- overcurrent fault
- temperature warning and final trip threshold

The PIC should read these comparator outputs and set the controller state, but the analog stage should be the primary protection layer.

## LCD strategy

Use a standard low-cost 16x2 or 20x4 character LCD fitted with a PCF8574-based I2C backpack.

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

## PTT and re-arm behavior

PTT must act as a transmit-cycle re-arm event.

Rules:

- when PTT is asserted, the PIC should clear software-latched fault state after a short settle delay
- a live comparator fault must not be bypassed by entering PTT
- if a hardware condition is still outside limits, the amplifier must remain disabled
- the startup power-up interval should keep the amplifier off for about 0.5 to 1.0 seconds after applying power

## Temperature and fan strategy

Temperature should be monitored on an ADC input using a thermistor or sensor divider.

Recommended behavior:

- warning threshold: fan increases speed or begins operation
- higher threshold: fan speed increases further
- critical threshold: amplifier trips and disables output

The fan can be controlled by simple threshold steps or by PWM if a smoother response is desired.

## Overcurrent sensor handling

The current sensor described as 2.5 V at max current, dropping toward 0 V as current increases, is an inverse current-monitor signal.

The protection logic should be implemented as:

- compare the sensor voltage against a threshold
- treat drop below threshold as overcurrent
- allow the comparator to latch the fault if the limit is crossed

This is a valid analog threshold scheme, but the reference must be chosen carefully using the real sensor transfer curve.

## Safety rules

- Input faults that can damage the amplifier must be detected in hardware first.
- Software latches must not override comparator faults.
- Fault states should remain latched until conditions are safe and the system is re-armed.
- Alarm output behavior must match actual hardware response and startup timing.
- Fault conditions must be visible on the LCD and reflected in the amplifier enable logic.

## Design principles

- Keep the hardware map explicit in one file.
- Keep the firmware state machine separate from the MCU pin definitions.
- Use named constants instead of raw magic numbers.
- Treat the prototype folder as the measurement/reference implementation, not the final protection controller.

## Recommended implementation order

1. Finalize the comparator board fault assignments
2. Define pin mappings and peripheral setup
3. Create the state machine skeleton with PTT re-arm logic
4. Add ADC monitoring for temperature and diagnostic channels
5. Add warning thresholds, trip detection, and latching logic
6. Add fan control and startup inhibit timing
7. Add LCD operator display and fault messages
8. Validate against real hardware and RF conditions
