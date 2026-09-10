# Project Status Notes

## Date
2026-09-10

## Summary
This project started as a PIC16F723A-based RF/SWR monitoring prototype. After review, the conclusion is that the existing code is a useful prototype and reference for a linear amplifier protection system, but it is not yet a full protection controller.

## Decision
The project should evolve into a new, cleaner project specifically for a linear amplifier protection system. The current implementation should be treated as a prototype/reference rather than the final production-control design.

## Important findings
- The code in main.c is a functional firmware for ADC-based forward/reflected power measurement.
- It includes SWR calculations and alarm outputs.
- It has LCD display logic and a 5 ms control loop.
- It is tightly coupled to hardware pin assignments and fixed values.
- It is not yet a full protection system because it does not include a complete state machine, trip logic, reset logic, fault latches, user-mode behavior, or a hardware abstraction model.

## New project direction
The new project should be organized around:
- PIC16F723A hardware layout and pin map
- clear firmware architecture
- a formal protection state machine
- fault definitions and trip thresholds
- amplifier enable/disable behavior
- warning vs trip logic
- LCD status display and operator feedback

## Hardware mapping status
The project currently documents the following relevant mappings:
- RC0 = NET_SWITCH
- RC1 = REALTIME_SWITCH
- RC3 = ALARM_2_1
- RC4 = ALARM_3_1
- RC5 = LCD_RS
- RC6 = LCD_RW
- RC7 = LCD_EN
- RB0-RB7 = LCD_DATA[0..7]
- RA0 = forward power ADC input
- RA1 = reflected power ADC input
- RA3 = spare/diagnostic ADC input
- OSC1/OSC2 = 20 MHz crystal

## Folder structure used during setup
- root project folder: My_Pic_Project
- docs/hardware/PIC16F723A_pin_map.md
- docs/project-architecture.md
- firmware/include/pin_map.h
- firmware/src/main.c

## Recommended next steps
1. Create a new project folder elsewhere for the real amplifier protection controller.
2. Copy the hardware map and architecture docs into the new project.
3. Keep the original prototype as a reference only.
4. Implement a state machine for standby, operate, warning, and trip.
5. Add explicit safety thresholds and latch/reset behavior.
6. Update hardware pin documentation whenever the design changes.

## Final note
This note preserves the status of the work so far: the prototype exists, the protection-system direction is chosen, the hardware mapping is understood, and the project is ready to move cleanly into a new folder.
