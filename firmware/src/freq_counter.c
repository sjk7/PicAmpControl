#include "../include/freq_counter.h"
#include "../include/pin_map.h"

static volatile unsigned int g_tmr1_overflows = 0;
static freq_counter_status_t g_fc_status = {
    .raw_pulses = 0,
    .frequency_hz = 0,
    .frequency_khz = 0,
    .candidate_band = BAND_UNKNOWN,
    .current_band = BAND_UNKNOWN,
    .locked_band = BAND_UNKNOWN,
    .band_locked = false,
    .stability_count = 0
};

#define STABILITY_REQUIRED_TICKS 2  // 2 x 10ms = 20ms stable reading to confirm band change

// Band frequency boundaries in kHz
// 160m: 1800 - 2000 kHz
// 80m:  3500 - 4000 kHz
// 40m:  7000 - 7300 kHz
// 20m:  14000 - 14350 kHz
// 15m:  21000 - 21450 kHz
// 10m:  28000 - 29700 kHz

static rf_band_t classify_frequency_khz(unsigned int freq_khz) {
    if (freq_khz < 1000U) {
        return BAND_160M; // Default to the lowest band when there is no valid RF or noise.
    } else if (freq_khz >= 1500U && freq_khz <= 2750U) {
        return BAND_160M;
    } else if (freq_khz > 2750U && freq_khz <= 5500U) {
        return BAND_80M;
    } else if (freq_khz > 5500U && freq_khz <= 10500U) {
        return BAND_40M;
    } else if (freq_khz > 10500U && freq_khz <= 17500U) {
        return BAND_20M;
    } else if (freq_khz > 17500U && freq_khz <= 24500U) {
        return BAND_15M;
    } else if (freq_khz > 24500U && freq_khz <= 32000U) {
        return BAND_10M;
    } else {
        return BAND_OUT_OF_SPEC;
    }
}

static void update_band_outputs(rf_band_t band) {
    OUTPUT_BAND_160M = (band == BAND_160M) ? 1 : 0;
    OUTPUT_BAND_80M  = (band == BAND_80M)  ? 1 : 0;
    OUTPUT_BAND_40M  = (band == BAND_40M)  ? 1 : 0;
    OUTPUT_BAND_20M  = (band == BAND_20M)  ? 1 : 0;
    OUTPUT_BAND_15M  = (band == BAND_15M)  ? 1 : 0;
    OUTPUT_BAND_10M  = (band == BAND_10M)  ? 1 : 0;
}

void freq_counter_init(void) {
    // Configure RD1 as digital input for T1CKI
    TRISDbits.TRISD1 = 1;

    // RD2-RD7: one digital output per band, driving the LPF relays.
    // The analog-select register is cleared as a whole rather than bit by bit: every PORTD pin
    // in this design is digital anyway - RD0 drives the LCD, RD1 is the T1CKI frequency-counter
    // input, RD2-RD7 are the band relays - so selecting all-digital is correct for this part,
    // whose analog-select register is ANSELD.
    ANSELD = 0x00;
    TRISDbits.TRISD2 = 0;
    TRISDbits.TRISD3 = 0;
    TRISDbits.TRISD4 = 0;
    TRISDbits.TRISD5 = 0;
    TRISDbits.TRISD6 = 0;
    TRISDbits.TRISD7 = 0;
    update_band_outputs(BAND_UNKNOWN);

    // Map T1CKI input to RD1 via PPS (Port D = 0x18 + pin 1 = 0x19)
    T1CKIPPS = 0x19;

    // Configure Timer1:
    // Clock source: T1CKIPPS (0x00)
    // Prescaler: 1:4 (CKPS = 2)
    // Async mode: nSYNC = 1 (do not sync to Fosc)
    // 16-bit read: RD16 = 1
    T1CLKbits.CS = 0x00;
    T1CONbits.CKPS = 0x02;
    T1CONbits.nSYNC = 1;
    T1CONbits.RD16 = 1;

    TMR1 = 0;
    g_tmr1_overflows = 0;

    PIR4bits.TMR1IF = 0;
    PIE4bits.TMR1IE = 1;  // Enable Timer1 overflow interrupt

    T1CONbits.ON = 1;     // Enable Timer1 counter
}

void freq_counter_isr(void) {
    if (PIE4bits.TMR1IE && PIR4bits.TMR1IF) {
        PIR4bits.TMR1IF = 0;
        g_tmr1_overflows++;
    }
}

/* Atomic read of the async counter.
 *
 * T1CON.nSYNC = 1 means Timer1 counts RD1 asynchronously, with no relationship to the CPU clock.
 * That is what makes the frequency counter work at all, and it is also what makes reading it
 * racy: while Timer1 is running, the CPU can be preempted between the two byte reads of the
 * 16-bit value, or the counter can carry into the high byte between them, and the ISR can bump
 * `g_tmr1_overflows` at any instant. The old code disabled the *interrupt* around the read, which
 * stops the ISR but not the counter - so a carry could still land between the low and high byte
 * and produce a value that is too high by 256, in the middle of the band classification.
 *
 * The fix is to read from a state that cannot change: stop Timer1, take the 16-bit value and the
 * overflow count, then restart. `RD16 = 1` makes `TMR1` a single 16-bit access, so with the
 * counter stopped the value is inherently consistent; and because the counter is stopped, the
 * overflow count cannot change underneath us either.
 *
 * Both halves matter for the same reason. The gate window is 10 ms, so losing a few cycles of
 * counting to the stop/start is 0.05% - far below the tolerance of a band classification that
 * separates 40m (7.0 MHz) from 20m (14 MHz). A torn read, by contrast, can shift the count by
 * 65536/4 = 16384 Hz-worth of pulses=*4 prescale = a whole band. Correctness is worth more than
 * the handful of cycles.
 *
 * This is deliberately written so it is correct regardless of which device is running: it makes
 * no assumption about clock ratio between the CPU and the counted signal, which is exactly the
 * assumption that stops holding when the core moves from 32 MHz to 64 MHz.
 */
static unsigned long read_counter_atomically(unsigned int *counter_out)
{
    bool ie_save = PIE4bits.TMR1IE;
    bool was_on = T1CONbits.ON;

    PIE4bits.TMR1IE = 0;      /* stop the ISR from bumping the overflow count */
    T1CONbits.ON = 0;         /* stop the counter: the value cannot move now */

    unsigned int counter = TMR1;
    unsigned int overflows = g_tmr1_overflows;

    /* An overflow that completed before we stopped the counter may have set TMR1IF without the
       ISR having run yet. A low value means the counter wrapped on the way to us, so account for
       it exactly once - the flag is cleared here so the ISR does not later double-count it. */
    if (PIR4bits.TMR1IF) {
        PIR4bits.TMR1IF = 0;
        if (counter < 0x8000U) {
            overflows++;
        }
    }

    TMR1 = 0;                 /* restart the gate window from a known state */
    g_tmr1_overflows = 0;

    if (was_on) {
        T1CONbits.ON = 1;
    }
    PIE4bits.TMR1IE = ie_save;

    *counter_out = counter;
    return ((unsigned long)overflows * 65536UL) + counter;
}

void freq_counter_tick_10ms(void) {
    unsigned int tmr1_val = 0;
    unsigned long total_pulses = read_counter_atomically(&tmr1_val);
    g_fc_status.raw_pulses = total_pulses;

    // Frequency calculation:
    // Prescaler = 1:4, Gate = 10ms (0.01s)
    // Frequency (Hz) = pulses * 4 / 0.01 = pulses * 400
    // Frequency (kHz) = pulses * 400 / 1000 = (pulses * 2) / 5
    g_fc_status.frequency_hz = total_pulses * 400UL;
    g_fc_status.frequency_khz = (unsigned int)((total_pulses * 2UL) / 5UL);

    // Classify candidate band
    rf_band_t measured_band = classify_frequency_khz(g_fc_status.frequency_khz);

    // The candidate/stability tracker follows the incoming RF even while the band is locked,
    // so the TX path can tell whether the RF being received still matches the frozen band
    // (freq_counter_measured_band()).
    if (measured_band == g_fc_status.candidate_band) {
        if (g_fc_status.stability_count < 255) {
            g_fc_status.stability_count++;
        }
    } else {
        g_fc_status.candidate_band = measured_band;
        g_fc_status.stability_count = 1;
    }

    // If band is locked (during transmit), do NOT update current_band or switch relays!
    if (g_fc_status.band_locked) {
        update_band_outputs(g_fc_status.current_band);
        return;
    }

    /* Only follow a usable measurement. An empty gate window classifies as the 160m
       no-signal default, and driving the relay selection from that would make the LPF
       relays chatter to 160m after every over and leave the selection disagreeing with
       current_band (invariant I4). Holding the last real selection also means a warm
       re-key on the same band moves no relay at all, so the T/R relay can close
       straight away instead of waiting on a relay that was never going to move.
       The frequency bound is what separates real 160m (1800-2000 kHz) from silence. */
    if (g_fc_status.stability_count >= STABILITY_REQUIRED_TICKS &&
        measured_band != BAND_OUT_OF_SPEC &&
        g_fc_status.frequency_khz >= 1000U) {
        g_fc_status.current_band = measured_band;
    }

    update_band_outputs(g_fc_status.current_band);
}

void freq_counter_lock_band(void) {
    g_fc_status.band_locked = true;
    g_fc_status.locked_band = g_fc_status.current_band;
}

bool freq_counter_restore_locked_band(rf_band_t band) {
    if (band == BAND_OUT_OF_SPEC) {
        return false;  // Nothing usable to restore; leave the live measurement in charge.
    }
    /* The relay selection is driven from current_band on every tick, so a difference here
       is exactly a relay move the caller has to let settle before the T/R relay closes. */
    bool relay_selection_changed = (g_fc_status.current_band != band);
    g_fc_status.current_band = band;
    g_fc_status.candidate_band = band;
    g_fc_status.locked_band = band;
    g_fc_status.band_locked = true;
    update_band_outputs(band);
    return relay_selection_changed;
}

bool freq_counter_band_confirmed(void) {
    return freq_counter_measured_band() != BAND_OUT_OF_SPEC &&
           g_fc_status.candidate_band == g_fc_status.current_band;
}

rf_band_t freq_counter_measured_band(void) {
    if (g_fc_status.stability_count < STABILITY_REQUIRED_TICKS) {
        return BAND_OUT_OF_SPEC;
    }
    if (g_fc_status.frequency_khz < 1000U || g_fc_status.frequency_khz > 32000U) {
        return BAND_OUT_OF_SPEC;
    }
    return g_fc_status.candidate_band;
}

void freq_counter_unlock_band(void) {
    g_fc_status.band_locked = false;
}

void freq_counter_get_status(freq_counter_status_t *status) {
    if (status != NULL) {
        *status = g_fc_status;
    }
}
