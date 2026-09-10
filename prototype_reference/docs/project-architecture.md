# Linear Amplifier Protection System Architecture

## Goal

Build a PIC16F723A-based protection controller for a linear amplifier that monitors RF power, estimates SWR, protects the amplifier from fault conditions, and presents fault status on an LCD.

## High-Level Blocks

1. RF sensing inputs
   - Forward power detector
   - Reflected power detector
   - Signal conditioning and ADC acquisition

2. Protection logic
   - Power calculation
   - SWR estimation
   - threshold comparison
   - latching alarm states
   - trip / reset behavior

3. Outputs
   - alarm signals
   - amplifier enable or disable control
   - fault indicators
   - LCD display interface

4. Human interface
   - mode switches
   - LCD status display
   - fault / warning indicators

## State Model

The system should evolve from a simple measurement approach into a formal state machine.

### Recommended states

- STANDBY
- IDLE
- OPERATE
- WARNING
- TRIP
- FAULT_LATCHED
- RESET_WAIT

## Key Safety Rules

- SWR thresholds must be compared using filtered or averaged samples.
- Fault latches must stay active until reset or safe condition is restored.
- Alarm output timing should be based on real hardware response rather than only raw ADC thresholds.
- Fault states must be visible on the LCD and, if possible, on hardware outputs.

## Design Principles

- Keep the hardware map explicit in one file.
- Keep the firmware state machine separate from the MCU pin definitions.
- Use named constants instead of raw magic numbers.
- Treat the current project as the sensor/display prototype, not the final product logic.
