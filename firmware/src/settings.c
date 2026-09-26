#include <xc.h>
#include <stdbool.h>
#include "../include/pin_map.h"
#include "../include/settings.h"
#include "../include/state.h"
#include "../include/nvm.h"

/* Settings record persistence: a versioned, checksummed copy of g_thresholds plus the last menu
   page, round-tripped through the internal EEPROM (nvm.c). */

unsigned char settings_checksum(menu_page_t page, const protection_thresholds_t *settings) {
    const unsigned char *bytes = (const unsigned char *)settings;
    unsigned char checksum = (unsigned char)page;
    unsigned char index;

    for (index = 0; index < sizeof(protection_thresholds_t); index++) {
        checksum ^= bytes[index];
    }
    return checksum;
}

void load_settings(void) {
    unsigned char header[3];
    unsigned char checksum;
    protection_thresholds_t stored_settings;

    if (internal_eeprom_read(0, header, sizeof(header)) &&
        header[0] == SETTINGS_MAGIC &&
        header[1] == SETTINGS_VERSION &&
        header[2] < MENU_PAGE_COUNT &&
        internal_eeprom_read(sizeof(header), (unsigned char *)&stored_settings, sizeof(stored_settings)) &&
        internal_eeprom_read(sizeof(header) + sizeof(stored_settings), &checksum, 1) &&
        stored_settings.temp_b_profile < 3 &&
        checksum == settings_checksum((menu_page_t)header[2], &stored_settings)) {
        g_thresholds = stored_settings;
        g_menu_page = (menu_page_t)header[2];
        g_saved_user_menu_page = g_menu_page;
    } else {
        g_menu_page = MENU_PAGE_POWER_TEMPERATURE;
        g_saved_user_menu_page = MENU_PAGE_POWER_TEMPERATURE;
    }
}

void save_settings(void) {
    unsigned char record[sizeof(protection_thresholds_t) + 4];
    const unsigned char *settings_bytes = (const unsigned char *)&g_thresholds;
    unsigned char index;

    record[0] = SETTINGS_MAGIC;
    record[1] = SETTINGS_VERSION;
    record[2] = (unsigned char)g_saved_user_menu_page;
    for (index = 0; index < sizeof(protection_thresholds_t); index++) {
        record[index + 3] = settings_bytes[index];
    }
    record[sizeof(protection_thresholds_t) + 3] = settings_checksum(g_menu_page, &g_thresholds);
    internal_eeprom_write(0, record, sizeof(record));
}

void mark_settings_dirty(void) {
    g_settings_dirty = true;
    g_settings_save_delay_ms = 100;
}

void service_settings_save(void) {
    if (g_settings_dirty && g_settings_save_delay_ms == 0 &&
        !g_ptt_active && !g_fault_latched && INPUT_OVERCURRENT_FAULT == 0) {
        save_settings();
        g_settings_dirty = false;
    }
}
