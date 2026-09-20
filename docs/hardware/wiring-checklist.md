# PIC16F18875-I/P Wiring Checklist – Pin-by-Pin Build Guide

**Device:** Microchip PIC16F18875-I/P, PDIP-40  
**Oscillator:** 32 MHz HFINTOSC (internal, no external clock required)  
**Voltage:** 3.3V supply recommended (or 5V with appropriate I/O tolerancing)

---

## Pin-by-Pin Wiring Instructions

**Legend:**
- **✓ PULLUP/PULLDOWN** = Required resistor to VDD or GND
- **—** = Not required
- **NC** = No connection
- **Voltage** = Supply and signal levels for each pin
- **Component** = Any filtering, protection, or discrete logic

---

### **VDD/VSS Power Distribution**

| Pin | Signal | Type | Voltage | Pullup | Notes |
|-----|--------|------|---------|--------|-------|
| 1 | **VSS (GND)** | Power | 0V | — | Ground plane; connect directly to GND rail. **Large star point for all return currents.** |
| 10 | **VDD** | Power | 3.3V | — | Main supply; 100nF ceramic cap to GND at pad. Place close to pin. |
| 19 | **VSS (GND)** | Power | 0V | — | Ground plane; second ground pin for current distribution. |
| 20 | **VDD** | Power | 3.3V | — | Second supply pin; 100nF ceramic cap to GND. |
| 38 | **VREF+** | Power | 3.3V | — | ADC reference; 1µF ceramic + 100nF ceramic to GND (RC filter). |

---

### **Port A – ADC Inputs & LCD Parallel Control**

| Pin | Signal | Mode | Voltage | Pullup | Component | Notes |
|-----|--------|------|---------|--------|-----------|-------|
| 2 | RA0 / ADC_SWR1_FWD | Analog In | 0–5V | — | 100nF cap to GND | SWR1 forward power sensor; AC-coupled preamp output. No pullup. |
| 3 | RA1 / ADC_SWR1_REF | Analog In | 0–5V | — | 100nF cap to GND | SWR1 reflected power sensor; AC-coupled preamp output. No pullup. |
| 4 | RA2 / ADC_SWR2_FWD | Analog In | 0–5V | — | 100nF cap to GND | SWR2 forward power sensor; AC-coupled preamp output. No pullup. |
| 5 | RA3 / ADC_SWR2_REF | Analog In | 0–5V | — | 100nF cap to GND | SWR2 reflected power sensor; AC-coupled preamp output. No pullup. |
| 6 | RA4 / LCD_RS | GPIO Out | 0–3.3V | — | Direct to LCD module | LCD Register Select. No pullup required (open-drain not needed). |
| 7 | RA5 / ADC_TEMP | Analog In | 0–5V | — | 100nF cap to GND | Thermistor preamp output; no pullup. |
| 8 | RA6 / LCD_E | GPIO Out | 0–3.3V | — | Direct to LCD module | LCD Enable strobe. No pullup required. |
| 9 | RA7 / LCD_D4 | GPIO Out | 0–3.3V | — | Direct to LCD module | LCD D4 (LSB of 4-bit data). No pullup required. |

---

### **Port B – Encoder Inputs, Comparator Fault, Fan PWM, Status Output**

| Pin | Signal | Mode | Voltage | Pullup | Component | Notes |
|-----|--------|------|---------|--------|-----------|-------|
| 21 | RB0 / INPUT_ENCODER_B | GPIO In | 0–3.3V | ✓ **10kΩ to VDD** | Direct from encoder | Rotary encoder quadrature phase B; pulls high at rest. |
| 22 | RB1 / ADC_CURRENT | Analog In | 0–5V | — | 100nF cap to GND | Drain/collector current sense amp output; no pullup. |
| 23 | RB2 | NC | — | — | **Leave floating or NC** | Reserved for future use; do not connect. |
| 24 | RB3 | NC | — | — | **Leave floating or NC** | Reserved for future use; do not connect. |
| 25 | RB4 / INPUT_OVERCURRENT_FAULT | GPIO In | 0–3.3V | — | Direct from comparator | Comparator latch output (active-low fault); internal pullup enabled in firmware. **No external pullup.** |
| 26 | RB5 / OUTPUT_FAN_PWM | GPIO Out | 0–3.3V | — | FET driver + fan relay | PWM output to fan motor control; drives FET gate. **Gate should be pulled low via 10kΩ to GND at driver.** |
| 27 | RB6 / INPUT_ENCODER_SWITCH | GPIO In | 0–3.3V | ✓ **10kΩ to VDD** | Direct from encoder push-button | Encoder center switch; debounced in firmware. Pulls high at rest. |
| 28 | RB7 / OUTPUT_TRIP_STATUS | GPIO Out | 0–3.3V | — | LED + 470Ω series R | Trip indicator output (active-low, ~20mA sink); drives LED to ground via resistor. |

---

### **Port C – PTT Input, Comparator Reset, Encoder A, LCD Parallel Data, TX Control Outputs**

| Pin | Signal | Mode | Voltage | Pullup | Component | Notes |
|-----|--------|------|---------|--------|-----------|-------|
| 11 | RC0 / INPUT_PTT | GPIO In | 0–3.3V | ✓ **10kΩ to VDD** | Direct from PTT switch | Push-to-talk input; pulled high at rest. Normally high, goes low on PTT. |
| 12 | RC1 / OUTPUT_COMP_RESET | GPIO Out | 0–3.3V | — | Direct to comparator | Comparator latch reset pulse (active-high, 1–2 µs); drives CMP1 reset pin. **No pullup.** |
| 13 | RC2 / INPUT_ENCODER_A | GPIO In | 0–3.3V | ✓ **10kΩ to VDD** | Direct from encoder | Rotary encoder quadrature phase A; pulls high at rest. |
| 14 | RC3 / LCD_D5 | GPIO Out | 0–3.3V | — | Direct to LCD module | LCD D5 (data bit 1 of 4-bit mode). No pullup required. |
| 15 | RC4 / LCD_D6 | GPIO Out | 0–3.3V | — | Direct to LCD module | LCD D6 (data bit 2 of 4-bit mode). No pullup required. |
| 16 | RC5 / OUTPUT_TX | GPIO Out | 0–3.3V | — | Relay/FET driver | TX enable output (active-low); drives relay coil or FET gate. **Gate should be pulled low via 10kΩ to GND.** |
| 17 | RC6 / OUTPUT_TX_VCC | GPIO Out | 0–3.3V | — | Relay/FET driver | TX VCC enable (active-low, ~100mA sink); drives amplifier supply relay. **Gate pulled low via 10kΩ.** |
| 18 | RC7 / OUTPUT_TX_BIAS | GPIO Out | 0–3.3V | — | Relay/FET driver | TX bias enable (active-low); controls amplifier idle condition. **Gate pulled low via 10kΩ.** |

---

### **Port D – LCD Parallel & Spare**

| Pin | Signal | Mode | Voltage | Pullup | Component | Notes |
|-----|--------|------|---------|--------|-----------|-------|
| 29 | RD0 / LCD_D7 | GPIO Out | 0–3.3V | — | Direct to LCD module | LCD D7 (data bit 3 of 4-bit mode). No pullup required. |
| 30 | RD1 | NC | — | — | **Leave floating or NC** | Reserved for future expansion; do not connect. |
| 31 | RD2 | NC | — | — | **Leave floating or NC** | Reserved for future expansion; do not connect. |
| 32 | RD3 | NC | — | — | **Leave floating or NC** | Reserved for future expansion; do not connect. |
| 33 | RD4 | NC | — | — | **Leave floating or NC** | Reserved for future expansion; do not connect. |
| 34 | RD5 | NC | — | — | **Leave floating or NC** | Reserved for future expansion; do not connect. |
| 35 | RD6 | NC | — | — | **Leave floating or NC** | Reserved for future expansion; do not connect. |
| 36 | RD7 | NC | — | — | **Leave floating or NC** | Reserved for future expansion; do not connect. |

---

### **Port E – Spare**

| Pin | Signal | Mode | Voltage | Pullup | Component | Notes |
|-----|--------|------|---------|--------|-----------|-------|
| 37 | RE0 | NC | — | — | **Leave floating or NC** | Reserved for future expansion; do not connect. |
| 39 | RE1 | NC | — | — | **Leave floating or NC** | Reserved for future expansion; do not connect. |
| 40 | RE2 | NC | — | — | **Leave floating or NC** | Reserved for future expansion; do not connect. |
| 40 | RE3 | NC | — | — | **Leave floating or NC** | Reserved for future expansion; do not connect. |

---

## Summary: Pullup/Pulldown Requirements

### **Must Have:**
- **RC0 (PTT):** 10kΩ pullup to VDD → active-low logic (normal = high, press = low)
- **RB0 (Encoder B):** 10kΩ pullup to VDD → encoder quadrature
- **RB6 (Encoder Switch):** 10kΩ pullup to VDD → encoder push-button
- **RC2 (Encoder A):** 10kΩ pullup to VDD → encoder quadrature
- **FET Gate Protection:** 10kΩ pulldown to GND on each FET driver (RC5/RC6/RC7 driving MOSFET gates) → pulls gates low when MCU powered off or reset

### **NOT Needed:**
- **ADC inputs (RA0-RA3, RA5, RB1):** No pullup/pulldown; connect directly to sensor preamp outputs
- **LCD pins (RA4, RA6, RA7, RC3, RC4, RD0):** No pullup required; push-pull CMOS outputs
- **RB4 (Comparator Fault):** No external pullup; MCU internal pullup is enabled in firmware
- **RC1 (Comparator Reset):** No pullup required; push-pull output to comparator reset pin

---

## Decoupling & Filtering

**Power Supply Bypass:**
- 100nF ceramic capacitor at each VDD pin (pins 10 & 20) to VSS, placed within 5mm of pins
- 1µF ceramic + 100nF ceramic on VREF+ (pin 38) → 1µF to GND + 100nF in series to GND

**ADC Input Filtering (all analog pins RA0-RA3, RA5, RB1):**
- 100nF ceramic capacitor from each ADC pin to GND, placed at the PIC pad
- No ferrite beads or inductors; keep traces short

**MCLR (Master Clear / Reset):**
- 10kΩ pullup to VDD (standard microcontroller reset circuit)
- Optional: 100nF cap from MCLR to GND for EMI filtering

---

## Connector / Interface Assignments

### **LCD 16×2 Parallel Display (4-bit Mode)**
**6 pins required; standard Hitachi HD44780 16×2 LCD module**

| PIC Pin | LCD Pin | Signal |
|---------|---------|--------|
| RA4 | 4 | RS (Register Select) |
| RA6 | 6 | E (Enable) |
| RA7 | 11 | D4 |
| RC3 | 12 | D5 |
| RC4 | 13 | D6 |
| RD0 | 14 | D7 |
| VDD | 2 | VDD (+3.3V or +5V) |
| VSS | 1, 5, 16 | VSS (GND) |
| VO | 3 | Contrast (10kΩ pot between VDD–VO–GND) |
| A | 15 | Backlight Anode (+5V via 470Ω) |
| K | 16 | Backlight Cathode (GND) |

**No pullup resistors on LCD data lines.** The PIC outputs them as push-pull CMOS.

---

### **Rotary Encoder (with Push-Button)**
**4 pins required; standard optical or mechanical encoder with center switch**

| PIC Pin | Encoder Pin | Signal |
|---------|-------------|--------|
| RB0 | A | Phase B (quadrature) |
| RC2 | B | Phase A (quadrature) |
| RB6 | C/SW | Center switch |
| VDD | + | Supply (+3.3V or +5V) |
| VSS | — | GND |

**Each encoder input (RB0, RC2, RB6) has 10kΩ pullup to VDD in firmware-enabled WPUB/WPUC registers.**

---

### **PTT Input (Manual Switch)**
**1 pin required; momentary push-button or relay contact**

| PIC Pin | Switch | Signal |
|---------|--------|--------|
| RC0 | 1 | PTT input (active-low) |
| RC0 | 2 | GND |

**10kΩ pullup to VDD keeps pin high at rest; pressing switch pulls pin to GND.**

---

### **Relay/FET Outputs (TX Control)**
**3 pins for TX relay control; each drives a MOSFET gate or relay coil**

| PIC Pin | Function | Active Level | Driver Stage |
|---------|----------|--------------|--------------|
| RC5 | TX Enable (RF relay) | Low | FET gate driver |
| RC6 | TX VCC (supply relay) | Low | FET gate driver |
| RC7 | TX Bias (idle bias) | Low | FET gate driver |

**Each output is active-low (~20–100mA sink capability):**
- **For MOSFET:** Gate pulldown 10kΩ to GND; MCU drives gate low to turn ON
- **For relay:** Flyback diode (1N4007) across coil; typical 12V/200mA relay

---

### **Protection & Sensing Inputs**

| PIC Pin | Function | Input Signal | Component |
|---------|----------|--------------|-----------|
| RB4 | Hardware overcurrent trip | Comparator latch output (active-low) | Direct from CMP1 |
| RB1 | Current sense (ADC) | 0–5V from current sense amp | 100nF cap to GND |
| RA5 | Temperature (ADC) | 0–5V from thermistor preamp | 100nF cap to GND |
| RA0, RA1, RA2, RA3 | SWR (fwd/ref) × 2 | 0–5V from directional coupler preamp | 100nF cap to GND each |

---

### **Fan PWM Output**
**1 pin required; drives FET for 12V fan motor control**

| PIC Pin | Function | Signal Level | Driver Stage |
|---------|----------|--------------|--------------|
| RB5 | Fan PWM | 0–3.3V PWM | FET gate (gate pulled low via 10kΩ to GND) |

**Typical circuit:**
- MCU RB5 → 1kΩ series R → MOSFET (N-channel, e.g., 2N7000) gate
- Gate pulldown: 10kΩ to GND
- Drain: +12V
- Source: Fan GND
- Flyback: 1N4007 diode across fan motor (cathode to +12V, anode to GND)

---

### **Trip Status Output**
**1 pin required; LED indicator**

| PIC Pin | Function | Active Level | Component |
|---------|----------|--------------|-----------|
| RB7 | Trip status LED | Low (active-low) | LED + 470Ω series R to GND |

**LED cathode to RB7; LED anode to +3.3V (or through series R to VDD).**

---

## Design Checklist

- [ ] **Power supply:** 3.3V (preferred) or 5V with tolerance resistors on CMOS inputs
- [ ] **Decoupling:** 100nF at both VDD pins, 1µF + 100nF at VREF+
- [ ] **ADC filtering:** 100nF ceramic on all analog input pins (RA0–RA3, RA5, RB1)
- [ ] **Pullups (VDD-connected):** RC0, RB0, RB6, RC2 all have 10kΩ to VDD
- [ ] **Pulldowns (GND-connected):** FET gates (RC5, RC6, RC7 drivers) pulled to GND via 10kΩ
- [ ] **LCD wiring:** 6 pins to 16×2 HD44780 parallel display, no pullups on data lines
- [ ] **Encoder:** Quadrature (RB0/RC2) + push-button (RB6) with pullups enabled
- [ ] **PTT input:** Momentary switch to GND with 10kΩ pullup to VDD
- [ ] **Comparator:** Connect CMP1 output (active-low) to RB4; connect MCLR reset to RC1 pin
- [ ] **TX relays:** 3 FETs (RC5/RC6/RC7) with gate pulldowns and flyback diodes
- [ ] **Fan PWM:** Single FET on RB5; gate pulled low, 12V fan motor with protection diode
- [ ] **Trip LED:** Cathode to RB7, anode to VDD via 470Ω
- [ ] **Unconnected pins:** All Port D (except RD0) and Port E left floating or tied to GND (tie to GND preferred to reduce noise)

---

**Document Version:** 1.0  
**Last Updated:** 2026-09-20  
**Board Target:** PIC16F18875-I/P, 40-pin PDIP, parallel LCD 16×2 display, RF amplifier protection controller
