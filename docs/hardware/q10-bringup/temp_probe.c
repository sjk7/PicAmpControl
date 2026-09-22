/*
 * PIC18F47Q10 temperature probe (throwaway; not part of the firmware build).
 *
 * One question only: what raw ADRES value does the ADCC produce for 2.5 V on RA5
 * (the temperature NTC pin, channel 5)?
 *
 * The firmware's temperature_c() assumes a 10-bit (0..1023) result. The Q10 ADCC is a
 * 12-bit converter. So 2.5 V can come back as:
 *     512   -> 10-bit right-justified   (what the firmware assumes)
 *     2048  -> 12-bit right-justified   (ADFM=1)  -> temperature_c() still trips 150
 *     32768 -> 12-bit left-justified    (ADFM=0)  -> temperature_c() trips 150
 *
 * This probe reads ADRESH/ADRESL separately AND the 16-bit ADRES, so the justification and
 * the resolution are both visible in the MDB transcript without any interpretation.
 *
 * Register values are read from PIC18F-Q_DFP/1.30.487's pic18f47q10.h, not assumed.
 */
#include <xc.h>

#pragma config FEXTOSC = OFF
#pragma config RSTOSC = HFINTOSC_64MHZ
#pragma config WDTE = OFF
#pragma config PWRTE = OFF
#pragma config CLKOUTEN = OFF
#pragma config MCLRE = EXTMCLR
#pragma config CP = OFF
#pragma config BOREN = ON
#pragma config BORV = VBOR_190

volatile unsigned int  g_raw   = 0;   /* ADRES (16-bit) after a completed conversion */
volatile unsigned char g_res_h = 0;   /* ADRESH byte */
volatile unsigned char g_res_l = 0;   /* ADRESL byte */
volatile unsigned char g_con0  = 0;   /* ADCON0 readback */
volatile unsigned char g_con2  = 0;   /* ADCON2 readback */
volatile unsigned char g_pch   = 0;   /* ADPCH readback */
volatile unsigned char g_done  = 0;   /* set once a conversion has completed */

void main(void) {
    unsigned int n;

    /* RA5 = ADC channel 5 = temperature NTC input (see firmware/include/pin_map.h). */
    ANSELA = 0x20;               /* RA5 analogue, everything else digital */
    TRISA  = 0x20;               /* RA5 input */

    /* ADCC, basic mode, right-justified — exactly what the working-tree adc_init() does. */
    ADCON1 = 0x00;               /* guard/precharge disabled */
    ADCON2 = 0x00;               /* ADMD=000 basic, no accumulator shift */
    ADCON3 = 0x00;               /* no threshold, no accumulator */
    ADCON0 = 0x88;               /* ADON=1, ADCS=0 (Fosc), single conversion */
    ADCON0bits.ADFM = 1;         /* right-justified result */

    ADPCH = 5;                   /* temperature channel */
    g_pch = ADPCH;

    /* Start one conversion and spin until GO_nDONE clears. */
    ADCON0bits.GO_nDONE = 1;
    for (n = 0; n < 200 && ADCON0bits.GO_nDONE; n++) { }

    g_res_h = ADRESH;
    g_res_l = ADRESL;
    g_raw   = (unsigned int)ADRES;
    g_con0  = ADCON0;
    g_con2  = ADCON2;
    g_done  = 1;

    /* Idle forever so MDB can read the globals. */
    while (1) { }
}
