#ifndef PIN_MAP_H
#define PIN_MAP_H

#include <xc.h>

#define _XTAL_FREQ 20000000UL

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

// ADC inputs
#define FWD_ADC_CHANNEL 0
#define REF_ADC_CHANNEL 1
#define TEMP_ADC_CHANNEL 3
#define DIAG_ADC_CHANNEL 4

// Comparator inputs and status lines (assigned to RBx as needed)
#define INPUT_SPARE_1 PORTBbits.RB0
#define INPUT_SPARE_2 PORTBbits.RB1
#define INPUT_COMP_SWR_1 INPUT_SPARE_1
#define INPUT_COMP_SWR_2 INPUT_SPARE_2
#define INPUT_COMP_OVERDRIVE PORTBbits.RB2
#define INPUT_COMP_DRAIN_PEAK PORTBbits.RB3
#define INPUT_COMP_OVERCURRENT PORTBbits.RB4
#define OUTPUT_FAN_PWM PORTBbits.RB5
#define OUTPUT_WARNING_STATUS PORTBbits.RB6
#define OUTPUT_TRIP_STATUS PORTBbits.RB7

#endif
