#ifndef PIN_MAP_H
#define PIN_MAP_H

#include <xc.h>

#define _XTAL_FREQ 32000000UL

// Parallel LCD in 4-bit mode on freed pins (RB2/RB3 are ADC_OVERDRIVE/ADC_DRAIN_PEAK, not free)
#define OUTPUT_LCD_RS PORTAbits.RA4
#define OUTPUT_LCD_E PORTAbits.RA6
#define OUTPUT_LCD_D4 PORTAbits.RA7
#define OUTPUT_LCD_D5 PORTCbits.RC3
#define OUTPUT_LCD_D6 PORTCbits.RC4
#define OUTPUT_LCD_D7 PORTDbits.RD0

// TX sequencing outputs; all are active-low by default.
#define OUTPUT_TX PORTCbits.RC5
#define OUTPUT_TX_VCC PORTCbits.RC6
#define OUTPUT_TX_BIAS PORTCbits.RC7

// Control inputs
#define INPUT_PTT PORTCbits.RC0
#define INPUT_ENCODER_A PORTCbits.RC2

// Comparator latch reset output.
#define OUTPUT_COMP_RESET PORTCbits.RC1

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
#define OUTPUT_FAN_PWM PORTBbits.RB5
// RA4, RA6, RA7 are now free for future use (previously used for filter band selection)
#define INPUT_ENCODER_SWITCH PORTBbits.RB6
#define OUTPUT_TRIP_STATUS PORTBbits.RB7

#endif

