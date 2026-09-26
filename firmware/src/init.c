#include <xc.h>
#include <stdbool.h>
#include "../include/pin_map.h"
#include "../include/state.h"
#include "../include/freq_counter.h"
#include "../include/outputs.h"
#include "../include/init.h"

/* Board bring-up: the system tick, the ADC, and the startup-inhibit window. */

/* Minimum sample-and-hold settling time after switching ADC channel, before
   starting a conversion; confirm against the datasheet's acquisition-time
   formula for each detector's actual source impedance during bench validation. */
#define ADC_ACQUISITION_US 5

void timer0_init(void) {
    /* Timer2 (not Timer0) drives the ~1ms system tick: TMR0's Fosc/4 overflow model
       stalls under MDB after the first interrupt, and Timer2's simpler compare-based
       architecture doesn't hit that issue on either real hardware or the simulator.

       Timer2 is clocked so that (clock / prescale / (PR2+1)) = 1 kHz:
         PIC18F47Q10: 64 MHz core, Fosc/8 = 8 MHz, 1:64, PR2 = 124 -> 8e6/64/125   = 1.000 kHz
       T2CLK is a code, not a divisor: 0x01 = Fosc/4, 0x02 = Fosc/8 (per the DFP). */
    T2CLK = 0x02;         /* Fosc/8: 64 MHz core -> 8 MHz Timer2 input */
    T2CONbits.CKPS = 6;   /* 1:64 prescale */
    T2CONbits.OUTPS = 0;  /* 1:1 postscale */
    PR2 = 124;            /* (124+1) * 64 / 8MHz = 1.000ms */
    TMR2 = 0;
    PIR4bits.TMR2IF = 0;
    PIE4bits.TMR2IE = 1;

    /* This family needs its priority mechanism armed before anything is dispatched. Measured on
       the simulator: with IPEN = 0 no interrupt ever reaches the ISR, even though TMR2IF sets and
       the peripheral enable is set. IPEN = 1, the source's IPRx priority bit, and the matching
       global (GIE/GIEH) make it run at once. */
    INTCONbits.IPEN = 1;
    IPR4bits.TMR2IP = 1;    /* system tick at high priority */

    T2CONbits.ON = 1;

    freq_counter_init();

    INTCONbits.GIE = 1;
}

void adc_init(void) {
    FVRCON = 0x00;
    ANSELA = 0x2F;
    ANSELA &= ~0x10; /* RA4 must stay digital: it drives OUTPUT_LCD_RS */
    ANSELB = 0x0E;
    ADCON1 = 0x20;
    ADPCH = 0;
    // The result must be a plain right-justified 0-1023 count: temperature_c(),
    // drain_voltage() and overdrive_power_mw() all treat the raw ADC value as 0-1023.
    //
    // ADCC ADFM is a SINGLE bit, ADCON0<2>, and 0 means LEFT-justified. The 10-bit result then
    // sits in ADRES<15:6>, so a 2.5V temperature input (raw 512) reads as 512<<6 = 32768 and
    // temperature_c() returns its 150C fault sentinel, which is exactly the spurious TEMPERATURE
    // trip the bring-up hit (probe_q10_ptt_path.py, 2026-09-22).
    ADCON0 = 0x88;
    ADCON0bits.ADFM = 1;
    PIR1bits.ADIF = 0;
    PIE1bits.ADIE = 1;
    INTCONbits.PEIE = 1;
    __delay_us(ADC_ACQUISITION_US);
    ADCON0bits.GO_nDONE = 1;
}

void apply_startup_inhibit(void) {
    apply_bypass();
    set_fan_output(false);
    set_trip_output(false);
    OUTPUT_COMP_RESET = 0; // SETTLE held low for the startup-inhibit window
    g_startup_inhibit = true;
    /* Power-up has no idea which band the operator is on: drop any remembered band and
       require a fresh first-dit measurement before the amplifier may key. */
    g_band_cache_valid = false;
    g_band_cache_band = BAND_UNKNOWN;
    g_band_cache_idle_ms = 0;
    g_snoop_active = false;
    g_band_settle_active = false;
    g_band_settle_elapsed_ms = 0;
    g_band_verify_active = false;
    g_band_verify_mismatch_ms = 0;
    g_band_established = false;
}
