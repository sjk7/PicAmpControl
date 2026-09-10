#include "../include/pin_map.h"

void Lcd_ToggleEnable(void) {
    LCD_EN = 1;
    __delay_us(2);
    LCD_EN = 0;
    __delay_us(50);
}

void Lcd_Cmd(unsigned char cmd) {
    LCD_RS = 0;
    LCD_RW = 0;
    LCD_DATA = cmd;
    Lcd_ToggleEnable();

    if (cmd == 0x01 || cmd == 0x02) {
        __delay_ms(2);
    }
}

void Lcd_Char(char data) {
    LCD_RS = 1;
    LCD_RW = 0;
    LCD_DATA = data;
    Lcd_ToggleEnable();
}

void Lcd_Init(void) {
    TRISCbits.TRISC5 = 0;
    TRISCbits.TRISC6 = 0;
    TRISCbits.TRISC7 = 0;
    TRISB = 0x00;

    LCD_RS = 0;
    LCD_RW = 0;
    LCD_EN = 0;
    LCD_DATA = 0x00;

    __delay_ms(20);

    Lcd_Cmd(0x38);
    Lcd_Cmd(0x0C);
    Lcd_Cmd(0x06);
    Lcd_Cmd(0x01);
}

void ADC_Init(void) {
    FVRCON = 0x00;
    ANSELA = 0x0B;
    ADCON1 = 0x22;
    ADCON0 = 0x01;
}

unsigned int ADC_Read(unsigned char channel) {
    ADCON0 &= 0x03;
    ADCON0 |= (unsigned char)(channel << 2);
    __delay_us(20);
    ADCON0bits.GO_DONE = 1;
    while (ADCON0bits.GO_DONE) {
        ;
    }
    return (unsigned int)ADRES;
}

void main(void) {
    TRISAbits.TRISA0 = 1;
    TRISAbits.TRISA1 = 1;
    TRISAbits.TRISA3 = 1;
    TRISCbits.TRISC0 = 1;
    TRISCbits.TRISC1 = 1;
    TRISCbits.TRISC3 = 0;
    TRISCbits.TRISC4 = 0;

    ALARM_2_1 = 0;
    ALARM_3_1 = 0;

    ADC_Init();
    Lcd_Init();

    while (1) {
        // Placeholder for amplifier protection logic.
        // The hardware mapping remains centralized in pin_map.h.
        __delay_ms(10);
    }
}
