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
#define INPUT_MENU_NEXT PORTCbits.RC2

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

// Menu controls, comparator inputs, and status lines
#define INPUT_MENU_INCREASE PORTBbits.RB0
#define INPUT_MENU_ADJUST INPUT_MENU_INCREASE
#define INPUT_SPARE_1 PORTBbits.RB1
#define INPUT_OVERCURRENT_FAULT PORTBbits.RB4
#define OUTPUT_FAN_PWM PORTBbits.RB5
#define OUTPUT_WARNING_STATUS PORTBbits.RB6
#define OUTPUT_TRIP_STATUS PORTBbits.RB7

#endif
