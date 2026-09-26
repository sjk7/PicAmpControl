#include <stdbool.h>
#include "../include/pin_map.h"
#include "../include/settings.h"
#include "../include/state.h"
#include "../include/outputs.h"
#include "../include/protection.h"

/* Protection and measurement maths, plus the single trip state machine
   (update_protection_state). */

/* NTC ADC-to-temperature table, indexed [b_profile][adc_step]. */
static const unsigned char g_ntc_adc[3][16] = {
    {190, 166, 141, 116, 94, 75, 59, 46, 37, 29, 23, 19, 15, 12, 10, 8},
    {197, 171, 142, 114, 89, 68, 51, 38, 29, 22, 17, 13, 10, 8, 6, 5},
    {201, 174, 143, 113, 86, 64, 47, 34, 25, 19, 14, 11, 8, 6, 5, 4}
};

bool swr_trip(unsigned int forward_raw,
              unsigned int reflected_raw,
              unsigned char limit_tenths) {
    unsigned long upper_factor;
    unsigned long lower_factor;

    if (forward_raw < 10 || limit_tenths <= 10) {
        return false;
    }

    upper_factor = (unsigned long)(limit_tenths + 10) * (limit_tenths + 10);
    lower_factor = (unsigned long)(limit_tenths - 10) * (limit_tenths - 10);
        return (unsigned long)reflected_raw * upper_factor >=
            (unsigned long)forward_raw * lower_factor;
}

unsigned int isqrt32(unsigned long value) {
    unsigned long result = 0;
    unsigned long bit = 1UL << 30;

    while (bit > value) {
        bit >>= 2;
    }
    while (bit != 0) {
        if (value >= result + bit) {
            value -= result + bit;
            result = (result >> 1) + bit;
        } else {
            result >>= 1;
        }
        bit >>= 2;
    }
    return (unsigned int)result;
}

/* Power-based SWR: forward/reflected ADC samples are proportional to power, so
    SWR = (1 + sqrt(Pr/Pf)) / (1 - sqrt(Pr/Pf)), computed here in fixed-point
    hundredths since this part has no FPU/sqrt(). Display-only; not used for trips. */
unsigned int compute_swr_hundredths(unsigned int forward_raw, unsigned int reflected_raw) {
    unsigned long ratio_scaled;
    unsigned int sqrt_ratio;
    unsigned int denominator;
    unsigned long swr_hundredths;

    if (forward_raw < 10) {
        return 100;
    }

    ratio_scaled = ((unsigned long)reflected_raw * 1000000UL) / forward_raw;
    sqrt_ratio = isqrt32(ratio_scaled);
    if (sqrt_ratio > 999) {
        sqrt_ratio = 999;
    }

    denominator = (unsigned int)(1000 - sqrt_ratio);
    swr_hundredths = ((unsigned long)(1000 + sqrt_ratio) * 100UL) / denominator;
    if (swr_hundredths > 9999) {
        swr_hundredths = 9999;
    }
    return (unsigned int)swr_hundredths;
}

unsigned int drain_voltage(unsigned int raw) {
    return (unsigned int)(((unsigned long)raw * 300UL) / 1023UL);
}

unsigned int temperature_c(unsigned int raw) {
    const unsigned char *table = g_ntc_adc[g_thresholds.temp_b_profile];
    unsigned char index;

    raw >>= 2;
    if (raw > 250) {
        return 150;
    }
    if (raw >= table[0]) {
        return 0;
    }
    for (index = 1; index < 16; index++) {
        if (raw >= table[index]) {
            return (unsigned int)(index * 10U);
        }
    }
    return 150;
}

unsigned int overdrive_power_mw(unsigned int raw) {
    unsigned long squared_raw = (unsigned long)raw * raw;
    return (unsigned int)(((squared_raw / 1023UL) * 10000UL) / 1023UL);
}

unsigned int current_amperes(unsigned int raw) {
    if (raw <= CURRENT_SENSOR_ZERO_RAW) {
        return 0;
    }
    return (unsigned int)(((unsigned long)(raw - CURRENT_SENSOR_ZERO_RAW) *
                           CURRENT_SENSOR_FULL_SCALE_A) /
                          CURRENT_SENSOR_POSITIVE_COUNTS);
}

void update_post_filter_power(unsigned int forward_raw, unsigned int reflected_raw) {
    unsigned int forward_w = (unsigned int)(((unsigned long)forward_raw *
                                             g_thresholds.swr2_fwd_full_scale_w) / 1023UL);
    unsigned int reflected_w = (unsigned int)(((unsigned long)reflected_raw *
                                               g_thresholds.swr2_fwd_full_scale_w) / 1023UL);
    unsigned int power_w = forward_w;

    if (g_thresholds.net_power_display && reflected_w < power_w) {
        power_w -= reflected_w;
    } else if (g_thresholds.net_power_display) {
        power_w = 0;
    }

    g_post_fwd_rms_w = (unsigned int)(((unsigned long)g_post_fwd_rms_w * 7UL + power_w) / 8UL);
    if (power_w >= g_post_fwd_pep_w) {
        g_post_fwd_pep_w = power_w;
        g_pep_decay_elapsed_ms = 0;
    }
}

void update_peak_decay(unsigned int *peak_value, unsigned int *elapsed_ms, unsigned int tick_ms) {
    unsigned int decay_step;
    unsigned int peak_hold_ms = g_thresholds.peak_hold_ms;
    unsigned int decay_interval_ms = g_thresholds.peak_decay_ms;

    *elapsed_ms += tick_ms;
    if (*elapsed_ms < peak_hold_ms) {
        return;
    }
    if (decay_interval_ms == 0) {
        decay_interval_ms = PEAK_DECAY_MIN_MS;
    }
    while (*elapsed_ms >= peak_hold_ms + decay_interval_ms && *peak_value > 0) {
        decay_step = *peak_value >> PEAK_DECAY_SHIFT;
        if (decay_step == 0) {
            decay_step = 1;
        }
        *peak_value = *peak_value > decay_step ? *peak_value - decay_step : 0;
        *elapsed_ms -= decay_interval_ms;
    }
    if (*peak_value == 0) {
        *elapsed_ms = peak_hold_ms;
    }
}

void update_current_peak(unsigned int current_a) {
    if (current_a >= g_current_peak_a) {
        g_current_peak_a = current_a;
        g_current_peak_decay_elapsed_ms = 0;
    }
}

void update_protection_state(unsigned int temp_c,
                            unsigned int overdrive_raw,
                            unsigned int drain_raw,
                            bool swr1_fault,
                            bool swr2_fault,
                            bool hw_fault,
                            bool current_fault) {
    bool temp_trip = temp_c >= g_thresholds.temp_trip_c;
    bool overdrive_trip = overdrive_raw >= (unsigned int)g_thresholds.overdrive_trip_tenths_w * 100U;
    bool drain_trip = drain_raw >= g_thresholds.drain_trip_v;
    /* The SWR bridges sit in the TX train, which the T/R relay only connects to the RF path
       while it is closed (sequencer stages 1-3 are exactly the stages that hold OUTPUT_TX
       asserted). During bypass the relay selection may legitimately be moving and any bridge
       reading is meaningless, so the SWR trips are only armed while TX is engaged. */
    bool swr_armed = (g_sequence_stage >= 1 && g_sequence_stage <= 3);
    bool any_trip_fault = (swr_armed && (swr1_fault || swr2_fault)) ||
                          hw_fault || current_fault ||
                          temp_trip || overdrive_trip || drain_trip;

    if (g_startup_inhibit) {
        g_state = STATE_RESET_WAIT;
        apply_bypass();
        return;
    }

    if (any_trip_fault) {
        g_trip_reason = (unsigned char)(
            (swr1_fault ? TRIP_REASON_SWR1 : 0) |
            (swr2_fault ? TRIP_REASON_SWR2 : 0) |
            (hw_fault ? TRIP_REASON_HWFAULT : 0) |
            (current_fault ? TRIP_REASON_CURRENT : 0) |
            (temp_trip ? TRIP_REASON_TEMP : 0) |
            (overdrive_trip ? TRIP_REASON_OVERDRIVE : 0) |
            (drain_trip ? TRIP_REASON_DRAIN : 0));
        if (!g_fault_latched) {
            g_fault_latched = true;
            g_ptt_complete_display_active = false;
            g_ptt_complete_display_elapsed_ms = 0;
            g_menu_changed = true;
            g_trip_shutdown_active = true;
            g_trip_shutdown_elapsed_ms = 0;
        }
        g_state = STATE_TRIP;
        set_trip_output(true);
        set_tx_vcc_output(false);
        if (!g_trip_shutdown_active) {
            set_tx_output(false);
            set_tx_bias_output(false);
        }
        return;
    }

    if (g_fault_latched) {
        if (g_trip_reason == TRIP_REASON_TEMP &&
            !any_trip_fault &&
            temp_c + TEMPERATURE_RECOVERY_HYSTERESIS_C < g_thresholds.temp_trip_c) {
            g_fault_latched = false;
            g_trip_reason = 0;
            g_trip_shutdown_active = false;
            g_trip_shutdown_elapsed_ms = 0;
            g_sequence_stage = 0;
            g_state = STATE_RESET_WAIT;
            set_trip_output(false);
            /* Recovery unlocks the band, so the relay selection becomes live again: put the
               amplifier in bypass before that can happen, and make it re-establish a band
               before it may key (with no RF the selection would follow the 160m default). */
            apply_bypass();
            invalidate_established_band();
            start_comparator_reset();
            return;
        }
        /* The condition itself cleared, but the latch persists until the next
           PTT re-arm edge explicitly clears it (see clear_fault_latches() in
           handle_ptt_transition()), so TRIP stays shown/TX stays inhibited. */
        g_state = STATE_TRIP;
        set_trip_output(true);
        set_tx_vcc_output(false);
        if (!g_trip_shutdown_active) {
            set_tx_output(false);
            set_tx_bias_output(false);
        }
        return;
    }

    /* The snoop flag, not the enumerated state, is authoritative: this function runs every
       pass and would otherwise overwrite STATE_BYPASS_SNOOP with STATE_OPERATE. */
    g_state = (g_snoop_active || g_unkeyable) ? STATE_BYPASS_SNOOP : STATE_OPERATE;
    set_trip_output(false);
}
