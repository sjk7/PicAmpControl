# PIC16F723A Hardware Pin Map

This document captures the project's current hardware understanding for the PIC16F723A and keeps the MCU pin layout tied directly to each function in the amplifier protection design.

## MCU

- Device: PIC16F723A
- Package: 28-pin MCU (assumed for this design based on the current firmware)
- Clock: 20 MHz crystal on OSC1/OSC2
- Core concept: measure forward and reflected signals, calculate SWR and power, drive alarms, and display status

## Project Signal Map

| PIC Pin | Port/Signal | Project Function | Direction | Notes |
|---|---|---|---|---|
| 11 | RC0 | NET_SWITCH | Input | High = net mode, low = forward mode |
| 12 | RC1 | REALTIME_SWITCH | Input | High = real-time, low = PEP mode |
| 14 | RC3 | ALARM_2_1 | Output | Alarm for 2:1 SWR threshold |
| 15 | RC4 | ALARM_3_1 | Output | Alarm for 3:1 SWR threshold |
| 16 | RC5 | LCD_RS | Output | 1602 LCD register select |
| 17 | RC6 | LCD_RW | Output | 1602 LCD read/write |
| 18 | RC7 | LCD_EN | Output | 1602 LCD enable |
| 19-26 | RB0-RB7 | LCD_DATA[0..7] | Output | LCD data bus D0-D7 |
| 2 | RA0 | FWD_ADC_INPUT | Input | Forward power ADC channel 0 |
| 3 | RA1 | REF_ADC_INPUT | Input | Reflected power ADC channel 1 |
| 5 | RA3 | SPARE/DIAG_ADC | Input | Present in current code as an ADC-capable input |
| 9,10 | OSC1, OSC2 | XTAL_IN/OUT | Input/Output | 20 MHz crystal |
| 1 | MCLR/VPP | RESET | Input | Master clear / reset control |
| 4,6,7,8,13,27,28 | VSS/VDD/NC | Power / support | Power | Follow datasheet for supply decoupling and grounds |

## Functional Grouping

### ADC Measurement Paths

- Forward power sense: RA0 / AN0
- Reflected power sense: RA1 / AN1
- Optional diagnostic/monitor input: RA3 / AN3

### LCD Interface

- RS: RC5
- RW: RC6
- EN: RC7
- Data bus: RB0-RB7

### Alarm Outputs

- ALARM_2_1: RC3
- ALARM_3_1: RC4

### User Controls

- NET_SWITCH: RC0
- REALTIME_SWITCH: RC1

## Wiring Notes

- The current implementation assumes direct digital writes to the LCD data port and direct reads from the mode switch pins.
- The ADC is configured for the selected analog channels, so the input pin naming is essential for hardware debugging.
- The system appears to rely on a 20 MHz crystal and a low-noise 5 V supply arrangement as typical for the PIC16F723A.

## Project Ownership Rule

When making changes to the amplifier protection system, update this document first whenever a pin is repurposed or a new hardware function is added. This keeps the firmware and the physical layout aligned.

## Recommended Next Step

Create a dedicated board-level schematic/table that maps each pin to connector labels, voltages, and external hardware such as:

- RF detector outputs
- LCD header
- alarm relay driver
- external switches
- power conditioning lines
