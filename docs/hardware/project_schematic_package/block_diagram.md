# Block Diagram – Linear Amplifier Protection Board

> **Pin assignments are not restated here.** Single source of truth:
> [../PIC16F18875_pin_map.md](../PIC16F18875_pin_map.md). Component-level nets:
> [connection_table.csv](connection_table.csv).

```
                            +12V_IN          +5V_IN
                               |                |
                            [Fan]               |
                               |                |
                           [NMOS Q1]            |
                               |                |
                               |                |
   +---------------------------+----------------+--------------------------+
   |                          PIC16F18875 (U1)                            |
   +--+------+-------+------+------+------+------+-----------------------+
      |      |       |      |      |      |      |       |
     ADC    ADC     ADC    ADC    ADC   COMP   SNOOP   BAND SELECT
      |      |       |      |      |      |      |       |
      |      |       |      |      |      |      |       +--> [ULN2803A U2]
      |      |       |      |      |      |      |                 |
      |      |       |      |      |      |      |          [LPF relay bank K1-K6]
      |      |       |      |      |      |      |          one active-high output
      |      |       |      |      |      |      |          per band, six bands
      |      |       |      |      |      |      |
      |      |       |      |      |      |      +--> [Band snoop -> Timer1 T1CKI via PPS]
      |      |       |      |      |      +--> [Overcurrent comparator latch (hard fault)]
      |      |       |      |      +--> [Drain peak detector]
      |      |       |      +--> [Overdrive detector]
      |      |       +--> [WCS1700 current sensor]
      |      +--> [NTC divider]
      +--> [SWR1/SWR2 forward + reflected bridges]

   User interface:
     [1602 LCD, 4-bit parallel: RS / E / D4-D7] <==> MCU
     [EC11 encoder A / B / push] --> MCU

   Other MCU outputs: PTT reset pulse, TX / TX_VCC / TX_BIAS sequencing,
   fan PWM, trip status
```

- All peripherals, the comparator latch, the EC11 encoder, and the fan connect to the MCU for measurement/control.
- Band selection is **direct**: one dedicated active-high output per band (six bands, 160–10 m). There is no 74HC4514 decoder and no B0–B2 address bus. Each output drives one ULN2803A channel, which sinks the matching LPF relay coil (K1–K6) with a flyback diode (D1–D6).
- The band-snoop input is the Timer1 external clock (T1CKI via PPS). It carries the RF band-snoop signal used to classify the band and to gate transmit; it is not a switch input and takes no pull-up.
- The band-select outputs are push-pull CMOS outputs driving the relay driver. No pull-ups or pull-downs are required.

## Band selection and lockout

```
  RF snoop (Timer1 T1CKI)
        |
        v
  Timer1 count -> 10 ms tick -> classify band (160/80/40/20/15/10 m)
        |                              |
        |                              +--> candidate_band / current_band
        v
  PTT falls
        |
        +-- live measurement already confirmed? ---> engage on it, lock the band
        |
        +-- no, but a band is remembered? ---------> restore + lock it, engage instantly
        |                                            (then verified against the first
        |                                             measurement of this transmission;
        |                                             a mismatch folds back to bypass and
        |                                             re-engages on the measured band)
        |
        +-- no band known at all ------------------> BYPASS-SNOOP: PTT latched, LDMOS bias
                                                     off, RF straight through to the
                                                     antenna while the radio's first
                                                     burst is decoded
                                                        |
                                                        v
                                                     cache band, lock, wait for the LPF
                                                     relay to settle, then engage
        v
  TX completes -> back to RX/idle -> band unlocked (band kept in the first-dit memory)
                                            |
                                            v
                                     LPF relays free to follow the next snoop
```

Band lockout is what prevents the LPF relays from being re-selected mid-transmission: while the
amplifier is keyed the selection is frozen, and a band change is only ever applied with the
amplifier cold. If nothing decodes a band, the amplifier is not keyed at all - the RF path stays
in bypass (straight through, no LDMOS bias) instead of transmitting through an unverified filter.
See [docs/first-dit-band-detection.md](../../first-dit-band-detection.md) for the full model,
its invariants and its test evidence.
