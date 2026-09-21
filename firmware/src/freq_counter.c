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
    ANSELDbits.ANSD1 = 0;

    // RD2-RD7: one digital output per band, driving the LPF relays.
    ANSELDbits.ANSD2 = 0;
    ANSELDbits.ANSD3 = 0;
    ANSELDbits.ANSD4 = 0;
    ANSELDbits.ANSD5 = 0;
    ANSELDbits.ANSD6 = 0;
    ANSELDbits.ANSD7 = 0;
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

void freq_counter_tick_10ms(void) {
    // Disable interrupt briefly or atomic read to capture counter and overflows cleanly
    bool ie_save = PIE4bits.TMR1IE;
    PIE4bits.TMR1IE = 0;

    unsigned int tmr1_val = TMR1;
    unsigned int overflows = g_tmr1_overflows;

    // Handle overflow that occurred just before reading
    if (PIR4bits.TMR1IF && tmr1_val < 32768U) {
        overflows++;
        PIR4bits.TMR1IF = 0;
    }

    // Reset counter for next 10ms gate window
    TMR1 = 0;
    g_tmr1_overflows = 0;

    PIE4bits.TMR1IE = ie_save;

    // Calculate raw pulses in 10ms
    unsigned long total_pulses = ((unsigned long)overflows * 65536UL) + tmr1_val;
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

    if (g_fc_status.stability_count >= STABILITY_REQUIRED_TICKS) {
        g_fc_status.current_band = measured_band;
    }

    update_band_outputs(g_fc_status.current_band);
}

void freq_counter_lock_band(void) {
    g_fc_status.band_locked = true;
    g_fc_status.locked_band = g_fc_status.current_band;
}

void freq_counter_restore_locked_band(rf_band_t band) {
    if (band == BAND_OUT_OF_SPEC) {
        return;  // Nothing usable to restore; leave the live measurement in charge.
    }
    g_fc_status.current_band = band;
    g_fc_status.candidate_band = band;
    g_fc_status.locked_band = band;
    g_fc_status.band_locked = true;
    update_band_outputs(band);
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
