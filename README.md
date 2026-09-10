# Linear Amplifier Protection Controller

## Overview

This repository contains the current design for a PIC16F723A-based linear amplifier protection controller. The project is intentionally separated from the old RF/SWR prototype and is now focused on hardware fault protection, safe amplifier enable/disable behavior, operator feedback, and startup/latched fault handling.

## Current project status

The project is in a working design-and-firmware skeleton stage:

- the MCU pin map is documented and approved for the protection controller
- the state-machine concept is defined
- the firmware includes a protection-state skeleton and startup inhibit logic
- the build is configured through CMake for a PIC XC8 toolchain flow
- GitHub Actions workflows are in place for remote build/release automation

## Key documentation

- Architecture overview: [docs/project-architecture.md](docs/project-architecture.md)
- Hardware pin map: [docs/hardware/PIC16F723A_pin_map.md](docs/hardware/PIC16F723A_pin_map.md)
- Bench validation procedure: [docs/hardware/bench-validation.md](docs/hardware/bench-validation.md)
- Firmware entry point: [firmware/src/main.c](firmware/src/main.c)
- Pin definitions: [firmware/include/pin_map.h](firmware/include/pin_map.h)
- LCD and software-I2C driver: [firmware/src/lcd_i2c.c](firmware/src/lcd_i2c.c)
- LCD driver interface: [firmware/include/lcd_i2c.h](firmware/include/lcd_i2c.h)
- Production CMake project: [cmake/My_Pic_Project/default/CMakeLists.txt](cmake/My_Pic_Project/default/CMakeLists.txt)
- GitHub Actions build workflow: [.github/workflows/firmware-build.yml](.github/workflows/firmware-build.yml)
- GitHub Actions release workflow: [.github/workflows/release-firmware.yml](.github/workflows/release-firmware.yml)

## Design direction

The controller is intended to use a layered protection model:

- hardware comparator trips for critical faults
- PIC firmware state machine for monitoring and safe sequencing
- I2C LCD status output using a standard backpack
- PTT-based re-arm behavior without bypassing live hardware faults
- startup inhibit and fault-latch behavior for safe operation

## Hardware overview

```mermaid
flowchart LR
    subgraph RF["RF path"]
        PRE["SWR sensor 1\nPre-LPF"]
        FILTER["Low-pass filter bank"]
        POST["SWR sensor 2\nPost-LPF"]
    end

    subgraph ADC["ADC measurement inputs"]
        PRE_FWD["ADC_SWR1_FWD"]
        PRE_REF["ADC_SWR1_REF"]
        POST_FWD["ADC_SWR2_FWD"]
        POST_REF["ADC_SWR2_REF"]
        TEMP["ADC_TEMP\n10 kOhm NTC"]
        OVERDRIVE["ADC_OVERDRIVE\nsoftware trip"]
        DRAIN_ADC["ADC_DRAIN_PEAK\nsoftware trip"]
    end

    subgraph ComparatorBoard["Comparator / protection board"]
        OC["Overcurrent comparator"]
        COMP_RESET["Comparator latch reset"]
    end

    subgraph MCU["PIC16F723A controller"]
        PTT["INPUT_PTT\nTransmit request"]
        RESET["OUTPUT_COMP_RESET\nComparator reset"]
        HARD["INPUT_OVERCURRENT_FAULT\nHardware overcurrent fault"]
        TICK["Timer0 ISR\n1 ms scheduler tick"]
        STATE["State machine"]
        SWR1["SWR pair 1\nsoftware trip logic"]
        SWR2["SWR pair 2\nsoftware trip logic"]
        TX["OUTPUT_TX\nTX sequence 1"]
        TXVCC["OUTPUT_TX_VCC\nTX sequence 2"]
        TXBIAS["OUTPUT_TX_BIAS\nTX sequence 3"]
        FAN["OUTPUT_FAN_PWM\nFan speed"]
        WARN["OUTPUT_WARNING_STATUS\nWarning"]
        TRIP["OUTPUT_TRIP_STATUS\nTrip"]
        LCD["1602 LCD\nPCF8574 I2C"]
        EEPROM["AT24C256\nsettings storage"]
    end

    PRE --> PRE_FWD
    PRE --> PRE_REF
    FILTER --> POST
    POST --> POST_FWD
    POST --> POST_REF

    PRE_FWD --> SWR1
    PRE_REF --> SWR1
    POST_FWD --> SWR2
    POST_REF --> SWR2
    TEMP --> STATE
    OVERDRIVE --> STATE
    DRAIN_ADC --> STATE

    SWR1 --> STATE
    SWR2 --> STATE
    OC -->|fault| HARD
    HARD --> STATE
    TICK -->|schedule| STATE

    PTT --> STATE
    STATE --> RESET
    RESET --> COMP_RESET
    STATE --> TX
    STATE --> TXVCC
    STATE --> TXBIAS
    STATE --> FAN
    STATE --> WARN
    STATE --> TRIP
    STATE -->|software I2C| LCD
    STATE -->|software I2C| EEPROM
```


## Approved hardware pin map

This is the current approved signal map for the protection controller. The 1602 LCD backpack and AT24C256 EEPROM share the software-I2C bus on RC3/RC4.

| PIC pin | Port | Project name | Direction | Function |
|---|---|---|---|---|
| 11 | RC0 | INPUT_PTT | Input | Transmit request / key-down input |
| 12 | RC1 | OUTPUT_COMP_RESET | Output | Active-low 10 ms comparator-latch reset pulse on PTT entry |
| 13 | RC2 | INPUT_MENU_NEXT | Input | Config-menu page select switch |
| 14 | RC3 | OUTPUT_LCD_I2C_SCL | Output | LCD backpack clock line |
| 15 | RC4 | OUTPUT_LCD_I2C_SDA | Output | LCD backpack data line |
| 16 | RC5 | OUTPUT_TX | Output | First TX sequencing driver |
| 17 | RC6 | OUTPUT_TX_VCC | Output | Second TX sequencing driver |
| 18 | RC7 | OUTPUT_TX_BIAS | Output | Final TX sequencing driver |
| 2 | RA0 | ADC_SWR1_FWD | Input | Pre-filter SWR forward power ADC |
| 3 | RA1 | ADC_SWR1_REF | Input | Pre-filter SWR reflected power ADC |
| 4 | RA2 | ADC_SWR2_FWD | Input | Post-filter SWR forward power ADC |
| 5 | RA3 | ADC_SWR2_REF | Input | Post-filter SWR reflected power ADC |
| 7 | RA5 | ADC_TEMP | Input | Temperature sensor ADC |
| 9,10 | OSC1, OSC2 | XTAL_IN/OUT | Input/Output | 20 MHz crystal |
| 1 | MCLR/VPP | RESET | Input | Master clear reset |
| 19 | RB0 | INPUT_MENU_ADJUST | Input | Menu adjust switch: short press increase, hold decrease |
| 20 | RB1 | INPUT_SPARE_1 | Input | Freed spare input |
| 21 | RB2 | ADC_OVERDRIVE | Input | Scaled overdrive-sense ADC |
| 22 | RB3 | ADC_DRAIN_PEAK | Input | Scaled drain-peak-sense ADC |
| 23 | RB4 | INPUT_OVERCURRENT_FAULT | Input | Active-high overcurrent comparator fault |
| 24 | RB5 | OUTPUT_FAN_PWM | Output | Fan speed control |
| 25 | RB6 | OUTPUT_WARNING_STATUS | Output | Warning status output |
| 26 | RB7 | OUTPUT_TRIP_STATUS | Output | Trip status output |
| 4,6,7,8,27,28 | VSS/VDD/NC | Power / support | Power | Follow datasheet decoupling rules |

## Current hardware assumptions

- MCU: PIC16F723A
- Clock: 20 MHz crystal
- Display: 1602 LCD with I2C backpack only
- Protection faults: software-driven SWR, overdrive, drain-voltage, and temperature thresholds, backed by an independent hardware overcurrent comparator
- SWR measurement pairs: two ADC pairs are required, one before and one after the low-pass filter bank, each with forward and reflected inputs
- ADC wiring: RA0-RA3, RA5, RB2, and RB3 directly sample the two SWR pairs, temperature, overdrive, and drain voltage; no external analog multiplexer is fitted
- Operator control: INPUT_PTT
- Configuration controls: INPUT_MENU_NEXT and INPUT_MENU_ADJUST; each switch is active-low and is available only while not transmitting
- Sequencing outputs: OUTPUT_TX, OUTPUT_TX_VCC, and OUTPUT_TX_BIAS
- Status outputs: OUTPUT_WARNING_STATUS and OUTPUT_TRIP_STATUS
- Output rule: all operational outputs default to active-low and can be individually changed to active-high in the receive-only configuration menu
- Input rule: input pin names follow the actual hardware comparator/sensor polarity; no polarity suffix is added unless a signal deliberately breaks the default output rule

## SWR measurement logic

Each SWR channel is measured independently at its own RF point.

- Read the forward sample at that point.
- Read the reflected sample at that point.
- Compute the SWR for that local pair.
- Compare the result against the configured threshold.
- If the SWR exceeds the threshold, trip that channel.
- The pre-filter default trip is 3:1 and the post-filter default trip is 2:1; either is configurable in the menu.

This applies to both SWR measurement points:

- pre-filter SWR sensor 1
- post-filter SWR sensor 2

The same logic is used for each pair and each sensor trips independently. A single high SWR at one measurement point must not be masked by a healthy reading at the other point.

## User configuration

The 1602 display config menu uses two active-low, normally-open switches wired from the menu input pins to ground. RC2 selects the displayed configuration page. RB0 is the adjust button: a short press increases the selected value; holding it for 500 ms then decreases the value repeatedly every 100 ms. A button action is accepted only while PTT is inactive, so a threshold cannot change during transmit. RB1 is freed as a spare input.

The menu also configures the sequencer. TX-to-VCC and VCC-to-bias delays are adjustable from 0 to 1000 ms in 5 ms steps, each defaulting to 20 ms. The active electrical level for OUTPUT_TX, OUTPUT_TX_VCC, OUTPUT_TX_BIAS, OUTPUT_FAN_PWM, OUTPUT_WARNING_STATUS, and OUTPUT_TRIP_STATUS is selectable as LOW or HIGH, with LOW as the default. LCD I2C polarity is not configurable because its open-drain signalling is defined by the I2C bus.

All menu settings and the selected display page are saved to the AT24C256 at each operator change. The stored record includes a magic value, format version, and checksum. At power-up the record is restored only when valid; a missing, incompatible, or corrupted record loads the compiled safe defaults and the primary status page.

Menu changes mark the settings record dirty rather than writing immediately. After a 100 ms quiet period, firmware writes the record only while PTT is inactive, no software fault is latched, and the hardware overcurrent input is clear. This coalesces rapid button presses and keeps EEPROM write latency out of the immediate protection decision path.

The default status screen displays post-filter forward power. Its primary readout can be selected as RMS or PEP, and the second row is a full-width PEP bar referenced to the configured post-filter maximum power. The common bar style uses `-` for measured PEP and `.` for unused capacity. A second status page shows `PEP ------------` with the temperature in degrees C on the next row. PEP is held and decays by one watt at a configurable 50-2000 ms interval; the default is 500 ms.

The menu makes these firmware trip thresholds available to the operator:

- pre-filter SWR trip ratio, from 1.1:1 to 5.0:1 in 0.1:1 steps; default 3:1
- post-filter SWR trip ratio, from 1.1:1 to 5.0:1 in 0.1:1 steps; default 2:1
- SWR1 forward full-scale power, from 500 W to 2500 W in 100 W steps; default 1500 W and also used for SWR1 reflected-power conversion
- SWR2 forward full-scale power, from 500 W to 2500 W in 100 W steps; default 1500 W and also used for SWR2 reflected-power conversion
- NTC B-value profile: B3435, B3950, or B4250; default B3950
- temperature warning, from 0 C to 150 C; default 70 C
- temperature trip, from 0 C to 150 C; default 100 C
- input-power warning, from 0.0 W to 10.0 W in 0.1 W steps
- input-power trip, from 0.0 W to 10.0 W in 0.1 W steps; default 10.0 W
- drain-voltage warning, from 0 V to 300 V in 1 V steps
- drain-voltage trip, from 0 V to 300 V in 1 V steps; default 150 V
- current trip, from 0 A to 100 A in 1 A steps; default 40 A, using WCS1700 on RB1/AN6

Each SWR ratio setting directly controls its local software trip: the controller calculates the mismatch from that sensor's forward/reflected pair and trips when it reaches the displayed setting. There are no dedicated SWR comparator inputs in this design.

The ADC reference is the regulated nominal 5.0 V VDD rail, so every analogue input is scaled from 0 to VDD, not to an independently guaranteed 5 V reference. With VDD regulated at 5.0 V, drain voltage uses a linear scale: ADC 0-1023 represents 0-300 V. Input power is calculated as peak-envelope power into 50 ohms, with ADC 0-1023 representing 0-10.0 W. This requires the input detector/divider to present 5 V at 31.62 V peak, a scale factor of approximately 6.325:1. Each SWR bridge detector also uses a 0-5 V range. Its bridge-specific 500-2500 W forward full-scale setting is shared by the associated reflected detector, so both readings use the same power range before SWR is calculated. The WCS1700 current ADC on RB1/AN6 uses a provisional 70 A full-scale calibration, with a configurable trip default of 40 A. All analogue paths require series resistance and clamps so the PIC pin remains between VSS and VDD under normal operation. The external overcurrent comparator on RB4 remains the independent fast protection path.

Temperature uses a 10 kOhm NTC divider with a selectable B3435, B3950, or B4250 profile; B3950 is the default. The firmware uses compact lookup points every 10 C from 0 C to 150 C, so displayed temperatures and thermal thresholds have 10 C resolution. The divider must use a 10 kOhm fixed resistor to the regulated 5 V rail and the NTC to ground. Bench-calibrate the selected sensor and resistor tolerance before relying on the warning and trip defaults.

## Naming convention used in code

All hardware symbols should follow the pattern:

- INPUT_... for external sense or control inputs
- OUTPUT_... for drive or status outputs
- Output pins are active-low by default
- Input pins use the actual hardware polarity and comparator behavior

Polarity suffixes are not added to pin names unless a specific signal intentionally breaks the default active-low output rule.

## Firmware state model

The protection controller uses a strict state machine with a hybrid protection model. SWR is computed in firmware from the forward and reflected ADC samples at each RF point. The comparator hardware remains the primary protection layer for fast analog faults such as overdrive, drain peak, and overcurrent. The PIC acts as the logic controller and sequencing manager.

### State definitions

The firmware should implement these states:

- STANDBY
  - system is idle
  - receive mode is active
  - TX outputs are disabled
  - comparators are monitored

- STARTUP_INHIBIT
  - active immediately after power-up
  - holds TX outputs inactive for the startup interval
  - prevents false enable during the first power-on period

- WAIT_FOR_TX
  - PTT is high, so the amplifier is in receive mode
  - no transmit sequence is active
  - the controller continues to monitor temperature, current, and comparator faults

- TX_RESET
  - triggered when INPUT_PTT changes from high to low
  - a 10 ms active-low OUTPUT_COMP_RESET pulse is applied to the comparator latch/reset network
  - this is the same hardware action used for startup inhibit, just triggered on TX entry

- TX_SEQUENCE_1
  - OUTPUT_TX is asserted
  - this is the first transmit relay step and must happen immediately on a valid transmit request

- TX_SEQUENCE_2
  - OUTPUT_TX_VCC is asserted after the first step delay

- TX_SEQUENCE_3
  - OUTPUT_TX_BIAS is asserted after the second step delay

- TX_ACTIVE
  - all sequencing outputs are in their required state and the amplifier is allowed to run
  - normal operation continues while no safety fault is active

- WARNING
  - temperature or other monitored parameter is above warning threshold but below trip threshold
  - warning output is asserted and the display informs the operator

- THERMAL_LOCKOUT
  - configured temperature threshold (typically around 100 C) has been reached or exceeded
  - transmit is forbidden regardless of PTT
  - TX outputs remain disabled
  - this is a hard block, not a soft warning

- FAULT_LATCHED
  - a comparator fault or protection condition has latched
  - TX outputs are forced off
  - the system waits for conditions to return to a safe state and for the next valid re-arm cycle

- TRIP
  - a fault or temperature threshold has been exceeded during TX operation
  - the output sequence is aborted immediately
  - all transmitter outputs are disabled
  - the trip output is asserted
  - this state remains latched until the next safe restart condition

### Critical behavior rules

1. Hardware comparator faults take priority over software logic.
   - If an overdrive, drain peak, or overcurrent comparator indicates a live fault, TX must not start.

2. SWR faults are computed in firmware from the local forward/reflected ADC pair.
   - Each SWR sensor pair is evaluated independently.
   - A sensor trips when its calculated SWR exceeds the configured threshold, default 2:1.

2. PTT high means receive mode.
   - The transmitter is not active.

3. PTT low means transmit request.
   - the transmit sequence begins only after the reset action and safety checks complete.

4. If the configured temperature threshold is exceeded, transmit is blocked regardless of PTT.
   - This is a hard thermal lockout.

5. If the temperature threshold is exceeded during an active transmit sequence, the system immediately trips and disables TX.
   - This is a runtime thermal trip.

6. The reset action is shared between startup inhibit and TX entry.
   - In practice, startup and TX reset are the same hardware intent: clear latched comparator state and force safe idle before enable.

7. SWR protection does not require dedicated SWR comparators once the MCU has forward and reflected samples for each RF point.
   - The MCU computes the SWR and trips the channel in software.

### TX sequence ordering

For a valid transmit request, the controller should complete the sequence in this order:

1. INPUT_PTT goes low
2. apply the 10 ms comparator reset pulse
3. wait for the comparator reset settle time
4. check all comparator inputs and thermal limits
5. if safe, assert OUTPUT_TX
6. wait the first sequencing delay
7. assert OUTPUT_TX_VCC
8. wait the second sequencing delay
9. assert OUTPUT_TX_BIAS
10. enter TX_ACTIVE

All TX outputs are active-low driver lines and are forced inactive whenever a fault, trip, or thermal lockout condition is detected.

### Reset and re-arm behavior

A fresh transmit cycle is allowed only when:

- PTT is low
- no comparator trip is active
- temperature has not reached the trip or lockout threshold
- the output sequence is complete and the RF path is safe

When PTT returns high, the controller disables the TX sequence and returns to receive/idle operation. The next falling PTT edge produces the comparator reset pulse for the following TX cycle.

See [firmware/src/main.c](firmware/src/main.c) for the protection and sequencer logic, and [firmware/src/lcd_i2c.c](firmware/src/lcd_i2c.c) for the LCD transport.

## Build status

The local project build has been validated with the CMake/XC8 flow. [cmake/My_Pic_Project/default/user.cmake](cmake/My_Pic_Project/default/user.cmake) constrains the production build to `firmware/src/main.c` and `firmware/src/lcd_i2c.c`, excluding historical prototype sources that the generated file list may contain.

The firmware uses a Timer0 interrupt tick of approximately 1 ms instead of a blocking 5 ms loop delay. ADC conversion-complete interrupts capture the seven analogue channels without doing protection math in the ISR. The main loop consumes those samples and evaluates software SWR, overdrive, drain, and temperature trips before LCD refresh and menu work. The external overcurrent comparator remains the asynchronous hard-protection path.

GitHub Actions builds on a self-hosted Windows x64 runner. Set these repository variables to the installed toolchain locations on that runner:

- `XC8_DIR`: XC8 `bin` directory containing `xc8-cc.exe` and `xc8-ar.exe`
- `PACK_REPO_PATH`: Microchip pack repository containing `Microchip/PIC16Fxxx_DFP/1.8.167/xc8`

The build workflow runs on pushes and pull requests to `main`, verifies those paths before compiling, and uploads an artifact named `firmware-<commit SHA>`. Releases are manual: dispatch the release workflow with an existing tag and the artifact name from a successful build. This prevents automatic release tags and duplicate releases from ordinary commits.

## TODOs

The following items remain to be finalized before the design is considered complete:

1. Bench-verify the TX sequencing order and set the exact delays for OUTPUT_TX, OUTPUT_TX_VCC, and OUTPUT_TX_BIAS.
2. Confirm the overcurrent comparator reference level, latch behavior, and active-high INPUT_OVERCURRENT_FAULT polarity; measure ADC/software response for overdrive and drain peak.
3. Measure the overcurrent sensor transfer curve and verify the comparator threshold direction.
4. Bench-calibrate the selected 10 kOhm NTC, B-value profile, and 10 kOhm divider against the displayed 10 C lookup points, including the open-sensor high-temperature fallback.
5. Build and validate the selected 12 V low-side logic-level MOSFET fan drive, its PWM-capable output routing, and its temperature schedule.
6. Calibrate the two SWR bridges, 10 W input detector, and 300 V drain divider against traceable measurements at the regulated 5.0 V rail, including the RMS/PEP display and PEP-bar response.
7. Verify that every conditioned ADC input stays between VSS and VDD, including fault/transient tests with the specified external clamps and series resistance.
8. Validate the shared software-I2C LCD/AT24C256 interface, menu switches, 10 ms PTT-triggered comparator reset pulse, settings restore, and interrupted-power recovery on the final PCB.
9. Configure the required self-hosted runner variables, run the GitHub Actions build workflow, and confirm the uploaded firmware artifact before using the manual release workflow.
10. Review the final PCB against the pin map and update the design documentation for any wiring changes before fabrication.

## Repository purpose

This repository is for the current design, documentation, and firmware work for the amplifier protection system. It is not a general-purpose application project; it is a focused embedded safety controller for the amplifier chain.
