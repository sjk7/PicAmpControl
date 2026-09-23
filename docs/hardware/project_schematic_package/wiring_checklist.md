# Wiring Checklist – Schematic Capture

Follow this list (left to right/top to bottom) during schematic assembly. Place, wire, and annotate as each item is completed.

1. **Add power connectors:** Place J1 (+12V) and J2 (+5V)
2. **Place PIC18F47Q10 (U1) and decoupling cap (C1) nearby**
   - Wire Vdd to +5V, Vss to GND, add C1 100nF across Vdd/Vss
   - Place R1 10k from MCLR to +5V
3. **ADC and analog inputs:** Wire RF bridges, NTC, overcurrent/current-sense dividers to the ADC pins shown in the pin map; wire the RF band snoop to the Timer1 T1CKI input (no pull-up)
4. **Place and connect ULN2803A (U2) with C2 decoupling**
   - Band-select outputs to ULN2803A IN1–IN6 (one pin per band, active-high)
   - ULN OUT1–OUT6 to K1–K6 relay coils, other side of each relay to +12V
   - Place D1–D6 flyback diodes across each coil
   - There is no 74HC4514 decoder and no B0–B2 address bus
5. **Fan and thermal:** NTC to PIC ADC; NMOS (Q1) and fan, GND return
6. **LCD and rotary UI:** J3 for the parallel 1602 LCD (RS/E/D4–D7; no I2C backpack); EC11 A/B/SW lines to the encoder inputs
7. **All outputs/controls:** Connect TX, BIAS, enable, status, trip lines
8. **Label all power and analog nets**
9. **Double-check all power/gnd connections**
10. **Review with DRC and project-architecture.md pin maps**

---

Check off as you go. This ensures nothing gets skipped during data entry or symbol placement.
