#ifndef PIN_MAP_H
#define PIN_MAP_H

#include <xc.h>

#define _XTAL_FREQ 20000000UL

// LCD I2C backpack on PIC hardware I2C
#define LCD_I2C_SCL PORTCbits.RC3
#define LCD_I2C_SDA PORTCbits.RC4

// Protection outputs
#define AMP_ENABLE PORTCbits.RC5
#define WARNING_OUT PORTCbits.RC6
#define TRIP_OUT PORTCbits.RC7

// Control inputs
#define MODE_SWITCH PORTCbits.RC0
#define FAULT_ACK PORTCbits.RC1
#define PTT_IN PORTCbits.RC2

// ADC inputs
#define FWD_ADC_CHANNEL 0
#define REF_ADC_CHANNEL 1
#define TEMP_ADC_CHANNEL 3
#define DIAG_ADC_CHANNEL 4

// Comparator inputs and status lines (assigned to RBx as needed)
#define COMP_SWR_1 PORTBbits.RB0
#define COMP_SWR_2 PORTBbits.RB1
#define COMP_OVERDRIVE PORTBbits.RB2
#define COMP_DRAIN_PEAK PORTBbits.RB3
#define COMP_OVERCURRENT PORTBbits.RB4
#define FAN_PWM PORTBbits.RB5

#endif
