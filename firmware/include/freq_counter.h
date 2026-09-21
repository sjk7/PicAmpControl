#ifndef FREQ_COUNTER_H
#define FREQ_COUNTER_H

#include <xc.h>
#include <stdbool.h>

typedef enum {
    BAND_160M = 1,
    BAND_UNKNOWN = BAND_160M,
    BAND_80M,
    BAND_40M,
    BAND_20M,
    BAND_15M,
    BAND_10M,
    BAND_OUT_OF_SPEC
} rf_band_t;

typedef struct {
    unsigned long raw_pulses;
    unsigned long frequency_hz;
    unsigned int frequency_khz;
    rf_band_t candidate_band;
    rf_band_t current_band;
    rf_band_t locked_band;
    bool band_locked;
    unsigned char stability_count;
} freq_counter_status_t;

// Initialize Timer1 and PPS for asynchronous frequency counting
void freq_counter_init(void);

// Handle Timer1 overflow interrupt (call from main ISR)
void freq_counter_isr(void);

// Process a 10ms scheduler tick: samples Timer1, updates frequency, and classifies band
void freq_counter_tick_10ms(void);

// Lock current band for transmit (freezes LPF relay changes during TX)
void freq_counter_lock_band(void);

// First-dit support: force current/locked/candidate band to a band remembered from an
// earlier TX cycle and lock it, so the LPF relays are already correct when the
// amplifier keys. freq_counter_lock_band() only freezes whatever current_band happens
// to be, which is the no-signal default during silence.
void freq_counter_restore_locked_band(rf_band_t band);

// Return true only when the stabilised current_band agrees with the latest measurement.
// Unlike freq_counter_signal_valid(), this cannot report a band left behind by earlier
// silence/noise (the 10 ms tick classifies an empty gate window as 160m).
bool freq_counter_band_confirmed(void);

// The band the latest stable measurement classifies to, or BAND_OUT_OF_SPEC when the gate
// window holds no usable RF. This ignores the lock, so a caller can tell that the incoming RF
// no longer matches the band the relay selection is frozen on.
rf_band_t freq_counter_measured_band(void);

// Unlock band after transmit returns to RX/Idle
void freq_counter_unlock_band(void);

// Get current frequency counter status
void freq_counter_get_status(freq_counter_status_t *status);

#endif // FREQ_COUNTER_H
