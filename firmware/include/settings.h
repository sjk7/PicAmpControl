#ifndef SETTINGS_H
#define SETTINGS_H

#include <stdbool.h>
#include "state.h"

/* User-configurable protection thresholds and display options. The single instance is
   `g_thresholds` (defined in main.c); the menu edits it in place and it round-trips through the
   versioned, checksummed EEPROM settings record (settings.c load_settings/save_settings). */
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

#define SETTINGS_MAGIC 0xA5
#define SETTINGS_VERSION 9

/* Settings record load/save/checksum/dirty/service (settings.c). */
unsigned char settings_checksum(menu_page_t page, const protection_thresholds_t *settings);
void load_settings(void);
void save_settings(void);
void mark_settings_dirty(void);
void service_settings_save(void);

#endif
