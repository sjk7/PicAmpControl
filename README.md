# Linear Amplifier Protection Controller

This workspace is being organized around a dedicated PIC16F723A linear amplifier protection system.

## Purpose

The project is intentionally separated from the older RF/SWR monitoring prototype. The prototype remains available under the reference folder for historical context and for reuse of useful measurement logic, but the new project is focused on safety behavior, fault states, latching, reset, and amplifier protection.

## Reference material

- Old prototype: [prototype_reference](prototype_reference)
- Architecture notes: [docs/project-architecture.md](docs/project-architecture.md)
- Hardware pin map: [docs/hardware/PIC16F723A_pin_map.md](docs/hardware/PIC16F723A_pin_map.md)

## Project direction

The new firmware should be designed around:

- explicit hardware mapping
- a formal protection state machine
- trip thresholds and warning thresholds
- latching fault behavior
- amplifier enable/disable logic
- clear LCD operator feedback

## Status

This is the start of the new controller project. The original code in the reference folder should be treated as a prototype and calibration reference, not as the final protection logic.
