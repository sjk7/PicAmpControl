# Block Diagram – Linear Amplifier Protection Board

```
     +12V_IN  +5V_IN
        |        |
        |        |
      [Fan]    [MCU - PIC16F18875]
        |        |      | \      | \
   [NMOS]   ADC1..8  |  LCD  EC11 encoder
        |        |      |   |
     [LPF Relay Bank]---|---|
        ^        |     Band decoder logic
        |        |
   [ULN2803A] <--|--- [74HC4514]
                           ^
                           |
                    [Band select outputs]

    [RF Forward/Reflected Detectors] => [ADC Inputs]
    [Current/Cmp Divider] => [Comparator => MCU Pin]
    [NTC Divider] => [ADC Input]
    [LCD backpack (PCF8574 I2C)] <==> [MCU I2C]
```

- All peripherals, comparators, the EC11 encoder, and fans connect to the MCU for measurement/control.
- Band select bus (B0-B2) from the MCU routes through decoder and driver to seven relays, each with a flyback diode and +12V supply; decoder B3/A3 is tied low.
