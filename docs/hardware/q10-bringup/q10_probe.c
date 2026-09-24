/*
 * PIC18F47Q10 bring-up probe (throwaway; not part of the firmware build).
 *
 * Purpose: answer the questions the Q10 port has never actually answered, with measured
 * evidence rather than assumed register values:
 *   1. Does the tick run at the frequency the firmware assumes (PR2/1:64 off the selected
 *      Timer2 clock)? NOTE: this probe predates the move to T2CLK = Fosc/8 in main.c - it still
 *      writes 0x01 (Fosc/4), so its timing confirms the PR2/prescaler chain only, not the clock
 *      source the shipping firmware now uses.
 *   2. Does an interrupt actually dispatch once IPEN + the source priority bit are set?
 *   3. Does T1CKIPPS accept the value the firmware writes (0x19), and is that RD1 on this device?
 *   4. Does the NVM (EEPROM) register sequence complete, i.e. is the Q10 NVM driver plausible?
 *   5. What is the CPU instruction rate, to recalibrate INSTRUCTIONS_PER_MS?
 *
 * Every value written here was read out of PIC18F-Q_DFP/1.30.487's pic18f47q10.h, not assumed:
 *   ADCON0.ADFM, T2CLK bits (T2CLKCON is a bitfield union with no named constant), T1CLKbits.CS,
 *   INTCONbits.IPEN, IPR4bits.TMR2IP, NVMCON1/NVMCON0/NVMCON2.
 */
#include <xc.h>

#pragma config FEXTOSC = OFF
#pragma config RSTOSC = HFINTOSC_1MHZ
#pragma config WDTE = OFF
#pragma config PWRTE = OFF
#pragma config MCLRE = EXTMCLR
#pragma config CP = OFF
#pragma config BOREN = ON
#pragma config BORV = VBOR_190

volatile unsigned int g_tick = 0;         /* Timer2 overflows dispatched into the ISR */
volatile unsigned int g_isr_any = 0;      /* every entry into the ISR */
volatile unsigned int g_tmr1_overflow = 0;
volatile unsigned char g_ptt_seen = 0;    /* latched PTT state as the ISR saw it */
volatile unsigned char g_pps_written = 0; /* T1CKIPPS readback */
volatile unsigned char g_nvm_done = 0;    /* EEPROM write finished */
volatile unsigned char g_nvm_value = 0;   /* EEPROM readback */
volatile unsigned long g_spin = 0;        /* instruction-rate calibration counter */

/* PTT is on RC0 in this design (see firmware/include/pin_map.h). */
#define PTT_PIN PORTCbits.RC0

void __interrupt() isr(void) {
    g_isr_any++;
    if (PIR4bits.TMR2IF) {
        PIR4bits.TMR2IF = 0;
        g_tick++;
    }
    if (PIR4bits.TMR1IF) {
        PIR4bits.TMR1IF = 0;
        g_tmr1_overflow++;
    }
}

void main(void) {
    unsigned char i;

    /* --- PTT on RC0, digital input with pull-up, exactly as main.c configures it --- */
    ANSELCbits.ANSELC0 = 0;
    TRISCbits.TRISC0 = 1;
    WPUCbits.WPUC0 = 1;

    /* --- Timer2: prescaler/PR2 as timer0_init() uses, but T2CLK here is still Fosc/4;
     *     main.c now selects Fosc/8 (T2CLK = 0x02) so the tick lands at 1.000 ms off the
     *     64 MHz core. This probe's Fosc/4 predates that change. --- */
    T2CLK = 0x01;              /* Fosc/4: what the probe was written against, NOT what main.c uses now */
    T2CONbits.CKPS = 6;        /* 1:64 prescale */
    T2CONbits.OUTPS = 0;
    PR2 = 124;                 /* (124+1) * 64 / Fosc = 1.000ms at 8 MHz */
    TMR2 = 0;
    PIR4bits.TMR2IF = 0;
    PIE4bits.TMR2IE = 1;

    /* --- interrupt dispatch: IPEN + source priority, the two things that were missing --- */
    INTCONbits.IPEN = 1;
    IPR4bits.TMR2IP = 1;
    INTCONbits.GIE = 1;

    T2CONbits.ON = 1;

    /* --- PPS: T1CKI from RD1, as freq_counter_init() writes it --- */
    T1CKIPPS = 0x19;
    g_pps_written = T1CKIPPS;

    /* --- Timer1 as the frequency-counter input (async, no clock at this stage) --- */
    T1CLKbits.CS = 0x00;       /* T1CKIPPS */
    T1CONbits.CKPS = 0x02;     /* 1:4 */
    T1CONbits.NOT_SYNC = 1;    /* async */
    T1CONbits.RD16 = 1;
    TMR1 = 0;
    PIR4bits.TMR1IF = 0;
    PIE4bits.TMR1IE = 1;
    T1CONbits.ON = 1;

    /* --- EEPROM: the Q10 NVM sequence (unlock 0x55/0xAA into NVMCON2, then WR) ---
       NOTE: NVMCON1 on this device has NO `WREN` member - its bits are RD, SECRD, WR, SECWR,
       SECER (read from the DFP header, not assumed). The unlock dance was the part the notes
       got right; the bit names were the part they got wrong. */
    NVMADRH = 0x00;
    NVMADRL = 0x00;
    NVMDATL = 0xA5;
    NVMCON2 = 0x55;
    NVMCON2 = 0xAA;
    NVMCON1bits.WR = 1;
    for (i = 0; i < 20; i++) { }        /* write cycle settles */
    NVMADRL = 0x00;
    NVMCON1bits.RD = 1;
    g_nvm_value = NVMDATL;
    g_nvm_done = 1;

    while (1) {
        g_ptt_seen = (PTT_PIN != 0) ? 1 : 0;
        g_spin++;
    }
}
