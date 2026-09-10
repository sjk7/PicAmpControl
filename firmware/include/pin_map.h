#ifndef PIN_MAP_H
#define PIN_MAP_H

#include <xc.h>

#define _XTAL_FREQ 20000000UL
#define LCD_I2C_ADDRESS 0x27
#define AT24C256_I2C_WRITE_ADDRESS 0xA0
#define AT24C256_I2C_READ_ADDRESS 0xA1

// LCD backpack and AT24C256 EEPROM on the software-I2C bus.
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
#define ADC_TEMP_CHANNEL 4
#define ADC_OVERDRIVE_CHANNEL 7
#define ADC_DRAIN_PEAK_CHANNEL 8

// Menu controls, comparator inputs, and status lines
#define INPUT_MENU_INCREASE PORTBbits.RB0
#define INPUT_MENU_DECREASE PORTBbits.RB1
#define INPUT_HARD_FAULT PORTBbits.RB4
#define OUTPUT_FAN_PWM PORTBbits.RB5
#define OUTPUT_WARNING_STATUS PORTBbits.RB6
#define OUTPUT_TRIP_STATUS PORTBbits.RB7

#endif
