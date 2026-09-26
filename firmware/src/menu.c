#include <xc.h>
#include <stdbool.h>
#include <stddef.h>
#include "../include/pin_map.h"
#include "../include/settings.h"
#include "../include/state.h"
#include "../include/outputs.h"
#include "../include/lcd_parallel.h"
#include "../include/lcd_format.h"
#include "../include/labels.h"
#include "../include/freq_counter.h"
#include "../include/self_test.h"
#include "../include/tx_selftest.h"
#include "../include/protection.h"
#include "../include/menu.h"

/* LCD menu and encoder UI. The page rendering (show_menu_page), the boot message, and the
   encoder/page/step handlers, all in one module so the per-page label/format tables stay beside
   their one consumer. */

#define MENU_SETTING_U8 0
#define MENU_SETTING_U16 1
#define MENU_SETTING_BOOL 2

static const unsigned char g_menu_setting_offsets[] = {
    offsetof(protection_thresholds_t, swr1_trip_tenths),
    offsetof(protection_thresholds_t, swr2_trip_tenths),
    offsetof(protection_thresholds_t, swr1_fwd_full_scale_w),
    offsetof(protection_thresholds_t, swr2_fwd_full_scale_w),
    offsetof(protection_thresholds_t, temp_b_profile),
    offsetof(protection_thresholds_t, temp_trip_c),
    offsetof(protection_thresholds_t, overdrive_trip_tenths_w),
    offsetof(protection_thresholds_t, drain_trip_v),
    offsetof(protection_thresholds_t, current_trip_a),
    offsetof(protection_thresholds_t, tx_vcc_delay_ms),
    offsetof(protection_thresholds_t, tx_bias_delay_ms),
    offsetof(protection_thresholds_t, tx_active_high),
    offsetof(protection_thresholds_t, tx_vcc_active_high),
    offsetof(protection_thresholds_t, tx_bias_active_high),
    offsetof(protection_thresholds_t, fan_active_high),
    offsetof(protection_thresholds_t, trip_active_high),
    offsetof(protection_thresholds_t, power_display_pep),
    offsetof(protection_thresholds_t, net_power_display),
    offsetof(protection_thresholds_t, peak_hold_ms),
    offsetof(protection_thresholds_t, peak_decay_ms)
};
static const unsigned char g_menu_setting_types[] = {
    MENU_SETTING_U8, MENU_SETTING_U8, MENU_SETTING_U16, MENU_SETTING_U16,
    MENU_SETTING_U8, MENU_SETTING_U16, MENU_SETTING_U8, MENU_SETTING_U16,
    MENU_SETTING_U16, MENU_SETTING_U16, MENU_SETTING_U16, MENU_SETTING_BOOL,
    MENU_SETTING_BOOL, MENU_SETTING_BOOL, MENU_SETTING_BOOL, MENU_SETTING_BOOL,
    MENU_SETTING_BOOL, MENU_SETTING_BOOL, MENU_SETTING_U16, MENU_SETTING_U16
};

/* Labels are kept as short as clarity allows: string literals live in STRCODE, which is the
   class the linker fails to place first, so every character here is flash. */
static const char *const g_setting_menu_labels[] = {
    "SWR1 TRIP", "SWR2 TRIP", "SWR1 FWD", "SWR2 FWD",
    "NTC B", "TEMP TRIP", "INPUT TRIP", "DRAIN TRIP", "CURR TRIP",
    "TX-VCC DLY", "TX-BIAS DLY", "TX ACTIVE",
    "TX-VCC POL", "TX-BIAS POL", "FAN POL", "TRIP POL",
    "POWER MODE", "NET POWER", "PK HOLD", "PK DECAY"
};

/* XC8 does not merge duplicate string literals, so the few that appear on more than one
   screen are defined once here instead of being repeated at each call site. */
static const char LCD_TEXT_SWR1[] = "SWR1 ";
static const char LCD_TEXT_SWR2[] = "SWR2 ";
static const char LCD_TEXT_MAX[] = "MAX ";
static const char LCD_TEXT_TEMP[] = "TEMP ";

void show_menu_page(void) {
    const char *label = "";
    unsigned int value = 0;
    unsigned char setting_index;
    unsigned char *setting;
    bool screen_changed = (g_menu_page != g_lcd_drawn_page) ||
                          (g_state != g_lcd_drawn_state) ||
                          (g_state == STATE_TRIP && g_trip_reason != g_lcd_drawn_trip_reason) ||
                          g_ptt_complete_display_active;

    if (g_menu_page >= MENU_PAGE_SWR1_TRIP) {
        setting_index = (unsigned char)(g_menu_page - MENU_PAGE_SWR1_TRIP);
        label = g_setting_menu_labels[setting_index];
        setting = (unsigned char *)&g_thresholds + g_menu_setting_offsets[setting_index];
        value = g_menu_setting_types[setting_index] == MENU_SETTING_U16 ? *(unsigned int *)setting : *setting;
        if (g_menu_page == MENU_PAGE_TEMP_B_VALUE) {
            value = value == 0 ? 3435 : (value == 1 ? 3950 : 4250);
        }
    }

    /* Every page redraws its fixed-width fields in place on each call, and the
       trip screen's text never changes while latched, so the display only needs
       a hard clear when the screen identity actually changes; this avoids a
       visible blank-flash on every periodic status update, trip redraw, or
       rapid-repeat adjustment of a setting. */
    if (screen_changed) {
        lcd_service(255); /* flush any bytes still queued from the previous page first */
        lcd_write_byte_now(0x01, false);
        __delay_ms(2);
    }
    g_lcd_drawn_page = g_menu_page;
    g_lcd_drawn_state = g_state;
    g_lcd_drawn_trip_reason = g_trip_reason;

    if (g_state == STATE_TRIP) {
        if (!screen_changed) {
            return;
        }
        /* Line 0 ALWAYS carries the enumerated fault name, and line 1 carries the evidence that
           produced it. On the bench, with no harness attached, the LCD is the only read-out there
           is, so no trip may ever leave a blank or unnamed screen - and the NAME must be the
           enumerator itself, not a hint, or a reader cannot tell which protection operated. */
        lcd_set_cursor(0, 0);
        lcd_write_text(trip_reason_name(g_trip_reason));
        lcd_set_cursor(1, 0);
        if (g_trip_reason & TRIP_REASON_TEMP) {
            lcd_write_unsigned(g_live_temperature_c);
            lcd_write_byte('/', true);
            lcd_write_unsigned(g_thresholds.temp_trip_c);
            lcd_write_byte('C', true);
        } else if (g_trip_reason & TRIP_REASON_SWR1) {
            if (g_swr1_live_hundredths >= 1000) {
                lcd_write_text("CHECK LPF");
            } else {
                lcd_write_swr_value(g_swr1_live_hundredths);
                lcd_write_byte('/', true);
                lcd_write_swr_value((unsigned int)g_thresholds.swr1_trip_tenths * 10U);
                lcd_write_text(":1");
            }
        } else if (g_trip_reason & TRIP_REASON_SWR2) {
            lcd_write_swr_value(g_swr2_live_hundredths);
            lcd_write_byte('/', true);
            lcd_write_swr_value((unsigned int)g_thresholds.swr2_trip_tenths * 10U);
            lcd_write_text(":1");
        } else if (g_trip_reason & TRIP_REASON_CURRENT) {
            lcd_write_unsigned(g_live_current_a);
            lcd_write_byte('/', true);
            lcd_write_unsigned(g_thresholds.current_trip_a);
            lcd_write_byte('A', true);
        } else if (g_trip_reason & TRIP_REASON_OVERDRIVE) {
            lcd_write_unsigned(g_live_overdrive_mw / 1000U);
            lcd_write_byte('/', true);
            lcd_write_unsigned((unsigned int)g_thresholds.overdrive_trip_tenths_w / 10U);
            lcd_write_byte('W', true);
        } else {
            /* HARDWARE, DRAIN, any combination the chain above does not name, or a zero mask:
               the name is on line 0, so line 1 states the latch instead of leaving a blank screen. */
            lcd_write_text("TRIP LATCHED");
        }
        return;
    }
    if (g_unkeyable || g_selftest_failed) {
        /* A FAULT RECORD IS ALWAYS ON THE PANEL. Line 0 reads FAULT:, never a PWR/SWR page; line 1 is
           the self-test's OWN reason, '+' when more than one check failed, and never blank. Cleared
           at the next key-down, so the reason can still be read after the amplifier has recovered. */
        static char selftest_reason_text[17];
        lcd_set_cursor(0, 0);
        lcd_write_text("FAULT:");
        lcd_set_cursor(1, 0);
        tx_selftest_reason_text(g_selftest_reason, selftest_reason_text, sizeof selftest_reason_text);
        lcd_write_text(selftest_reason_text);
        return;
    }
    if (g_ptt_complete_display_active) {
        lcd_set_cursor(0, 0);
        lcd_write_text("PTT COMPLETE");
        lcd_set_cursor(1, 0);
        /* The stage name, not a bare "TX ACTIVE": if the sequence ever fails to sit in BIAS-ON
           while keyed, the panel says which stage it is actually in. */
        lcd_write_text("TX ");
        lcd_write_text(sequence_stage_name(g_sequence_stage));
        return;
    }
    if (g_ptt_active) {
        /* Keyed but not yet complete: name the stage being executed, so a sequence that stalls on
           the bench (never reaching BIAS-ON, or sitting in a UNKEY stage after release) is read off
           the panel with no harness attached. Refreshed by the 100 ms live-page redraw. */
        freq_counter_status_t fc;
        freq_counter_get_status(&fc);
        lcd_set_cursor(0, 0);
        lcd_write_text("TX ");
        lcd_write_text(sequence_stage_name(g_sequence_stage));
        lcd_set_cursor(1, 0);
        lcd_write_text(band_name(fc.current_band));
        lcd_write_byte(' ', true);
        lcd_write_unsigned(fc.frequency_khz);
        lcd_write_text("kHz");
        return;
    }
    if (g_menu_page == MENU_PAGE_STATUS) {
        unsigned int power_w = g_thresholds.power_display_pep ? g_post_fwd_pep_w : g_post_fwd_rms_w;

        lcd_set_cursor(0, 0);
        lcd_write_text(g_thresholds.power_display_pep ? "P=" : "R=");
        if (power_w < 1000) lcd_write_spaces(1);
        if (power_w < 100) lcd_write_spaces(1);
        if (power_w < 10) lcd_write_spaces(1);
        lcd_write_unsigned(power_w);
        lcd_write_byte('W', true);
        lcd_write_swr_right(9, g_swr2_live_hundredths);
        lcd_set_cursor(1, 0);
        if (g_sequence_stage != SEQ_IDLE) {
            /* Unkeyed but not idle: the release never finished, so show which stage it is stuck in
               instead of the power bar. */
            lcd_write_text("SEQ ");
            lcd_write_text(sequence_stage_name(g_sequence_stage));
        } else {
            lcd_write_power_bar(power_w, g_thresholds.swr2_fwd_full_scale_w, 16);
        }
        return;
    }
    if (g_menu_page == MENU_PAGE_POWER_TEMPERATURE) {
        unsigned int temp_c_value = temperature_c(ADC_SAMPLE_TEMP);

        lcd_set_cursor(0, 0);
        lcd_write_text("P=");
        lcd_write_unsigned_padded(g_post_fwd_pep_w, 4);
        lcd_write_text("W ");
        lcd_write_power_bar(g_post_fwd_pep_w, g_thresholds.swr2_fwd_full_scale_w, 8);
        lcd_set_cursor(1, 0);
        lcd_write_text(LCD_TEXT_TEMP);
        if (temp_c_value < 100) lcd_write_spaces(1);
        if (temp_c_value < 10) lcd_write_spaces(1);
        lcd_write_unsigned(temp_c_value);
        lcd_write_byte('C', true);
        return;
    }
    if (g_menu_page == MENU_PAGE_SWR_METER) {
        lcd_set_cursor(0, 0);
        lcd_write_text(LCD_TEXT_SWR1);
        lcd_write_swr_right(11, g_swr1_live_hundredths);
        lcd_set_cursor(1, 0);
        lcd_write_text(LCD_TEXT_SWR2);
        lcd_write_swr_right(11, g_swr2_live_hundredths);
        return;
    }
    if (g_menu_page == MENU_PAGE_CURRENT_METER) {
        lcd_set_cursor(0, 0);
        lcd_write_text("A=");
        lcd_write_unsigned_padded(g_live_current_a, 3);
        lcd_write_text("A PK=");
        lcd_write_unsigned_padded(g_current_peak_a, 3);
        lcd_write_byte('A', true);
        lcd_write_spaces(2);
        lcd_set_cursor(1, 0);
        lcd_write_power_bar(g_current_peak_a, g_thresholds.current_trip_a, 16);
        return;
    }
    if (g_menu_page == MENU_PAGE_SELF_TEST) {
        /* The diagnostic screen: line 0 names the page and the selected check(s) (rotate to pick
           ALL or one check, press to run); line 1 shows RUNNING, the pending selection, or PASS /
           the '+' joined names of every failed check. */
        static char diag_text[17];
        lcd_set_cursor(0, 0);
        lcd_write_text("SELF TEST ");
        lcd_write_text(diag_selected_name());
        lcd_set_cursor(1, 0);
        if (diag_busy()) {
            lcd_write_text("RUNNING...");
        } else if (!diag_done()) {
            lcd_write_text("PRESS TO RUN");
        } else if (diag_result() == DIAG_OK) {
            lcd_write_text("PASS");
        } else {
            unsigned char used = 0;
            unsigned char i;
            diag_text[0] = '\0';
            for (i = 0; i < DIAG_CHECK_COUNT; i++) {
                if (diag_result() & (unsigned char)(1u << i)) {
                    const char *name = diag_check_name(i);
                    if (used != 0 && used + 1 < sizeof diag_text) diag_text[used++] = '+';
                    while (*name && used + 1 < sizeof diag_text) diag_text[used++] = *name++;
                }
            }
            diag_text[used] = '\0';
            lcd_write_text(diag_text);
            lcd_write_spaces(16 - used);
        }
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
        lcd_write_unsigned_padded(value, 4);
        lcd_write_byte('W', true);
    } else if (g_menu_page == MENU_PAGE_OVERDRIVE_TRIP) {
        lcd_write_unsigned_padded((unsigned int)(value / 10), 2);
        lcd_write_byte('.', true);
        lcd_write_unsigned((unsigned int)(value % 10));
        lcd_write_byte('W', true);
    } else if (g_menu_page == MENU_PAGE_TEMP_B_VALUE ||
               g_menu_page == MENU_PAGE_TEMP_TRIP) {
        lcd_write_unsigned_padded(value, g_menu_page == MENU_PAGE_TEMP_TRIP ? 3 : 4);
        lcd_write_byte('C', true);
    } else if (g_menu_page == MENU_PAGE_DRAIN_TRIP) {
        lcd_write_unsigned_padded(value, 3);
        lcd_write_byte('V', true);
    } else if (g_menu_page == MENU_PAGE_CURRENT_TRIP) {
        lcd_write_unsigned_padded(value, 3);
        lcd_write_byte('A', true);
    } else if (g_menu_page == MENU_PAGE_TX_VCC_DELAY || g_menu_page == MENU_PAGE_TX_BIAS_DELAY) {
        lcd_write_unsigned_padded(value, 4);
        lcd_write_text("ms");
    } else if (g_menu_page == MENU_PAGE_PEAK_HOLD_MS || g_menu_page == MENU_PAGE_PEAK_DECAY_MS) {
        lcd_write_unsigned_padded(value, 4);
        lcd_write_text("ms");
    } else if (g_menu_page == MENU_PAGE_POWER_DISPLAY_MODE) {
        lcd_write_text(value != 0 ? "PEP" : "RMS");
    } else if (g_menu_page == MENU_PAGE_NET_POWER) {
        lcd_write_text(value != 0 ? "NET" : "FWD");
    } else if (g_menu_page >= MENU_PAGE_TX_ACTIVE_HIGH) {
        lcd_write_text(value != 0 ? "HIGH" : "LOW ");
    } else {
        lcd_write_unsigned(value);
    }
}

void show_boot_message(void) {
    lcd_write_byte_now(0x01, false);
    __delay_ms(2);
    lcd_set_cursor(0, 0);
    lcd_write_text("Booting");
}

bool is_live_menu_page(menu_page_t page) {
    return page < MENU_PAGE_SWR1_TRIP;
}

static void step_home_page(bool clockwise) {
    if (clockwise) {
        g_menu_page = (menu_page_t)(g_menu_page + 1);
        if (!is_live_menu_page(g_menu_page)) {
            g_menu_page = MENU_PAGE_STATUS;
        }
    } else if (g_menu_page == MENU_PAGE_STATUS) {
        g_menu_page = MENU_PAGE_SELF_TEST;
    } else {
        g_menu_page = (menu_page_t)(g_menu_page - 1);
    }

    g_saved_user_menu_page = g_menu_page;
    g_menu_changed = true;
    mark_settings_dirty();
}

static void step_settings_page(void) {
    if (g_menu_page < MENU_PAGE_SWR1_TRIP || g_menu_page >= MENU_PAGE_PEAK_DECAY_MS) {
        g_menu_page = MENU_PAGE_SWR1_TRIP;
    } else {
        g_menu_page = (menu_page_t)(g_menu_page + 1);
    }
    g_menu_changed = true;
}

static void enter_settings(void) {
    if (!g_ptt_active) {
        g_ui_mode = UI_MODE_SETTINGS;
        g_menu_page = MENU_PAGE_SWR1_TRIP;
        g_menu_changed = true;
    }
}

static void exit_settings(void) {
    g_ui_mode = UI_MODE_HOME;
    g_menu_page = g_saved_user_menu_page;
    g_menu_changed = true;
    mark_settings_dirty();
}

static void adjust_selected_setting(bool increase) {
    unsigned char setting_index;
    unsigned char *selected_u8;
    unsigned int *selected_u16;

    if (g_menu_page < MENU_PAGE_SWR1_TRIP || g_menu_page > MENU_PAGE_PEAK_DECAY_MS) {
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

    if (g_menu_page == MENU_PAGE_CURRENT_TRIP) {
        if (increase && *selected_u16 < 100) {
            *selected_u16 += 1;
        } else if (!increase && *selected_u16 > 0) {
            *selected_u16 -= 1;
        }
    } else if (g_menu_page == MENU_PAGE_TEMP_TRIP) {
        if (increase && *selected_u16 < 150) {
            *selected_u16 += 1;
        } else if (!increase && *selected_u16 > 0) {
            *selected_u16 -= 1;
        }
    } else if (g_menu_page == MENU_PAGE_PEAK_HOLD_MS) {
        if (increase && *selected_u16 < 5000) {
            *selected_u16 += 100;
        } else if (!increase && *selected_u16 > 200) {
            *selected_u16 -= 100;
        }
    } else if (g_menu_page == MENU_PAGE_PEAK_DECAY_MS) {
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
    } else if (g_menu_page == MENU_PAGE_DRAIN_TRIP) {
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

static void handle_encoder_rotation(bool clockwise) {
    if (g_state == STATE_TRIP || g_transient_menu_display) {
        return;
    }
    if (g_ui_mode == UI_MODE_SETTINGS) {
        if (!g_ptt_active) {
            adjust_selected_setting(clockwise);
            g_menu_changed = true;
            mark_settings_dirty();
        }
    } else if (g_menu_page == MENU_PAGE_SELF_TEST) {
        /* Rotate picks which check(s) the next press runs (ALL or one), while the diagnostic is
           idle. It must not change the selection mid-run. */
        if (!diag_busy()) {
            diag_select_cycle();
            g_menu_changed = true;
        }
    } else if (is_live_menu_page(g_menu_page)) {
        step_home_page(clockwise);
    }
}

static void handle_encoder_short_press(void) {
    if (g_state == STATE_TRIP || g_transient_menu_display) {
        return;
    }
    if (g_ui_mode == UI_MODE_SETTINGS) {
        step_settings_page();
    } else if (g_menu_page == MENU_PAGE_SELF_TEST) {
        diag_start();
    } else {
        enter_settings();
    }
}

static void handle_encoder_long_press(void) {
    if (g_state == STATE_TRIP) {
        clear_fault_latches();
        g_ui_mode = UI_MODE_HOME;
        g_menu_page = g_saved_user_menu_page;
        g_menu_changed = true;
    } else if (g_ui_mode == UI_MODE_SETTINGS) {
        exit_settings();
    } else if (is_live_menu_page(g_menu_page)) {
        g_saved_user_menu_page = g_menu_page;
        g_menu_changed = true;
        mark_settings_dirty();
    }
}

void poll_menu_inputs(unsigned int elapsed_ms) {
    static bool button_was_pressed = false;
    static bool long_press_reported = false;
    static bool encoder_a_was_high = true;
    static unsigned int encoder_rotation_lockout_ms = 0;
    static unsigned int button_hold_ms = 0;
    bool button_pressed = (INPUT_ENCODER_SWITCH == 0);
    bool encoder_a_high = (INPUT_ENCODER_A != 0);
    bool user_activity = false;

    if (encoder_rotation_lockout_ms > elapsed_ms) {
        encoder_rotation_lockout_ms -= elapsed_ms;
    } else {
        encoder_rotation_lockout_ms = 0;
    }

    if (encoder_rotation_lockout_ms == 0 && encoder_a_was_high && !encoder_a_high) {
        handle_encoder_rotation(INPUT_ENCODER_B != 0);
        encoder_rotation_lockout_ms = ENCODER_ROTATION_LOCKOUT_MS;
        user_activity = true;
    }
    encoder_a_was_high = encoder_a_high;

    if (button_pressed) {
        button_hold_ms += elapsed_ms;
        if (!long_press_reported &&
            button_hold_ms >= (g_state == STATE_TRIP ? ENCODER_FAULT_CLEAR_MS : ENCODER_LONG_PRESS_MS)) {
            handle_encoder_long_press();
            long_press_reported = true;
            user_activity = true;
        }
    } else {
        if (button_was_pressed && !long_press_reported) {
            handle_encoder_short_press();
            user_activity = true;
        }
        button_hold_ms = 0;
        long_press_reported = false;
    }
    button_was_pressed = button_pressed;

    if (user_activity) {
        g_menu_idle_ms = 0;
    } else if (g_ui_mode == UI_MODE_SETTINGS) {
        g_menu_idle_ms += elapsed_ms;
        if (g_menu_idle_ms >= MENU_IDLE_TIMEOUT_MS) {
            exit_settings();
            g_menu_idle_ms = 0;
        }
    } else {
        g_menu_idle_ms = 0;
    }
}
