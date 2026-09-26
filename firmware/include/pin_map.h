#ifndef PIN_MAP_H
#define PIN_MAP_H

#include <xc.h>

/* System oscillator: HFINTOSC at 64 MHz (RSTOSC = HFINTOSC_64MHZ, the core the part actually
   runs). XC8 compiles __delay_us()/__delay_ms() from this, so it must match the real 64 MHz core
   or every delay in the LCD init, the page-clear settle and the ADC acquisition runs at the wrong
   length. There is no 32 MHz internal setting on this part. */
#define _XTAL_FREQ 64000000UL

/* Outputs are written through the LAT register, inputs are read from PORT.
   Writing a PORT bit is a read-modify-write of the whole port latch, so a pin whose
   level disagrees with its latch (a relay driver still slewing, a line held by an
   external load) is written back into another pin's latch by any unrelated write on
   the same port. PORTC alone mixes the T/R and VCC/bias relay lines with the LCD data
   lines, so that is a live hazard here, not a theoretical one.

   Where the firmware must confirm what a pin is ACTUALLY doing before a relay is
   allowed to move, it reads the matching SENSE_* macro instead, which is the PORT read.
   Reading the LAT there would only echo back what the firmware commanded. */

// Parallel LCD in 4-bit mode on freed pins (RB2/RB3 are ADC_OVERDRIVE/ADC_DRAIN_PEAK, not free)
#define OUTPUT_LCD_RS LATAbits.LATA4
#define OUTPUT_LCD_E LATAbits.LATA6
#define OUTPUT_LCD_D4 LATAbits.LATA7
#define OUTPUT_LCD_D5 LATCbits.LATC3
#define OUTPUT_LCD_D6 LATCbits.LATC4
#define OUTPUT_LCD_D7 LATDbits.LATD0

// TX sequencing outputs; all are active-low by default. Written via LAT.
#define OUTPUT_TX LATCbits.LATC5
#define OUTPUT_TX_VCC LATCbits.LATC6
#define OUTPUT_TX_BIAS LATCbits.LATC7

// Pin-level readback of the TX outputs. These are the PORT reads used by the checks
// that must confirm the hardware really has reached a state before a relay may move
// (release_band_if_cold) or before PTT COMPLETE is shown.
#define SENSE_TX PORTCbits.RC5
#define SENSE_TX_VCC PORTCbits.RC6
#define SENSE_TX_BIAS PORTCbits.RC7

// Control inputs
#define INPUT_PTT PORTCbits.RC0
#define INPUT_ENCODER_A PORTCbits.RC2
#define INPUT_FREQ_COUNTER PORTDbits.RD1   // Timer1 frequency counter input (T1CKI via PPS)

// Comparator latch reset output.
#define OUTPUT_COMP_RESET LATCbits.LATC1

// Pin-level readback of the remaining outputs, for the diagnostic self-test's
// assert-and-verify loop. Writes go out via LAT (the OUTPUT_* macros); the confirm
// reads the same pin back through PORT, so a driver that never reached its level is
// caught. No extra pins: each SENSE_* is the PORT read of an already-wired output.
#define SENSE_FAN PORTBbits.RB5
#define SENSE_TRIP PORTBbits.RB7
#define SENSE_BAND_160M PORTDbits.RD2
#define SENSE_BAND_80M  PORTDbits.RD3
#define SENSE_BAND_40M  PORTDbits.RD4
#define SENSE_BAND_20M  PORTDbits.RD5
#define SENSE_BAND_15M  PORTDbits.RD6
#define SENSE_BAND_10M  PORTDbits.RD7

// Dedicated ADC inputs; no external analog multiplexer is required.
#define ADC_SWR1_FWD_CHANNEL 0
#define ADC_SWR1_REF_CHANNEL 1
#define ADC_SWR2_FWD_CHANNEL 2
#define ADC_SWR2_REF_CHANNEL 3
#define ADC_TEMP_CHANNEL 5
#define ADC_CURRENT_CHANNEL 9
#define ADC_OVERDRIVE_CHANNEL 10
#define ADC_DRAIN_PEAK_CHANNEL 11

// Rotary encoder UI, comparator inputs, and status lines
#define INPUT_ENCODER_B PORTBbits.RB0
// RB1 is ADC_CURRENT_CHANNEL (analog input, see above) - not a digital pin.
#define INPUT_OVERCURRENT_FAULT PORTBbits.RB4
#define OUTPUT_FAN_PWM LATBbits.LATB5
#define INPUT_ENCODER_SWITCH PORTBbits.RB6
#define OUTPUT_TRIP_STATUS LATBbits.LATB7

// Band-select (LPF relay) outputs, one dedicated active-high pin per band.
#define OUTPUT_BAND_160M LATDbits.LATD2
#define OUTPUT_BAND_80M  LATDbits.LATD3
#define OUTPUT_BAND_40M  LATDbits.LATD4
#define OUTPUT_BAND_20M  LATDbits.LATD5
#define OUTPUT_BAND_15M  LATDbits.LATD6
#define OUTPUT_BAND_10M  LATDbits.LATD7

#endif

