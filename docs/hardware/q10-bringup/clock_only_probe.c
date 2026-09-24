/*
 * Clock-only probe (throwaway; not part of the firmware build).
 *
 * Purpose: measure the simulator's execution rate with NOTHING in the way. The full firmware
 * drags the LCD, the ADC scan, EEPROM and the menu loop through every measurement, and MDB prints
 * a warning for each - which is both noise and a different code path from "how fast does the model
 * clock the core". This program is the clock and nothing else:
 *   - the same config words as firmware/src/main.c (RSTOSC = HFINTOSC_64MHZ, FEXTOSC = OFF),
 *     so the intended 64 MHz core is what is being asked for;
 *   - the same Timer2 setup as timer0_init() (T2CLK = Fosc/8, CKPS = 1:64, OUTPS = 0, PR2 = 124);
 *   - one ISR that increments a counter and nothing else;
 *   - a bare `while (1) {}` main loop - no LCD, no ADC, no NVM, no delays, no printing.
 *
 * Read g_ticks before and after a known number of MDB `Stepi` steps: the ratio is the model's
 * steps per firmware millisecond. Ask MDB `Stopwatch` at the same points to get the model's own
 * cycle count, which is the model's idea of elapsed time.
 *
 * Build (macOS):
 *   xc8-cc -mcpu=18F47Q10 -mdfp=/Applications/microchip/mplabx/v6.35/packs/Microchip/PIC18F-Q_DFP/1.30.487/xc8 \
 *          -O1 -gdwarf-3 -std=c99 clock_only_probe.c -o _build/clock_probe/clock_only_probe.elf
 */
#include <xc.h>

#pragma config FEXTOSC = OFF
#pragma config RSTOSC = HFINTOSC_64MHZ
#pragma config CLKOUTEN = OFF
#pragma config WDTE = OFF
#pragma config PWRTE = OFF
#pragma config MCLRE = EXTMCLR
#pragma config CP = OFF
#pragma config BOREN = ON
#pragma config BORV = VBOR_190

/* One increment per Timer2 overflow interrupt. volatile so the simulator can read it by name. */
volatile unsigned int g_ticks = 0;

void __interrupt() isr(void) {
    if (PIR4bits.TMR2IF) {
        PIR4bits.TMR2IF = 0;
        g_ticks++;
    }
}

void main(void) {
    /* --- clock: 64 MHz internal HFINTOSC, written explicitly ---
     * On silicon the config word `RSTOSC = HFINTOSC_64MHZ` already selects this, which is why
     * firmware/src/main.c never writes these registers. The simulator was measured NOT to apply the
     * config word (after 300,000 steps of the real firmware `OSCCON1`, `OSCFRQ` and `OSCCON3` all
     * still read 0), so this probe - and anything else that needs the model to run at the design
     * clock - programs the oscillator in code instead:
     *   OSCCON1 = 0x60 -> NDIV = 0 (/1), NOSC = 0b0110 = HFINTOSC as the system clock
     *   OSCFRQ  = 0x07 -> HFFRQ = 64 MHz (the Q10 has no 32 MHz step above 16: 0=1, 1=2, 2=4,
     *                    3=8, 4=12, 5=16, 6=32, 7=64 MHz)
     * Setting OSCFRQ without selecting HFINTOSC leaves the frequency register ignored, which is
     * why an MDB `write OSCFRQ 0x07` alone changed nothing. */
    OSCCON1 = 0x60;
    OSCFRQ = 0x07;
    /* 6 = 0b0110 = HFINTOSC; wait for the switch to be visible before timing anything. */
    while (OSCCON1bits.NOSC != 6) {
    }

    /* Exactly the tick setup firmware/src/main.c timer0_init() uses. */
    T2CLK = 0x02;         /* Fosc/8: 64 MHz core -> 8 MHz Timer2 input */
    T2CONbits.CKPS = 6;   /* 1:64 prescale */
    T2CONbits.OUTPS = 0;  /* 1:1 postscale */
    PR2 = 124;            /* (124+1) * 64 / 8MHz = 1.000ms on silicon */
    TMR2 = 0;
    PIR4bits.TMR2IF = 0;
    PIE4bits.TMR2IE = 1;

    /* The priority mechanism has to be armed before anything is dispatched (measured on this
       model: with IPEN = 0 no interrupt ever reaches the ISR). */
    INTCONbits.IPEN = 1;
    IPR4bits.TMR2IP = 1;

    T2CONbits.ON = 1;
    INTCONbits.GIE = 1;

    while (1) {
    }
}
