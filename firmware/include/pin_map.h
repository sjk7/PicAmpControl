#ifndef PIN_MAP_H
#define PIN_MAP_H

#include <xc.h>

#define _XTAL_FREQ 20000000UL
#define LCD_I2C_ADDRESS 0x27

// LCD I2C backpack on PIC hardware I2C
#define OUTPUT_LCD_I2C_SCL PORTCbits.RC3
#define OUTPUT_LCD_I2C_SDA PORTCbits.RC4

// TX sequencing outputs; all are active-low by default.
#define OUTPUT_TX PORTCbits.RC5
#define OUTPUT_TX_VCC PORTCbits.RC6
#define OUTPUT_TX_BIAS PORTCbits.RC7

// Control inputs
#define INPUT_PTT PORTCbits.RC0
#define INPUT_FAULT_ACK PORTCbits.RC1
#define INPUT_MENU_NEXT PORTCbits.RC2

// Dedicated ADC inputs; no external analog multiplexer is required.
#define ADC_SWR1_FWD_CHANNEL 0
#define ADC_SWR1_REF_CHANNEL 1
#define ADC_SWR2_FWD_CHANNEL 2
#define ADC_SWR2_REF_CHANNEL 3
#define ADC_TEMP_CHANNEL 4

// Menu controls, comparator inputs, and status lines
#define INPUT_MENU_INCREASE PORTBbits.RB0
#define INPUT_MENU_DECREASE PORTBbits.RB1
#define INPUT_COMP_OVERDRIVE PORTBbits.RB2
#define INPUT_COMP_DRAIN_PEAK PORTBbits.RB3
#define INPUT_COMP_OVERCURRENT PORTBbits.RB4
#define OUTPUT_FAN_PWM PORTBbits.RB5
#define OUTPUT_WARNING_STATUS PORTBbits.RB6
#define OUTPUT_TRIP_STATUS PORTBbits.RB7

#endif
