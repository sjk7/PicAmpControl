#ifndef PIN_MAP_H
#define PIN_MAP_H

#include <xc.h>

#define _XTAL_FREQ 20000000UL

// ADC channels
#define FWD_SENSE_CHANNEL 0
#define REF_SENSE_CHANNEL 1
#define DIAG_CHANNEL 3

// LCD control pins
#define LCD_RS PORTCbits.RC5
#define LCD_RW PORTCbits.RC6
#define LCD_EN PORTCbits.RC7
#define LCD_DATA PORTB

// Alarm outputs
#define ALARM_2_1 PORTCbits.RC3
#define ALARM_3_1 PORTCbits.RC4

// Mode inputs
#define NET_SWITCH PORTCbits.RC0
#define REALTIME_SWITCH PORTCbits.RC1

// ADC analog input aliases
#define FWD_ADC_INPUT PORTAbits.RA0
#define REF_ADC_INPUT PORTAbits.RA1
#define SPARE_ADC_INPUT PORTAbits.RA3

#endif
