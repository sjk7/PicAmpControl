# Schematic Section Breakdown – Linear Amplifier Protection Board

## 1. Power Supplies & Layout
- +12V_IN (J1), +5V_IN (J2)
- Decoupling caps (C1–C3)
- GND blocks

## 2. MCU & Digital Logic
- PIC16F18875 (U1)
  - MCLR pull-up (R1)
  - All analog sense, digital out, LCD, I2C, and EC11 encoder wiring

## 3. Band Decoder System
- 74HC4514 (U2) and all input/output wiring
- ULN2803A (U3) and relay drivers
- LPF relays (K1–K7), flyback diodes (D1–D7)

## 4. Analog & RF Measurement
- Forward/reflected bridges to ADC (FWD1/REF1)
- Divider/filter networks (R series, Cx as needed)

## 5. Protection & Fault Sensing
- Comparator inputs/outputs
- Overcurrent sense circuit, reset path, digital trip

## 6. Thermal & Fan Section
- NTC divider (RN1)
- Fan output NMOS (Q1), fan connector, +12V

## 7. User Interface
- LCD I2C output (J3)
- PCF8574 backpack wiring
- EC11 encoder A/B/push wiring

---

*Capture each block as a visible and logically grouped area. Label all nets and annotate references. DRC at each major step.*
