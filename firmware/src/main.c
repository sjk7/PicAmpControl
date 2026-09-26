#include <xc.h>
#include <stdbool.h>
#include "../include/pin_map.h"
#include "../include/lcd_parallel.h"
#include "../include/freq_counter.h"
#include "../include/settings.h"
#include "../include/outputs.h"
#include "../include/self_test.h"
#include "../include/state.h"
#include "../include/protection.h"
#include "../include/sequencer.h"
#include "../include/menu.h"
#include "../include/tx_selftest.h"
#include "../include/labels.h"

#pragma config FEXTOSC = OFF

/* PIC18F47Q10 is the ONLY device in this project (decided 2026-09-23; the PIC16F18875 port,
   and with it every 16F code path, build option and note, was removed). Config words therefore
   use this part's names only: RSTOSC must name the HFINTOSC rate,
   MCLR is EXTMCLR/INTMCLR, and BORV uses VBOR_xxx names - see the DFP's 18f47q10.cfgmap.
   
   THE CLOCK IS NOT A FREE CHOICE: this part's config map offers only two reset oscillator
   settings, `HFINTOSC_64MHZ` and `HFINTOSC_1MHZ` (there is no HFINT32 name here). Choose the
   64 MHz setting - the part's highest internal rate - and match `_XTAL_FREQ` to it (pin_map.h)
   so the XC8 `__delay_*` loops are compiled for the real core. Timer2 takes Fosc/8 so its input
   is 8 MHz and the 1 ms tick falls out of the PR2/prescaler chain below. */
#pragma config RSTOSC = HFINTOSC_64MHZ

#pragma config WDTE = OFF
#pragma config PWRTE = OFF

/* RA6 doubles as CLKOUT/OSC2 on this part, and the CLKOUTEN default is ON (the config bit
   reads clear = enabled; see the DFP's 18f47q10.cfgdata, CVALUE:1:OFF / CVALUE:0:ON). RA6 is
   OUTPUT_LCD_E in this design, so leaving the default silently hands the LCD enable line to the
   clock-output function and the panel never latches.

   Found on 2026-09-22 by reading the pin back under MDB in the boot trace: it reported
   `RA6 Ain 5.0V (RA6)/IOCA6/ANA6/CLKOUT/OSC2` even though the firmware had configured it as an
   output, which is what pointed at the undocumented-by-us config default. */
#pragma config CLKOUTEN = OFF

#pragma config MCLRE = EXTMCLR

#pragma config CP = OFF
#pragma config BOREN = ON

#pragma config BORV = VBOR_190

#define TX_ACTIVE_HIGH_DEFAULT false
#define TX_VCC_ACTIVE_HIGH_DEFAULT false
#define TX_BIAS_ACTIVE_HIGH_DEFAULT false
#define FAN_ACTIVE_HIGH_DEFAULT false
#define TRIP_ACTIVE_HIGH_DEFAULT false

/* Minimum sample-and-hold settling time after switching ADC channel, before
   starting a conversion; confirm against the datasheet's acquisition-time
   formula for each detector's actual source impedance during bench validation. */
#define ADC_ACQUISITION_US 5

/* --- State globals. The DEFINITIONS live here (one per symbol); every other module declares
   them `extern` through state.h. The simulator harnesses read these by .sym address, so the
   names, the types and the single-definition discipline must not change. --- */

volatile system_state_t g_state = STATE_STANDBY;
volatile bool g_fault_latched = false;
volatile unsigned char g_trip_reason = 0;
volatile bool g_trip_shutdown_active = false;
volatile unsigned char g_trip_shutdown_elapsed_ms = 0;
volatile bool g_ptt_active = false;
/* First-dit band memory (see docs/first-dit-band-detection.md). Declared volatile so the
   simulator/debugger can read and drive the cache state directly. */
volatile bool g_band_cache_valid = false;
volatile rf_band_t g_band_cache_band = BAND_UNKNOWN;
volatile bool g_snoop_active = false;
unsigned int g_band_cache_idle_ms = 0;
volatile bool g_band_settle_active = false;
unsigned int g_band_settle_elapsed_ms = 0;
volatile bool g_band_verify_active = false;
unsigned int g_band_verify_mismatch_ms = 0;
/* A band is "established" for the current transmission when it is backed by a real measurement
   or by the first-dit memory. This is what gates keying: with no RF the classifier reports its
   160m no-signal default, and the amplifier must never key on a band that was never measured. */
volatile bool g_band_established = false;
/* UNDEFINED/UNKEYABLE interlock: set when a keyed band lock lost its measurement. Read by the LCD
   so the bench sees why the amplifier is refusing to key, and cleared once a fresh decode exists. */
volatile bool g_unkeyable = false;
/* The longest-holding failing self-test check, in ms. Published for the simulator harnesses. */
unsigned int g_lock_loss_ms = 0;
/* The self-test's verdict for the CURRENT key-down (tx_selftest_run()). */
volatile bool g_selftest_failed = false;
volatile unsigned int g_selftest_reason = TX_SELFTEST_OK;
/* Consecutive-ms counters, one per check bit, indexed by bit position. */
unsigned int g_selftest_hold[TX_SELFTEST_CHECK_COUNT] = { 0 };
/* How long the current unkey has been unwinding, in ms: TX_SELFTEST_REL_STUCK's window. */
unsigned int g_selftest_unkey_ms = 0;

volatile bool g_startup_inhibit = true;
volatile bool g_comparator_reset_active = false;
volatile unsigned char g_comparator_reset_elapsed_ms = 0;
volatile menu_page_t g_menu_page = MENU_PAGE_POWER_TEMPERATURE;
volatile menu_page_t g_saved_user_menu_page = MENU_PAGE_POWER_TEMPERATURE;
ui_mode_t g_ui_mode = UI_MODE_HOME;
volatile bool g_transient_menu_display = false;
volatile bool g_boot_message_active = false;
volatile bool g_ptt_complete_display_active = false;
volatile unsigned int g_ptt_complete_display_elapsed_ms = 0;
volatile bool g_menu_changed = true;
unsigned int g_sequence_elapsed_ms = 0;
unsigned char g_sequence_stage = SEQ_IDLE;
/* Current stage as text. Refreshed once per main-loop pass so it can be used by the LCD debug
   read-out and read by the simulator harnesses. Initialised with a literal rather than
   SEQUENCE_STAGE_NAMES[SEQ_IDLE]: XC8 rejects a volatile pointer initialised from a ROM array
   element ("(712) can't generate code for this expression"). */
volatile const char *g_sequence_stage_text = "IDLE";
unsigned int g_post_fwd_rms_w = 0;
unsigned int g_post_fwd_pep_w = 0;
unsigned int g_swr1_live_hundredths = 100;
unsigned int g_swr2_live_hundredths = 100;
unsigned int g_live_temperature_c = 0;
unsigned int g_live_current_a = 0;
unsigned int g_current_peak_a = 0;
unsigned int g_live_overdrive_mw = 0;
unsigned int g_pep_decay_elapsed_ms = 0;
unsigned int g_current_peak_decay_elapsed_ms = 0;
unsigned int g_status_refresh_ms = 0;
unsigned int g_startup_elapsed_ms = 0;
volatile unsigned char g_timer_ticks_pending = 0;
menu_page_t g_lcd_drawn_page = MENU_PAGE_COUNT;
system_state_t g_lcd_drawn_state = STATE_RESET_WAIT;
unsigned char g_lcd_drawn_trip_reason = 0;
unsigned int g_menu_idle_ms = 0;
volatile bool g_settings_dirty = false;
unsigned int g_settings_save_delay_ms = 0;
volatile unsigned char g_adc_scan_index = 0;
volatile unsigned char g_adc_active_index = 0;
/* Defaults until the first real ADC scan completes for each channel: 0 (idle,
   no fault) for power/current/overdrive/drain, and a mid-scale ~2.5V reading
   for temp (raw 0 would otherwise map to a false 150C thermal trip). */
volatile unsigned int g_adc_samples[8] = {0, 0, 0, 0, 511, 0, 0, 0};
static const unsigned char g_adc_scan_channels[8] = {0, 1, 2, 3, 5, 9, 10, 11};

protection_thresholds_t g_thresholds = {
    30, 20,
    1500, 1500,
    1, 100,
    100,
    150,
    40,
    20, 20,
    TX_ACTIVE_HIGH_DEFAULT,
    TX_VCC_ACTIVE_HIGH_DEFAULT,
    TX_BIAS_ACTIVE_HIGH_DEFAULT,
    FAN_ACTIVE_HIGH_DEFAULT,
    TRIP_ACTIVE_HIGH_DEFAULT,
    true, false, PEAK_HOLD_DEFAULT_MS, PEAK_DECAY_DEFAULT_MS
};

void __interrupt() timer0_isr(void) {
    freq_counter_isr();

    bool tick = false;
    if (PIR4bits.TMR2IF != 0) {
        PIR4bits.TMR2IF = 0;
        tick = true;
        if (g_timer_ticks_pending != 255) {
            g_timer_ticks_pending++;
        }
    }

    if (PIR1bits.ADIF != 0) {
        unsigned int sample = (unsigned int)ADRES;
        PIR1bits.ADIF = 0;

        /* The ADCC is 12-bit (0..4095) while every converter below - temperature_c(),
           drain_voltage(), overdrive_power_mw(), current_amperes() and the SWR maths - treats
           the raw value as 10-bit (0..1023). Downscale once here, at capture, so all eight
           channels stay on the 10-bit scale the firmware already assumes. Measured 2026-09-22:
           without this, 2.5 V on the temp pin reads 2048 and temperature_c(2048) -> 2048>>2 =
           512 > 250 -> 150C fault sentinel. */
        sample >>= 2;

        /* Indexed store rather than an 8-case switch: g_adc_active_index is always a valid
           channel index (it is only ever loaded from g_adc_scan_index), and the switch cost
           eight copies of the same store in flash. */
        if (g_adc_active_index < 8) {
            g_adc_samples[g_adc_active_index] = sample;
        }
    }

    /* Refresh every trip ADC on the same bounded cadence. At one channel per
       1 ms tick, any ADC-based trip input is at most one 8-channel scan old. */
    if (tick && ADCON0bits.GO_nDONE == 0) {
        g_adc_active_index = g_adc_scan_index;
        ADPCH = g_adc_scan_channels[g_adc_scan_index];
        g_adc_scan_index++;
        if (g_adc_scan_index >= 8) {
            g_adc_scan_index = 0;
        }
        ADCON0bits.GO_nDONE = 1;
    }

}

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

int main(void) {
    unsigned int swr1_fwd_raw = 0;
    unsigned int swr1_ref_raw = 0;
    unsigned int swr2_fwd_raw = 0;
    unsigned int swr2_ref_raw = 0;
    unsigned int temp_raw = 0;
    unsigned int temp_c = 0;
    unsigned int overdrive_raw = 0;
    unsigned int drain_raw = 0;
    unsigned int overdrive_power = 0;
    unsigned int drain_voltage_v = 0;
    unsigned int current_raw = 0;

    /* Internal oscillator at 64 MHz, written explicitly.
     *
     * On silicon the config word (`#pragma config RSTOSC = HFINTOSC_64MHZ`) selects this at reset,
     * which is why it was implicit until now. The MDB simulator does NOT apply the config word -
     * after a full boot its `OSCCON1`/`OSCFRQ` still read 0 (measured 2026-09-24) - so a simulated
     * run is not at the design clock unless the clock is programmed in code. Writing what the config
     * word already implies is harmless on hardware and makes the simulation match:
     *   NDIV = 0 (/1), NOSC = 0b0110 = HFINTOSC, HFFRQ = 0x07 = 64 MHz
     * (HFFRQ has no 32 MHz step above 16: 0 = 1, 1 = 2, 2 = 4, 3 = 8, 4 = 12, 5 = 16, 6 = 32, 7 = 64.) */
    OSCCON1 = 0x60;
    OSCFRQ = 0x07;

    TRISAbits.TRISA0 = 1;
    TRISAbits.TRISA1 = 1;
    TRISAbits.TRISA2 = 1;
    TRISAbits.TRISA3 = 1;
    TRISAbits.TRISA4 = 0;
    TRISAbits.TRISA5 = 1;
    TRISAbits.TRISA6 = 0;
    TRISAbits.TRISA7 = 0;
    ANSELC = 0x00;
    TRISCbits.TRISC0 = 1;
    WPUCbits.WPUC0 = 1;
    TRISCbits.TRISC1 = 0;
    TRISCbits.TRISC2 = 1;
    WPUCbits.WPUC2 = 1;
    TRISCbits.TRISC3 = 0;
    TRISCbits.TRISC4 = 0;
    TRISCbits.TRISC5 = 0;
    TRISCbits.TRISC6 = 0;
    TRISCbits.TRISC7 = 0;

    TRISB = 0x5F;
    TRISBbits.TRISB6 = 1;
    PORTB = 0x00;
    WPUB = 0x43;

    /* Port D for parallel LCD D7 pin; RD1 (freq counter) and RD2-RD7 (band
       outputs) are configured separately by freq_counter_init(). */
    TRISD = 0xFE;  /* RD0 = output (LCD D7), rest inputs for now */

    set_tx_output(false);
    set_tx_vcc_output(false);
    set_tx_bias_output(false);
    set_fan_output(false);
    set_trip_output(false);

    /* ORDER MATTERS, AND IT IS A SAFETY PROPERTY.
     *
     * The 1 ms system tick is the only periodic supervision this amplifier has: it is what
     * advances the startup-inhibit window, the band-settle delay, the band-verify timeout and
     * every trip debounce. Nothing below this point may run with the amplifier able to key and
     * no tick, because a stall anywhere in the remaining bring-up would then leave the outputs
     * latched with no supervision at all.
     *
     * It used to run at the *end* of initialisation - after `lcd_init()` and
     * `show_boot_message()` - and the Q10 bring-up run on 2026-09-22 showed exactly why that is
     * wrong: 200,000 simulator steps in, `T2CON` and `OSCCON1` still read 0 because the LCD boot
     * sequence had not finished, so the tick was not yet armed. The LCD is the slowest and least
     * trustworthy thing in the boot path (a held E line or a missing panel can block it), and it
     * must never be a prerequisite for the protection tick.
     *
     * So the sequence is now: force every output safe -> arm the tick -> then talk to the LCD and
     * the rest. `apply_startup_inhibit()` immediately follows, so the outputs stay inhibited while
     * the slow peripherals come up. */
    timer0_init();
    apply_startup_inhibit();

    adc_init();
    load_settings();
    lcd_init();
    show_boot_message();
    g_boot_message_active = true;

    while (1) {
        if (g_diag_request && !diag_busy()) {
            g_diag_request = false;
            diag_start();
        }
        if (diag_busy()) {
            /* The diagnostic owns every output while it runs: freeze protection, the sequencer,
               the frequency counter and the TX self-test so none of them re-drive a pin under
               test. The amplifier is already cold (forced bypass at start); just advance time,
               step the diagnostic and keep the LCD fresh. */
            unsigned int diag_ms = 0;
            while (g_timer_ticks_pending != 0) {
                g_timer_ticks_pending--;
                diag_ms++;
            }
            diag_tick(diag_ms);
            if (g_menu_changed) {
                show_menu_page();
                g_menu_changed = false;
            }
            lcd_service(2);
            continue;
        }

        swr1_fwd_raw = ADC_SAMPLE_SWR1_FWD;
        swr1_ref_raw = ADC_SAMPLE_SWR1_REF;
        swr2_fwd_raw = ADC_SAMPLE_SWR2_FWD;
        swr2_ref_raw = ADC_SAMPLE_SWR2_REF;
        temp_raw = ADC_SAMPLE_TEMP;
        temp_c = temperature_c(temp_raw);
        overdrive_raw = ADC_SAMPLE_OVERDRIVE;
        drain_raw = ADC_SAMPLE_DRAIN;
        overdrive_power = overdrive_power_mw(overdrive_raw);
        drain_voltage_v = drain_voltage(drain_raw);
        current_raw = ADC_SAMPLE_CURRENT;
        update_post_filter_power(swr2_fwd_raw, swr2_ref_raw);
        g_swr2_live_hundredths = compute_swr_hundredths(swr2_fwd_raw, swr2_ref_raw);
        g_swr1_live_hundredths = compute_swr_hundredths(swr1_fwd_raw, swr1_ref_raw);
        g_live_temperature_c = temp_c;
        g_live_current_a = current_amperes(current_raw);
        update_current_peak(g_live_current_a);
        g_live_overdrive_mw = overdrive_power;

        bool swr1_fault = swr_trip(swr1_fwd_raw, swr1_ref_raw,
                       g_thresholds.swr1_trip_tenths);
        bool swr2_fault = swr_trip(swr2_fwd_raw, swr2_ref_raw,
                       g_thresholds.swr2_trip_tenths);
        bool hw_fault = (INPUT_OVERCURRENT_FAULT == 1);
        unsigned int current_trip_raw = CURRENT_SENSOR_ZERO_RAW +
            (unsigned int)(((unsigned long)g_thresholds.current_trip_a *
                            CURRENT_SENSOR_POSITIVE_COUNTS) /
                           CURRENT_SENSOR_FULL_SCALE_A);
        bool current_fault = (current_raw >= current_trip_raw);

        if ((INPUT_PTT == 0) != g_ptt_active) {
            handle_ptt_transition(INPUT_PTT == 0);
        }

        update_protection_state(temp_c, overdrive_power, drain_voltage_v,
                                swr1_fault,
                                swr2_fault,
                                hw_fault,
                                current_fault);

        unsigned int elapsed_ms = 0;
        while (g_timer_ticks_pending != 0) {
            g_timer_ticks_pending--;
            elapsed_ms++;
            if (g_comparator_reset_active) {
                g_comparator_reset_elapsed_ms++;
                if (g_comparator_reset_elapsed_ms >= 10) {
                    OUTPUT_COMP_RESET = 1;
                    g_comparator_reset_active = false;
                }
            }
            if (g_trip_shutdown_active) {
                g_trip_shutdown_elapsed_ms++;
                if (g_trip_shutdown_elapsed_ms >= 5) {
                    set_tx_output(false);
                    set_tx_bias_output(false);
                    g_trip_shutdown_active = false;
                }
            }
            if (g_ptt_complete_display_active) {
                g_ptt_complete_display_elapsed_ms++;
                if (g_ptt_complete_display_elapsed_ms >= 500) {
                    g_ptt_complete_display_active = false;
                    g_ptt_complete_display_elapsed_ms = 0;
                    if (!g_fault_latched) {
                        g_transient_menu_display = false;
                        g_menu_page = g_saved_user_menu_page;
                    }
                    g_menu_changed = true;
                }
            }
            if (g_startup_inhibit) {
                g_startup_elapsed_ms++;
                if (g_startup_elapsed_ms >= 1000) {
                    g_startup_inhibit = false;
                    g_boot_message_active = false;
                    g_menu_changed = true;
                    // Single low->high transition signals hardware has settled; PTT
                    // is only actionable after this (SETTLE then idles high, pulsing
                    // low again on each subsequent PTT transition).
                    OUTPUT_COMP_RESET = 1;
                }
            } else {
                update_peak_decay(&g_post_fwd_pep_w, &g_pep_decay_elapsed_ms, 1);
                update_peak_decay(&g_current_peak_a, &g_current_peak_decay_elapsed_ms, 1);
                update_tx_sequence();
            }
            /* First-dit band memory ages only while receiving. After a long idle period
               the operator may have changed bands, so the remembered band is dropped and
               the next PTT goes back to bypass-snoop. */
            if (!g_ptt_active && g_band_cache_valid) {
                if (g_band_cache_idle_ms < BAND_CACHE_IDLE_TIMEOUT_MS) {
                    g_band_cache_idle_ms++;
                } else {
                    g_band_cache_valid = false;
                    g_band_cache_band = BAND_UNKNOWN;
                    g_band_cache_idle_ms = 0;
                }
            }
            static unsigned char fc_tick_ms = 0;
            fc_tick_ms++;
            if (fc_tick_ms >= 10) {
                fc_tick_ms = 0;
                freq_counter_tick_10ms();
                /* The keyed self-test rides the same gate: it reads exactly what that gate produced,
                   and it must not add work to the per-millisecond path (see TX_SELFTEST_TICK_MS).
                   It performs its own action, so the sequence picks the result up on the next tick. */
                tx_selftest_run();
            }

            if (g_settings_save_delay_ms > 0) {
                g_settings_save_delay_ms--;
            }
            g_status_refresh_ms++;
        }

        poll_menu_inputs(elapsed_ms);

        /* Publish the sequence stage as text: `sequence_stage_name()` is the one conversion and
           this keeps the published copy in step with the state machine. */
        g_sequence_stage_text = sequence_stage_name(g_sequence_stage);

        if (!g_boot_message_active &&
            (g_menu_page == MENU_PAGE_STATUS ||
             g_menu_page == MENU_PAGE_POWER_TEMPERATURE ||
             g_menu_page == MENU_PAGE_SWR_METER ||
             g_menu_page == MENU_PAGE_CURRENT_METER)) {
            if (g_status_refresh_ms >= 100 || g_menu_changed) {
                show_menu_page();
                g_status_refresh_ms = 0;
                g_menu_changed = false;
            }
        } else if (!g_boot_message_active && g_menu_changed) {
            show_menu_page();
            g_menu_changed = false;
        }

        /* Drain a few queued LCD bytes per pass instead of blocking for a
           whole page, so update_protection_state() above is never starved by
           an in-progress screen redraw (see bench-validation.md timing budget). */
        lcd_service(2);

        service_settings_save();
    }
}
