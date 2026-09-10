#include <xc.h>

// --- Verified Pragma Configuration Settings for PIC16F723A ---
#pragma config FOSC = HS        // High Speed Crystal (20MHz)
#pragma config WDTE = OFF       // Watchdog Timer Disabled
#pragma config PWRTE = OFF      // Power-up Timer Disabled
#pragma config MCLRE = ON       // RE3/MCLR pin function is Reset
#pragma config CP = OFF         // Code Protection Disabled
#pragma config BOREN = ON       // Brown-out Reset Enabled
#pragma config BORV = 19        // Brown-out Reset Voltage set to 1.9V
#pragma config PLLEN = OFF      // Phase Locked Loop Disabled

#define _XTAL_FREQ 20000000     // 20MHz Crystal on Pins 9 & 10

// --- 1602 LCD Pin Mappings ---
#define LCD_RS PORTCbits.RC5    // Pin 16 of PIC -> Pin 4 of Display (RS)
#define LCD_RW PORTCbits.RC6    // Pin 17 of PIC -> Pin 5 of Display (R/W)
#define LCD_EN PORTCbits.RC7    // Pin 18 of PIC -> Pin 6 of Display (E)
#define LCD_DATA PORTB          // Port B maps directly to Display Data D0-D7

// --- Safe Alarm Output Pin Mappings ---
#define ALARM_2_1 PORTCbits.RC3 // Pin 14 of PIC (Goes high at 2.00 SWR)
#define ALARM_3_1 PORTCbits.RC4 // Pin 15 of PIC (Goes high at 3.00 SWR)

// --- Mode Switch Input Pins ---
#define NET_SWITCH PORTCbits.RC0 // Pin 11 of PIC (High = Net, Low = Fwd)
#define REALTIME_SWITCH PORTCbits.RC1 // Pin 12 of PIC (High = Real-Time, Low = PEP)

// --- 8-Bit 1602 LCD Driver Functions ---
void Lcd_ToggleEnable(void) {
    LCD_EN = 1;
    __delay_us(2);
    LCD_EN = 0;
    __delay_us(50);
}

void Lcd_Cmd(unsigned char cmd) {
    LCD_RS = 0; LCD_RW = 0; LCD_DATA = cmd;
    Lcd_ToggleEnable();
    if (cmd == 0x01 || cmd == 0x02) __delay_ms(2); 
}

void Lcd_Char(char data) {
    LCD_RS = 1; LCD_RW = 0; LCD_DATA = data;
    Lcd_ToggleEnable();
}

void Lcd_Init(void) {
    TRISCbits.TRISC5 = 0; TRISCbits.TRISC6 = 0; TRISCbits.TRISC7 = 0; TRISB = 0x00; 
    LCD_RS = 0; LCD_RW = 0; LCD_EN = 0; LCD_DATA = 0x00;
    __delay_ms(20);     
    Lcd_Cmd(0x38); Lcd_Cmd(0x0C); Lcd_Cmd(0x06); Lcd_Cmd(0x01);
}

void Lcd_Print(const char *str) {
    while (*str) { Lcd_Char(*str++); }
}

int Lcd_PrintNumber(unsigned long num) {
    char buf[11]; 
    int i = 0; int chars_printed = 0;
    if (num == 0) { Lcd_Char('0'); return 1; }
    while (num > 0) { buf[i++] = (char)((num % 10) + '0'); num /= 10; }
    chars_printed = i;
    while (i > 0) { Lcd_Char(buf[--i]); }
    return chars_printed;
}

// --- Analog-to-Digital Converter (ADC) ---
void ADC_Init(void) {
    FVRCON = 0x00; ANSELA = 0x0B; ADCON1 = 0x22; ADCON0 = 0x01; 
}

unsigned int ADC_Read(unsigned char channel) {
    ADCON0 &= 0x03; ADCON0 |= (unsigned char)(channel << 2); 
    __delay_us(20);             
    ADCON0bits.GO_DONE = 1;     
    while (ADCON0bits.GO_DONE); 
    return (unsigned int)ADRES; 
}

// --- Main Program ---
void main(void) {
    unsigned int raw_ref = 0; unsigned int raw_fwd = 0;
    unsigned long fwd_sq = 0; unsigned long ref_sq = 0;
    unsigned long fwd_watts = 0; unsigned long ref_watts = 0;
    unsigned long unsigned_active_watts = 0; unsigned long display_watts = 0;  
    unsigned long swr_scaled = 100; unsigned int swr_whole = 1; unsigned int swr_decimal = 0;
    
    unsigned int alarm_2_1_timer = 0; unsigned int alarm_3_1_timer = 0;
    unsigned int pep_hold_timer = 0; unsigned long pep_peak_value = 0;
    
    // Professional Timing Counters
    unsigned int display_refresh_counter = 0;
    unsigned int peak_decay_counter = 0;
    int used_spaces = 0; int rem_spaces = 0;
    
    TRISAbits.TRISA0 = 1; TRISAbits.TRISA1 = 1; TRISAbits.TRISA3 = 1;
    TRISCbits.TRISC0 = 1; TRISCbits.TRISC1 = 1; TRISCbits.TRISC3 = 0; TRISCbits.TRISC4 = 0;
    ALARM_2_1 = 0; ALARM_3_1 = 0;
    
    ADC_Init(); Lcd_Init(); 
    
    while(1) {
        // High-Speed Sample Block (Runs every 5ms)
        raw_ref = ADC_Read(0); 
        raw_fwd = ADC_Read(1); 

        // --- 1. Base 8-Bit Power Calculations ---
        fwd_sq = (unsigned long)raw_fwd * raw_fwd;
        fwd_watts = (fwd_sq * 38446UL) / 1000000UL;
        ref_sq = (unsigned long)raw_ref * raw_ref;
        ref_watts = (ref_sq * 38446UL) / 1000000UL;

        if (NET_SWITCH == 1) {
            unsigned_active_watts = (fwd_watts > ref_watts) ? (fwd_watts - ref_watts) : 0;
        } else {
            unsigned_active_watts = fwd_watts;
        }

        // --- 2. Ultra-Fast Peak Tracking ---
        if (unsigned_active_watts >= pep_peak_value) {
            pep_peak_value = unsigned_active_watts;
            pep_hold_timer = 200; // 200 loops * 5ms = 1.0 second hold time
        }

        // --- 3. SWR Calculation & Immediate Alarm Safety Interlocks ---
        if (raw_fwd >= 5) { 
            if (raw_fwd > (raw_ref + 2)) {
                swr_scaled = (100UL * (raw_fwd + raw_ref)) / (raw_fwd - raw_ref);
                if (swr_scaled > 999) swr_scaled = 999; 
            } else { swr_scaled = 999; }
            
            // Critical Alarms fire instantly (within 5ms) to protect the amp!
            if (swr_scaled >= 300) { ALARM_3_1 = 1; alarm_3_1_timer = 600; } // 3 second latch
            if (swr_scaled >= 200) { ALARM_2_1 = 1; alarm_2_1_timer = 600; }
        } else {
            swr_scaled = 100; 
        }

        // --- 4. Throttled Background Timers (Every 5ms) ---
        if (pep_hold_timer > 0) {
            pep_hold_timer--;
        } else {
            // Decay ticks every 15ms (3 loops) for a silky-smooth analog-style glide down
            peak_decay_counter++;
            if (peak_decay_counter >= 3) {
                peak_decay_counter = 0;
                if (pep_peak_value > unsigned_active_watts) {
                    unsigned long decay_step = (pep_peak_value - unsigned_active_watts) >> 3; // Smooth 12% drop steps
                    if (decay_step == 0) decay_step = 1;
                    pep_peak_value -= decay_step;
                } else { pep_peak_value = unsigned_active_watts; }
            }
        }

        // Handle Alarm Output Latch Decay Timers
        if (raw_fwd < 5) {
            if (alarm_3_1_timer > 0) alarm_3_1_timer--; else ALARM_3_1 = 0;
            if (alarm_2_1_timer > 0) alarm_2_1_timer--; else ALARM_2_1 = 0;
        } else {
            if (alarm_3_1_timer > 0) alarm_3_1_timer--; else if (swr_scaled < 300) ALARM_3_1 = 0;
            if (alarm_2_1_timer > 0) alarm_2_1_timer--; else if (swr_scaled < 200) ALARM_2_1 = 0;
        }

        // Select what the display var tracks based on mode switch
        display_watts = (REALTIME_SWITCH == 0) ? pep_peak_value : unsigned_active_watts;

        // --- 5. Throttled LCD Screen Render Engine (Every 75ms / 15 loops) ---
        display_refresh_counter++;
        if (display_refresh_counter >= 15) {
            display_refresh_counter = 0;
            
            swr_whole = (unsigned int)(swr_scaled / 100UL);
            swr_decimal = (unsigned int)(swr_scaled % 100UL);

            Lcd_Cmd(0x80); // Line 1
            if (raw_fwd >= 5 || display_watts > 0) {
                used_spaces = Lcd_PrintNumber(display_watts);
                if (REALTIME_SWITCH == 0) { Lcd_Print("W PEP"); used_spaces += 5; } 
                else { Lcd_Print("W"); used_spaces += 1; }
                rem_spaces = 16 - used_spaces;
                while (rem_spaces-- > 0) { Lcd_Char(' '); }
            } else { Lcd_Print("0W              "); }
            
            Lcd_Cmd(0xC0); // Line 2
            if (raw_fwd >= 5) {
                Lcd_Print("SWR: "); used_spaces = 5;
                used_spaces += Lcd_PrintNumber((unsigned long)swr_whole);
                Lcd_Char('.'); used_spaces += 1;
                if (swr_decimal < 10) { Lcd_Char('0'); used_spaces += 1; }
                used_spaces += Lcd_PrintNumber((unsigned long)swr_decimal);
                rem_spaces = 16 - used_spaces;
                while (rem_spaces-- > 0) { Lcd_Char(' '); }
            } else { Lcd_Print("SWR: --.-       "); }
        }

        __delay_ms(5); // Ultra-short non-blocking core baseline loop heartbeat
    }
}
