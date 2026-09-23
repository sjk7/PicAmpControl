# Component List – Amplifier Protection Board

| RefDes  | Value         | Description/GUIDE        | Notes                                  |
|---------|---------------|--------------------------|----------------------------------------|
| U1      | PIC18F47Q10   | MCU_Microchip_PIC        | Main firmware controller               |
| U2      | ULN2803A      | Interface_ULN:ULN2803A   | Relay driver / high-current outputs    |
| K1–K6   | RELAY         | Relay_SPST                | LPF relays (160,80,40,20,15,10m)       |
| D1–D6   | 1N4007        | Diode                     | Flyback on relays                      |
| R1      | 10k           | Resistor                  | Pull-up, MCLR                          |
| R2–R15  | Various       | Resistor                  | Analog dividers, NTC, etc.             |
| C1–C2   | 100nF         | Capacitor                 | Decoupling (MCU, relay driver)         |
| C3–Cx   | Various       | Capacitor                 | Filtering for analog/ADC, Vcc, etc.    |
| J1      | Header        | Conn_01x02 (+12V)         | Relay power                            |
| J2      | Header        | Conn_01x02 (+5V)          | Logic power                            |
| J3      | Header        | Conn_01x08                | Parallel 1602 LCD (RS/E/D4-D7/VSS/VDD) |
| Q1      | MOSFET        | NMOS, TO-220              | Fan control driver                     |
| RN1     | NTC           | 10k NTC                   | Temperature sensor                     |
| FWD1/REF1 | SMA         | SMA socket                | Forward/reflected bridge connectors    |
| SW1     | EC11 encoder  | 5-pin rotary + push       | Single front-panel UI control          |

*Add additional references per actual schematic as needed (SWR bridges, comparators, etc.)*

## Notes

- The 74HC4514 band decoder has been **removed**. Band selection is now one dedicated active-high MCU output per band (RD2–RD7), each driving a ULN2803A channel directly. There is no B0–B2 address bus and no 6 m output.
- The LCD is a 1602 driven in 4-bit parallel mode, not an I2C backpack. Confirm the J3 pin count and contrast wiring at capture.
- `RD1` / `INPUT_FREQ_COUNTER` is the Timer1 T1CKI band-snoop input; it takes no pull-up.
