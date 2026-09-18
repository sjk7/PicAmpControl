# Functional Netlist/Connection Table – Amplifier Protection Board

**Legend:**
- All pin numbers must be confirmed against part datasheets/pin maps during schematic capture.
- Use native net label names as shown for clarity.

## 1. Power
- J1 (12V) supplies relay bank and fan driver
- J2 (5V) supplies MCU, logic, fan PWM, analog
- All ICs: Vdd to 5V, Vss to GND, decouple with 100nF at each

## 2. Band Decoder & LPF relays
- MCU port pins RA4/RA6/RA7 → 74HC4514 A0/A1/A2; tie 74HC4514 A3 low
- 74HC4514 Y0–Y6 → ULN2803A IN1-IN7
- ULN2803A OUT1–OUT7 → one side of relay K1–K7
- K1–K7 other side → +12V
- 1N4007 (D1–D7) across each relay coil (anode: ULN, cathode: +12V)

## 3. RF & Analog Sensing
- Bridge SMA FWD1, REF1, etc. outputs → PIC ADC pins (RA0–RA3, RB1–RB3, etc.)
- Divider/filter resistors/caps as needed per architecture

## 4. Overcurrent/Comparator Fault
- Sensor output → analog comparator input → MCU digital input (fault)
- Comparator reset (output from MCU) → comparator reset input

## 5. Temperature/Fan
- NTC divider output → MCU analog input
- MCU PWM output (e.g. RB5) → NMOS (Q1) gate
- Fan − (GND) to NMOS drain, Fan + to +12V

## 6. LCD & UI
- MCU I2C SCL/SDA (RC3/RC4) → J3 pins for I2C LCD
- EC11 encoder A/B/SW → digital inputs (RC2, RB0, RB6)

## 7. Misc/Control/Status Outputs
- MCU output pins to TX, BIAS, relay enable, etc. as per `project-architecture.md`
- All unused inputs pulled or tied safe

---

Consult the architecture and pin map docs for final pin assignments and layout.
