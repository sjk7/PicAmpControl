#include <xc.h>
#include <stdbool.h>
#include "../include/pin_map.h"
#include "../include/settings.h"
#include "../include/state.h"
#include "../include/freq_counter.h"
#include "../include/outputs.h"

/* Output drives and the safety helpers around them. Every output is written through the LAT
   register (pin_map.h); the active-high polarity of each comes from g_thresholds. */

bool output_level(bool active, bool active_high) {
    return active_high ? active : !active;
}

void set_tx_output(bool active) {
    OUTPUT_TX = output_level(active, g_thresholds.tx_active_high);
}

void set_tx_vcc_output(bool active) {
    OUTPUT_TX_VCC = output_level(active, g_thresholds.tx_vcc_active_high);
}

void set_tx_bias_output(bool active) {
    OUTPUT_TX_BIAS = output_level(active, g_thresholds.tx_bias_active_high);
}

void set_fan_output(bool active) {
    OUTPUT_FAN_PWM = output_level(active, g_thresholds.fan_active_high);
}

void set_trip_output(bool active) {
    OUTPUT_TRIP_STATUS = output_level(active, g_thresholds.trip_active_high);
}

/* Safety invariant for band selection: the LPF relays must never move while the
   amplifier is keyed. Any code path that is about to let the relay selection change
   (restoring a remembered band, entering bypass-snoop, or following live RF) must put
   the amplifier in bypass first. Bypass is always safe: the RF path is straight
   through to the antenna and no LDMOS bias is applied. */
void apply_bypass(void) {
    set_tx_output(false);
    set_tx_vcc_output(false);
    set_tx_bias_output(false);
}

/* The band may only go back to following live RF once the amplifier is cold, otherwise
   the relays would move underneath a keyed amplifier. */
void release_band_if_cold(void) {
    /* SENSE_* reads the pin, not the latch: this confirmation must be about the hardware. */
    if (SENSE_TX == output_level(false, g_thresholds.tx_active_high) &&
        SENSE_TX_VCC == output_level(false, g_thresholds.tx_vcc_active_high) &&
        SENSE_TX_BIAS == output_level(false, g_thresholds.tx_bias_active_high)) {
        freq_counter_unlock_band();
    }
}

/* The relay selection is free to follow live RF again (a trip recovery, a PTT release), so the
   band is no longer established and the amplifier must establish one before it may key. */
void invalidate_established_band(void) {
    g_band_established = false;
}

void clear_fault_latches(void) {
    g_fault_latched = false;
    g_trip_reason = 0;
    g_trip_shutdown_active = false;
    g_trip_shutdown_elapsed_ms = 0;
    set_trip_output(false);
}

void start_comparator_reset(void) {
    OUTPUT_COMP_RESET = 0;
    g_comparator_reset_active = true;
    g_comparator_reset_elapsed_ms = 0;
}
