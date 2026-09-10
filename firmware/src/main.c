#include <xc.h>
#include <stdbool.h>
#include <stddef.h>
#include "../include/pin_map.h"
#include "../include/lcd_i2c.h"

#pragma config FOSC = HS
#pragma config WDTE = OFF
#pragma config PWRTE = OFF
#pragma config MCLRE = ON
#pragma config CP = OFF
#pragma config BOREN = ON
#pragma config BORV = 19
#pragma config PLLEN = OFF

typedef enum {
    STATE_STANDBY = 0,
    STATE_IDLE,
    STATE_OPERATE,
    STATE_WARNING,
    STATE_TRIP,
    STATE_FAULT_LATCHED,
    STATE_RESET_WAIT
} system_state_t;

typedef enum {
    MENU_PAGE_STATUS = 0,
    MENU_PAGE_POWER_TEMPERATURE,
    MENU_PAGE_SWR1_TRIP,
    MENU_PAGE_SWR2_TRIP,
    MENU_PAGE_SWR1_FWD_FULL_SCALE,
    MENU_PAGE_SWR2_FWD_FULL_SCALE,
    MENU_PAGE_TEMP_B_VALUE,
    MENU_PAGE_TEMP_WARNING,
    MENU_PAGE_TEMP_TRIP,
    MENU_PAGE_OVERDRIVE_WARNING,
    MENU_PAGE_OVERDRIVE_TRIP,
    MENU_PAGE_DRAIN_WARNING,
    MENU_PAGE_DRAIN_TRIP,
    MENU_PAGE_TX_VCC_DELAY,
    MENU_PAGE_TX_BIAS_DELAY,
    MENU_PAGE_TX_ACTIVE_HIGH,
    MENU_PAGE_TX_VCC_ACTIVE_HIGH,
    MENU_PAGE_TX_BIAS_ACTIVE_HIGH,
    MENU_PAGE_FAN_ACTIVE_HIGH,
    MENU_PAGE_WARNING_ACTIVE_HIGH,
    MENU_PAGE_TRIP_ACTIVE_HIGH,
    MENU_PAGE_POWER_DISPLAY_MODE,
    MENU_PAGE_PEP_DECAY_MS,
    MENU_PAGE_COUNT
} menu_page_t;

typedef struct {
    unsigned char swr1_trip_tenths;
    unsigned char swr2_trip_tenths;
    unsigned int swr1_fwd_full_scale_w;
    unsigned int swr2_fwd_full_scale_w;
    unsigned char temp_b_profile;
    unsigned int temp_warning_c;
    unsigned int temp_trip_c;
    unsigned char overdrive_warning_tenths_w;
    unsigned char overdrive_trip_tenths_w;
    unsigned int drain_warning_v;
    unsigned int drain_trip_v;
    unsigned int tx_vcc_delay_ms;
    unsigned int tx_bias_delay_ms;
    bool tx_active_high;
    bool tx_vcc_active_high;
    bool tx_bias_active_high;
    bool fan_active_high;
    bool warning_active_high;
    bool trip_active_high;
    bool power_display_pep;
    unsigned int pep_decay_ms;
} protection_thresholds_t;

#define SETTINGS_MAGIC 0xA5
#define SETTINGS_VERSION 2
#define MENU_SETTING_U8 0
#define MENU_SETTING_U16 1
#define MENU_SETTING_BOOL 2

static volatile system_state_t g_state = STATE_STANDBY;
static volatile bool g_fault_latched = false;
static volatile bool g_ptt_active = false;
static volatile bool g_startup_inhibit = true;
static volatile bool g_comparator_reset_active = false;
static volatile unsigned char g_comparator_reset_elapsed_ms = 0;
static volatile menu_page_t g_menu_page = MENU_PAGE_STATUS;
static volatile bool g_menu_changed = true;
static unsigned int g_sequence_elapsed_ms = 0;
static unsigned char g_sequence_stage = 0;
static unsigned int g_post_fwd_rms_w = 0;
static unsigned int g_post_fwd_pep_w = 0;
static unsigned int g_pep_decay_elapsed_ms = 0;
static unsigned int g_status_refresh_ms = 0;
static unsigned int g_startup_elapsed_ms = 0;
static volatile unsigned char g_timer_ticks_pending = 0;
static volatile bool g_settings_dirty = false;
static unsigned int g_settings_save_delay_ms = 0;
static volatile unsigned char g_adc_scan_index = 0;
static volatile unsigned int g_adc_swr1_fwd = 0;
static volatile unsigned int g_adc_swr1_ref = 0;
static volatile unsigned int g_adc_swr2_fwd = 0;
static volatile unsigned int g_adc_swr2_ref = 0;
static volatile unsigned int g_adc_temp = 0;
static volatile unsigned int g_adc_overdrive = 0;
static volatile unsigned int g_adc_drain = 0;
static unsigned int g_temperature_raw = 0;
static const unsigned char g_ntc_adc[3][16] = {
    {190, 166, 141, 116, 94, 75, 59, 46, 37, 29, 23, 19, 15, 12, 10, 8},
    {197, 171, 142, 114, 89, 68, 51, 38, 29, 22, 17, 13, 10, 8, 6, 5},
    {201, 174, 143, 113, 86, 64, 47, 34, 25, 19, 14, 11, 8, 6, 5, 4}
};
static const unsigned char g_adc_scan_channels[7] = {0, 1, 2, 3, 4, 7, 8};
static const unsigned char g_menu_setting_offsets[] = {
    offsetof(protection_thresholds_t, swr1_trip_tenths),
    offsetof(protection_thresholds_t, swr2_trip_tenths),
    offsetof(protection_thresholds_t, swr1_fwd_full_scale_w),
    offsetof(protection_thresholds_t, swr2_fwd_full_scale_w),
    offsetof(protection_thresholds_t, temp_b_profile),
    offsetof(protection_thresholds_t, temp_warning_c),
    offsetof(protection_thresholds_t, temp_trip_c),
    offsetof(protection_thresholds_t, overdrive_warning_tenths_w),
    offsetof(protection_thresholds_t, overdrive_trip_tenths_w),
    offsetof(protection_thresholds_t, drain_warning_v),
    offsetof(protection_thresholds_t, drain_trip_v),
    offsetof(protection_thresholds_t, tx_vcc_delay_ms),
    offsetof(protection_thresholds_t, tx_bias_delay_ms),
    offsetof(protection_thresholds_t, tx_active_high),
    offsetof(protection_thresholds_t, tx_vcc_active_high),
    offsetof(protection_thresholds_t, tx_bias_active_high),
    offsetof(protection_thresholds_t, fan_active_high),
    offsetof(protection_thresholds_t, warning_active_high),
    offsetof(protection_thresholds_t, trip_active_high),
    offsetof(protection_thresholds_t, power_display_pep),
    offsetof(protection_thresholds_t, pep_decay_ms)
};
static const unsigned char g_menu_setting_types[] = {
    MENU_SETTING_U8, MENU_SETTING_U8, MENU_SETTING_U16, MENU_SETTING_U16,
    MENU_SETTING_U8, MENU_SETTING_U16, MENU_SETTING_U16, MENU_SETTING_U8,
    MENU_SETTING_U8, MENU_SETTING_U16, MENU_SETTING_U16, MENU_SETTING_U16,
    MENU_SETTING_U16, MENU_SETTING_BOOL, MENU_SETTING_BOOL, MENU_SETTING_BOOL,
    MENU_SETTING_BOOL, MENU_SETTING_BOOL, MENU_SETTING_BOOL, MENU_SETTING_BOOL,
    MENU_SETTING_U16
};
static const char *const g_menu_labels[] = {
    "STATUS", "STATUS", "S1 SWR TRIP", "S2 SWR TRIP", "S1 FWD MAX", "S2 FWD MAX",
    "NTC B VALUE", "TEMP WARNING", "TEMP TRIP", "INPUT WARNING", "INPUT TRIP",
    "DRAIN WARNING", "DRAIN TRIP", "TX-VCC DELAY", "TX-BIAS DELAY", "TX ACTIVE",
    "TX-VCC ACTIVE", "TX-BIAS ACTIVE", "FAN ACTIVE", "WARN ACTIVE", "TRIP ACTIVE",
    "POWER DISPLAY", "PEP DECAY"
};
static protection_thresholds_t g_thresholds = {
    30, 20,
    1500, 1500,
    1, 70, 100,
    90, 100,
    140, 150,
    20, 20,
    false, false, false, false, false, false,
    true, 500
};

bool output_level(bool active, bool active_high) {
    return active == active_high;
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

void set_warning_output(bool active) {
    OUTPUT_WARNING_STATUS = output_level(active, g_thresholds.warning_active_high);
}

void set_trip_output(bool active) {
    OUTPUT_TRIP_STATUS = output_level(active, g_thresholds.trip_active_high);
}

void __interrupt() timer0_isr(void) {
    if (INTCONbits.T0IF != 0) {
        TMR0 = 100;
        INTCONbits.T0IF = 0;
        if (g_timer_ticks_pending != 255) {
            g_timer_ticks_pending++;
        }
    }

    if (PIR1bits.ADIF != 0) {
        unsigned int sample = (unsigned int)ADRES;
        PIR1bits.ADIF = 0;

        switch (g_adc_scan_index) {
            case 0: g_adc_swr1_fwd = sample; break;
            case 1: g_adc_swr1_ref = sample; break;
            case 2: g_adc_swr2_fwd = sample; break;
            case 3: g_adc_swr2_ref = sample; break;
            case 4: g_adc_temp = sample; break;
            case 5: g_adc_overdrive = sample; break;
            default: g_adc_drain = sample; break;
        }

        g_adc_scan_index++;
        if (g_adc_scan_index >= 7) {
            g_adc_scan_index = 0;
        }
        ADCON0 &= 0x03;
        ADCON0 |= (unsigned char)(g_adc_scan_channels[g_adc_scan_index] << 2);
        ADCON0bits.GO_DONE = 1;
    }

}

void timer0_init(void) {
    OPTION_REGbits.T0CS = 0;
    OPTION_REGbits.PSA = 0;
    OPTION_REGbits.PS = 0b100;
    TMR0 = 100;
    INTCONbits.T0IF = 0;
    INTCONbits.T0IE = 1;
    INTCONbits.GIE = 1;
}

unsigned int temperature_c(unsigned int raw);

void lcd_write_spaces(unsigned char count) {
    while (count > 0) {
        lcd_write_byte(' ', true);
        count--;
    }
}

void lcd_write_power_bar(unsigned int power_w, unsigned int full_scale_w, unsigned char width) {
    unsigned char bar_segment;
    unsigned char bar_segments = (unsigned char)(((unsigned long)power_w * width) / full_scale_w);

    if (bar_segments > width) {
        bar_segments = width;
    }

    for (bar_segment = 0; bar_segment < width; bar_segment++) {
        lcd_write_byte(bar_segment < bar_segments ? '-' : '.', true);
    }
}

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

    if (at24c256_read(0, header, sizeof(header)) &&
        header[0] == SETTINGS_MAGIC &&
        header[1] == SETTINGS_VERSION &&
        header[2] < MENU_PAGE_COUNT &&
        at24c256_read(sizeof(header), (unsigned char *)&stored_settings, sizeof(stored_settings)) &&
        at24c256_read(sizeof(header) + sizeof(stored_settings), &checksum, 1) &&
        stored_settings.temp_b_profile < 3 &&
        checksum == settings_checksum((menu_page_t)header[2], &stored_settings)) {
        g_thresholds = stored_settings;
        g_menu_page = (menu_page_t)header[2];
    } else {
        g_menu_page = MENU_PAGE_STATUS;
    }
}

void save_settings(void) {
    unsigned char record[sizeof(protection_thresholds_t) + 4];
    const unsigned char *settings_bytes = (const unsigned char *)&g_thresholds;
    unsigned char index;

    record[0] = SETTINGS_MAGIC;
    record[1] = SETTINGS_VERSION;
    record[2] = (unsigned char)g_menu_page;
    for (index = 0; index < sizeof(protection_thresholds_t); index++) {
        record[index + 3] = settings_bytes[index];
    }
    record[sizeof(protection_thresholds_t) + 3] = settings_checksum(g_menu_page, &g_thresholds);
    at24c256_write(0, record, sizeof(record));
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

void show_menu_page(void) {
    const char *label = g_menu_labels[g_menu_page];
    unsigned int value = 0;
    unsigned char setting_index;
    unsigned char *setting;

    if (g_menu_page >= MENU_PAGE_SWR1_TRIP) {
        setting_index = (unsigned char)(g_menu_page - MENU_PAGE_SWR1_TRIP);
        setting = (unsigned char *)&g_thresholds + g_menu_setting_offsets[setting_index];
        value = g_menu_setting_types[setting_index] == MENU_SETTING_U16 ? *(unsigned int *)setting : *setting;
        if (g_menu_page == MENU_PAGE_TEMP_B_VALUE) {
            value = value == 0 ? 3435 : (value == 1 ? 3950 : 4250);
        }
    }

    lcd_write_byte(0x01, false);
    __delay_ms(2);
    if (g_menu_page == MENU_PAGE_STATUS) {
        unsigned int power_w = g_thresholds.power_display_pep ? g_post_fwd_pep_w : g_post_fwd_rms_w;

        lcd_set_cursor(0, 0);
        lcd_write_text("P=");
        if (power_w < 1000) lcd_write_spaces(1);
        if (power_w < 100) lcd_write_spaces(1);
        if (power_w < 10) lcd_write_spaces(1);
        lcd_write_unsigned(power_w);
        lcd_write_byte('W', true);
        lcd_write_text(" SWR=");
        lcd_set_cursor(1, 0);
        lcd_write_power_bar(g_post_fwd_pep_w, g_thresholds.swr2_fwd_full_scale_w, 16);
        return;
    }
    if (g_menu_page == MENU_PAGE_POWER_TEMPERATURE) {
        lcd_set_cursor(0, 0);
        lcd_write_text("PEP ");
        lcd_write_power_bar(g_post_fwd_pep_w, g_thresholds.swr2_fwd_full_scale_w, 12);
        lcd_set_cursor(1, 0);
        lcd_write_text("TEMP ");
        lcd_write_unsigned(temperature_c(g_temperature_raw));
        lcd_write_byte('C', true);
        return;
    }
    lcd_set_cursor(0, 0);
    lcd_write_text(label);
    lcd_set_cursor(1, 0);
    if (g_menu_page == MENU_PAGE_SWR1_TRIP || g_menu_page == MENU_PAGE_SWR2_TRIP) {
        lcd_write_unsigned((unsigned int)(value / 10));
        lcd_write_byte('.', true);
        lcd_write_unsigned((unsigned int)(value % 10));
        lcd_write_text(":1");
    } else if (g_menu_page == MENU_PAGE_SWR1_FWD_FULL_SCALE ||
               g_menu_page == MENU_PAGE_SWR2_FWD_FULL_SCALE) {
        lcd_write_unsigned(value);
        lcd_write_byte('W', true);
    } else if (g_menu_page == MENU_PAGE_OVERDRIVE_WARNING || g_menu_page == MENU_PAGE_OVERDRIVE_TRIP) {
        lcd_write_unsigned((unsigned int)(value / 10));
        lcd_write_byte('.', true);
        lcd_write_unsigned((unsigned int)(value % 10));
        lcd_write_byte('W', true);
    } else if (g_menu_page == MENU_PAGE_TEMP_B_VALUE ||
               g_menu_page == MENU_PAGE_TEMP_WARNING ||
               g_menu_page == MENU_PAGE_TEMP_TRIP) {
        lcd_write_unsigned(value);
        lcd_write_byte('C', true);
    } else if (g_menu_page == MENU_PAGE_DRAIN_WARNING || g_menu_page == MENU_PAGE_DRAIN_TRIP) {
        lcd_write_unsigned(value);
        lcd_write_byte('V', true);
    } else if (g_menu_page == MENU_PAGE_TX_VCC_DELAY || g_menu_page == MENU_PAGE_TX_BIAS_DELAY) {
        lcd_write_unsigned(value);
        lcd_write_text("ms");
    } else if (g_menu_page == MENU_PAGE_PEP_DECAY_MS) {
        lcd_write_unsigned(value);
        lcd_write_text("ms");
    } else if (g_menu_page == MENU_PAGE_POWER_DISPLAY_MODE) {
        lcd_write_text(value != 0 ? "PEP" : "RMS");
    } else if (g_menu_page >= MENU_PAGE_TX_ACTIVE_HIGH) {
        lcd_write_text(value != 0 ? "HIGH" : "LOW");
    } else {
        lcd_write_unsigned(value);
    }
}

void adc_init(void) {
    FVRCON = 0x00;
    ANSELA = 0x2F;
    ANSELB = 0x0C;
    ADCON1 = 0x20;
    ADCON0 = 0x01;
    PIR1bits.ADIF = 0;
    PIE1bits.ADIE = 1;
    INTCONbits.PEIE = 1;
    ADCON0bits.GO_DONE = 1;
}

void apply_startup_inhibit(void) {
    set_tx_output(false);
    set_tx_vcc_output(false);
    set_tx_bias_output(false);
    set_fan_output(false);
    set_warning_output(false);
    set_trip_output(false);
    g_startup_inhibit = true;
}

void clear_fault_latches(void) {
    g_fault_latched = false;
    set_warning_output(false);
    set_trip_output(false);
}

void start_comparator_reset(void) {
    OUTPUT_COMP_RESET = 0;
    g_comparator_reset_active = true;
    g_comparator_reset_elapsed_ms = 0;
}

void handle_ptt_transition(bool ptt_asserted) {
    if (ptt_asserted) {
        g_ptt_active = true;
        start_comparator_reset();
        if (!g_fault_latched) {
            g_state = STATE_RESET_WAIT;
        }
        if (INPUT_OVERCURRENT_FAULT == 0) {
            clear_fault_latches();
            g_state = STATE_OPERATE;
        }
    } else {
        g_ptt_active = false;
        g_state = STATE_STANDBY;
    }
}

bool swr_trip(unsigned int forward_raw,
              unsigned int reflected_raw,
              unsigned int forward_full_scale_w,
              unsigned char limit_tenths) {
    unsigned long upper_factor;
    unsigned long lower_factor;
    unsigned int forward_power_w;
    unsigned int reflected_power_w;

    if (forward_raw < 10 || limit_tenths <= 10) {
        return false;
    }

    forward_power_w = (unsigned int)(((unsigned long)forward_raw * forward_full_scale_w) / 1023UL);
    reflected_power_w = (unsigned int)(((unsigned long)reflected_raw * forward_full_scale_w) / 1023UL);
    upper_factor = (unsigned long)(limit_tenths + 10) * (limit_tenths + 10);
    lower_factor = (unsigned long)(limit_tenths - 10) * (limit_tenths - 10);
    return (unsigned long)reflected_power_w * upper_factor >=
           (unsigned long)forward_power_w * lower_factor;
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

void adjust_selected_threshold(bool increase) {
    unsigned char setting_index;
    unsigned char *selected_u8;
    unsigned int *selected_u16;

    if (g_menu_page < MENU_PAGE_SWR1_TRIP || g_menu_page > MENU_PAGE_PEP_DECAY_MS) {
        return;
    }

    setting_index = (unsigned char)(g_menu_page - MENU_PAGE_SWR1_TRIP);
    selected_u8 = (unsigned char *)&g_thresholds + g_menu_setting_offsets[setting_index];
    if (g_menu_setting_types[setting_index] == MENU_SETTING_BOOL) {
        *selected_u8 = !*selected_u8;
        set_tx_output(false);
        set_tx_vcc_output(false);
        set_tx_bias_output(false);
        set_fan_output(false);
        set_warning_output(g_state == STATE_WARNING || g_state == STATE_TRIP);
        set_trip_output(g_state == STATE_TRIP);
        return;
    }

    if (g_menu_page == MENU_PAGE_TEMP_B_VALUE) {
        if (increase && *selected_u8 < 2) {
            *selected_u8 += 1;
        } else if (!increase && *selected_u8 > 0) {
            *selected_u8 -= 1;
        }
        return;
    }

    if (g_menu_setting_types[setting_index] == MENU_SETTING_U8) {
        if (g_menu_page == MENU_PAGE_SWR1_TRIP || g_menu_page == MENU_PAGE_SWR2_TRIP) {
            if (increase && *selected_u8 < 50) *selected_u8 += 1;
            else if (!increase && *selected_u8 > 11) *selected_u8 -= 1;
        } else if (increase && *selected_u8 < 100) {
            *selected_u8 += 1;
        } else if (!increase && *selected_u8 > 0) {
            *selected_u8 -= 1;
        }
        return;
    }

    selected_u16 = (unsigned int *)selected_u8;

    if (g_menu_page == MENU_PAGE_TEMP_WARNING ||
        g_menu_page == MENU_PAGE_TEMP_TRIP) {
        if (increase && *selected_u16 < 150) {
            *selected_u16 += 1;
        } else if (!increase && *selected_u16 > 0) {
            *selected_u16 -= 1;
        }
    } else if (g_menu_page == MENU_PAGE_PEP_DECAY_MS) {
        if (increase && *selected_u16 < 2000) {
            *selected_u16 += 50;
        } else if (!increase && *selected_u16 > 50) {
            *selected_u16 -= 50;
        }
    } else if (g_menu_page == MENU_PAGE_TX_VCC_DELAY || g_menu_page == MENU_PAGE_TX_BIAS_DELAY) {
        if (increase && *selected_u16 < 1000) {
            *selected_u16 += 5;
        } else if (!increase && *selected_u16 >= 5) {
            *selected_u16 -= 5;
        }
    } else if (g_menu_page == MENU_PAGE_SWR1_FWD_FULL_SCALE ||
        g_menu_page == MENU_PAGE_SWR2_FWD_FULL_SCALE) {
        if (increase && *selected_u16 < 2500) {
            *selected_u16 += 100;
        } else if (!increase && *selected_u16 > 500) {
            *selected_u16 -= 100;
        }
    } else if (g_menu_page == MENU_PAGE_DRAIN_WARNING || g_menu_page == MENU_PAGE_DRAIN_TRIP) {
        if (increase && *selected_u16 < 300) {
            *selected_u16 += 1;
        } else if (!increase && *selected_u16 > 0) {
            *selected_u16 -= 1;
        }
    } else if (increase && *selected_u16 < 1013) {
        *selected_u16 += 10;
    } else if (!increase && *selected_u16 > 10) {
        *selected_u16 -= 10;
    }
}

void update_post_filter_power(unsigned int raw) {
    unsigned int power_w = (unsigned int)(((unsigned long)raw * g_thresholds.swr2_fwd_full_scale_w) / 1023UL);

    g_post_fwd_rms_w = (unsigned int)(((unsigned long)g_post_fwd_rms_w * 7UL + power_w) / 8UL);
    if (power_w >= g_post_fwd_pep_w) {
        g_post_fwd_pep_w = power_w;
        g_pep_decay_elapsed_ms = 0;
    }
}

void update_power_decay(unsigned int elapsed_ms) {
    g_pep_decay_elapsed_ms += elapsed_ms;
    while (g_pep_decay_elapsed_ms >= g_thresholds.pep_decay_ms && g_post_fwd_pep_w > 0) {
        g_post_fwd_pep_w--;
        g_pep_decay_elapsed_ms -= g_thresholds.pep_decay_ms;
    }
}

void update_tx_sequence(void) {
    if (!g_ptt_active || g_startup_inhibit || g_fault_latched || g_comparator_reset_active) {
        set_tx_output(false);
        set_tx_vcc_output(false);
        set_tx_bias_output(false);
        g_sequence_stage = 0;
        return;
    }

    if (g_sequence_stage == 0) {
        set_tx_output(true);
        g_sequence_elapsed_ms = 0;
        g_sequence_stage = 1;
    } else if (g_sequence_stage == 1) {
        g_sequence_elapsed_ms++;
        if (g_sequence_elapsed_ms >= g_thresholds.tx_vcc_delay_ms) {
            set_tx_vcc_output(true);
            g_sequence_elapsed_ms = 0;
            g_sequence_stage = 2;
        }
    } else if (g_sequence_stage == 2) {
        g_sequence_elapsed_ms++;
        if (g_sequence_elapsed_ms >= g_thresholds.tx_bias_delay_ms) {
            set_tx_bias_output(true);
            g_sequence_stage = 3;
        }
    }
}

void poll_menu_inputs(void) {
    static bool next_was_pressed = false;
    static bool increase_was_pressed = false;
    static bool decrease_was_pressed = false;
    bool next_pressed = (INPUT_MENU_NEXT == 0);
    bool increase_pressed = (INPUT_MENU_INCREASE == 0);
    bool decrease_pressed = (INPUT_MENU_DECREASE == 0);

    if (!g_ptt_active) {
        if (next_pressed && !next_was_pressed) {
            g_menu_page = (menu_page_t)((g_menu_page + 1) % MENU_PAGE_COUNT);
            g_menu_changed = true;
            mark_settings_dirty();
        }
        if (increase_pressed && !increase_was_pressed) {
            adjust_selected_threshold(true);
            g_menu_changed = true;
            mark_settings_dirty();
        }
        if (decrease_pressed && !decrease_was_pressed) {
            adjust_selected_threshold(false);
            g_menu_changed = true;
            mark_settings_dirty();
        }
    }

    next_was_pressed = next_pressed;
    increase_was_pressed = increase_pressed;
    decrease_was_pressed = decrease_pressed;
}

void update_protection_state(unsigned int temp_c,
                            unsigned int overdrive_raw,
                            unsigned int drain_raw,
                            bool swr1_fault,
                            bool swr2_fault,
                            bool hard_fault) {
    bool any_trip_fault = swr1_fault || swr2_fault || hard_fault ||
                          (temp_c >= g_thresholds.temp_trip_c) ||
                          (overdrive_raw >= (unsigned int)g_thresholds.overdrive_trip_tenths_w * 100U) ||
                          (drain_raw >= g_thresholds.drain_trip_v);
    bool any_warning = (temp_c >= g_thresholds.temp_warning_c) ||
                       (overdrive_raw >= (unsigned int)g_thresholds.overdrive_warning_tenths_w * 100U) ||
                       (drain_raw >= g_thresholds.drain_warning_v);

    if (g_startup_inhibit) {
        g_state = STATE_RESET_WAIT;
        set_tx_output(false);
        set_tx_vcc_output(false);
        set_tx_bias_output(false);
        return;
    }

    if (any_trip_fault) {
        g_fault_latched = true;
        g_state = STATE_TRIP;
        set_trip_output(true);
        set_warning_output(true);
        set_tx_output(false);
        set_tx_vcc_output(false);
        set_tx_bias_output(false);
        return;
    }

    if (any_warning) {
        g_state = STATE_WARNING;
        set_warning_output(true);
    } else {
        g_state = STATE_OPERATE;
        set_warning_output(false);
        set_trip_output(false);
    }
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
    TRISAbits.TRISA0 = 1;
    TRISAbits.TRISA1 = 1;
    TRISAbits.TRISA2 = 1;
    TRISAbits.TRISA3 = 1;
    TRISAbits.TRISA5 = 1;
    TRISCbits.TRISC0 = 1;
    TRISCbits.TRISC1 = 0;
    TRISCbits.TRISC2 = 1;
    TRISCbits.TRISC3 = 1;
    TRISCbits.TRISC4 = 1;
    TRISCbits.TRISC5 = 0;
    TRISCbits.TRISC6 = 0;
    TRISCbits.TRISC7 = 0;

    TRISB = 0x1F;
    PORTB = 0x00;
    WPUB = 0x03;
    OPTION_REGbits.nRBPU = 0;

    set_tx_output(false);
    set_tx_vcc_output(false);
    set_tx_bias_output(false);
    set_fan_output(false);
    set_warning_output(false);
    set_trip_output(false);
    OUTPUT_COMP_RESET = 1;

    adc_init();
    load_settings();
    lcd_init();
    timer0_init();
    show_menu_page();
    apply_startup_inhibit();

    while (1) {
        swr1_fwd_raw = g_adc_swr1_fwd;
        swr1_ref_raw = g_adc_swr1_ref;
        swr2_fwd_raw = g_adc_swr2_fwd;
        swr2_ref_raw = g_adc_swr2_ref;
        temp_raw = g_adc_temp;
        g_temperature_raw = temp_raw;
        temp_c = temperature_c(temp_raw);
        overdrive_raw = g_adc_overdrive;
        drain_raw = g_adc_drain;
        overdrive_power = overdrive_power_mw(overdrive_raw);
        drain_voltage_v = drain_voltage(drain_raw);
        update_post_filter_power(swr2_fwd_raw);

        bool swr1_fault = swr_trip(swr1_fwd_raw, swr1_ref_raw,
                       g_thresholds.swr1_fwd_full_scale_w,
                       g_thresholds.swr1_trip_tenths);
        bool swr2_fault = swr_trip(swr2_fwd_raw, swr2_ref_raw,
                       g_thresholds.swr2_fwd_full_scale_w,
                       g_thresholds.swr2_trip_tenths);
        bool hard_fault = (INPUT_OVERCURRENT_FAULT == 1);

        if ((INPUT_PTT == 0) != g_ptt_active) {
            handle_ptt_transition(INPUT_PTT == 0);
        }

        update_protection_state(temp_c, overdrive_power, drain_voltage_v,
                                swr1_fault,
                                swr2_fault,
                                hard_fault);

        while (g_timer_ticks_pending != 0) {
            g_timer_ticks_pending--;
            if (g_comparator_reset_active) {
                g_comparator_reset_elapsed_ms++;
                if (g_comparator_reset_elapsed_ms >= 10) {
                    OUTPUT_COMP_RESET = 1;
                    g_comparator_reset_active = false;
                }
            }
            if (g_startup_inhibit) {
                g_startup_elapsed_ms++;
                if (g_startup_elapsed_ms >= 1000) {
                    g_startup_inhibit = false;
                }
            } else {
                update_power_decay(1);
                update_tx_sequence();
            }
            if (g_settings_save_delay_ms > 0) {
                g_settings_save_delay_ms--;
            }
            g_status_refresh_ms++;
        }

        poll_menu_inputs();

        if (g_menu_page == MENU_PAGE_STATUS || g_menu_page == MENU_PAGE_POWER_TEMPERATURE) {
            if (g_status_refresh_ms >= 100 || g_menu_changed) {
                show_menu_page();
                g_status_refresh_ms = 0;
                g_menu_changed = false;
            }
        } else if (g_menu_changed) {
            show_menu_page();
            g_menu_changed = false;
        }

        service_settings_save();
    }
}
