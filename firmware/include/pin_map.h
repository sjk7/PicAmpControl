#ifndef PIN_MAP_H
#define PIN_MAP_H

#include <xc.h>

#define _XTAL_FREQ 32000000UL
#define LCD_I2C_ADDRESS 0x27

// LCD backpack on the software-I2C bus; settings persist in the PIC's internal EEPROM.
#define OUTPUT_LCD_I2C_SCL PORTCbits.RC3
#define OUTPUT_LCD_I2C_SDA PORTCbits.RC4

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
#define OUTPUT_FILTER_BAND_0 PORTAbits.RA4
#define OUTPUT_FILTER_BAND_1 PORTAbits.RA6
// RA7 reserved for Timer1 external clock (frequency counter); 2-bit band selector (4 bands)
#define INPUT_FREQ_COUNTER_TIMER1 PORTAbits.RA7
#define INPUT_ENCODER_SWITCH PORTBbits.RB6
#define OUTPUT_TRIP_STATUS PORTBbits.RB7

#endif

