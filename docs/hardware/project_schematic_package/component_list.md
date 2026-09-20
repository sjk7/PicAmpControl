# Component List – Amplifier Protection Board

| RefDes  | Value         | Description/GUIDE        | Notes                                  |
|---------|---------------|--------------------------|----------------------------------------|
| U1      | PIC16F18875   | MCU_Microchip_PIC        | Main firmware controller               |
| U2      | 74HC4514      | 74xx:74HC4514            | Band decoder, 4-to-16                  |
| U3      | ULN2803A      | Interface_ULN:ULN2803A   | Relay driver / high-current outputs    |
| K1–K7   | RELAY         | Relay_SPST                | LPF relays (160,80,40,20,15,10,6m)     |
| D1–D7   | 1N4007        | Diode                     | Flyback on relays                      |
| R1      | 10k           | Resistor                  | Pull-up, MCLR                          |
| R2–R15  | Various       | Resistor                  | Analog dividers, NTC, etc.             |
| C1–C3   | 100nF         | Capacitor                 | Decoupling (each IC)                   |
| C4–Cx   | Various       | Capacitor                 | Filtering for analog/ADC, Vcc, etc.    |
| J1      | Header        | Conn_01x02 (+12V)         | Relay power                            |
| J2      | Header        | Conn_01x02 (+5V)          | Logic power                            |
| J3      | Header/I2C    | Conn_01x04                | LCD I2C backpack                       |
| Q1      | MOSFET        | NMOS, TO-220              | Fan control driver                     |
| RN1     | NTC           | 10k NTC                   | Temperature sensor                     |
| FWD1/REF1 | SMA         | SMA socket                | Forward/reflected bridge connectors    |
| SW1     | EC11 encoder  | 5-pin rotary + push       | Single front-panel UI control          |

*Add additional references per actual schematic as needed (SWR bridges, comparators, etc.)*
