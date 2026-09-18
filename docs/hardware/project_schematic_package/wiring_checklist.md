# Wiring Checklist – Schematic Capture

Follow this list (left to right/top to bottom) during schematic assembly. Place, wire, and annotate as each item is completed.

1. **Add power connectors:** Place J1 (+12V) and J2 (+5V)
2. **Place PIC16F18855 (U1) and decoupling cap (C1) nearby**
   - Wire Vdd to +5V, Vss to GND, add C1 100nF across Vdd/Vss
   - Place R1 10k from MCLR to +5V
3. **ADC and analog inputs:** Wire RF bridges, NTC, overcurrent/currentsense dividers to ADC/analog pins
4. **Place and connect 74HC4514 (U2) and ULN2803A (U3) (with C2, C3 decoupling)**
   - RA4/RA6/RA7 to decoder A0/A1/A2; tie decoder A3 low
   - Decoder outputs (Y0–Y6) to ULN2803A IN1–IN7
   - ULN OUT1–OUT7 to K1–K7 relay coils, other side of each relay to +12V
   - Place D1–D7 flyback diodes across each coil
5. **Fan and thermal:** NTC to PIC ADC; NMOS (Q1) and fan, GND return
6. **LCD and rotary UI:** J3 for I2C LCD backpack; EC11 A/B/SW lines to RC2/RB0/RB6
7. **All outputs/controls:** Connect TX, BIAS, enable, status, trip lines
8. **Label all power and analog nets**
9. **Double-check all power/gnd connections**
10. **Review with DRC and project-architecture.md pin maps**

---

Check off as you go. This ensures nothing gets skipped during data entry or symbol placement.
