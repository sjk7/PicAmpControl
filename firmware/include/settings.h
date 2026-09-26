#ifndef SETTINGS_H
#define SETTINGS_H

#include <stdbool.h>

/* User-configurable protection thresholds and display options. The single instance is
   `g_thresholds` (defined in main.c); the menu edits it in place and it round-trips through the
   versioned, checksummed EEPROM settings record (see main.c load_settings/save_settings). */
typedef struct {
    unsigned char swr1_trip_tenths;
    unsigned char swr2_trip_tenths;
    unsigned int swr1_fwd_full_scale_w;
    unsigned int swr2_fwd_full_scale_w;
    unsigned char temp_b_profile;
    unsigned int temp_trip_c;
    unsigned char overdrive_trip_tenths_w;
    unsigned int drain_trip_v;
    unsigned int current_trip_a;
    unsigned int tx_vcc_delay_ms;
    unsigned int tx_bias_delay_ms;
    bool tx_active_high;
    bool tx_vcc_active_high;
    bool tx_bias_active_high;
    bool fan_active_high;
    bool trip_active_high;
    bool power_display_pep;
    bool net_power_display;
    unsigned int peak_hold_ms;
    unsigned int peak_decay_ms;
} protection_thresholds_t;

extern protection_thresholds_t g_thresholds;

#endif
