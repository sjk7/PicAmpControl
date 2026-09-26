#include <xc.h>
#include <stdbool.h>
#include "../include/state.h"
#include "../include/settings.h"

/* The single definition of every shared state global. One per symbol, HERE, and nowhere else -
   every other module declares them `extern` through state.h. The simulator harnesses read these
   by .sym address, so the names, the types and the single-definition discipline must not change;
   moving the definitions out of main.c does not change any of them. */

#define TX_ACTIVE_HIGH_DEFAULT false
#define TX_VCC_ACTIVE_HIGH_DEFAULT false
#define TX_BIAS_ACTIVE_HIGH_DEFAULT false
#define FAN_ACTIVE_HIGH_DEFAULT false
#define TRIP_ACTIVE_HIGH_DEFAULT false

volatile system_state_t g_state = STATE_STANDBY;
volatile bool g_fault_latched = false;
volatile unsigned char g_trip_reason = 0;
volatile bool g_trip_shutdown_active = false;
volatile unsigned char g_trip_shutdown_elapsed_ms = 0;
volatile bool g_ptt_active = false;
/* First-dit band memory (see docs/first-dit-band-detection.md). Declared volatile so the
   simulator/debugger can read and drive the cache state directly. */
volatile bool g_band_cache_valid = false;
volatile rf_band_t g_band_cache_band = BAND_UNKNOWN;
volatile bool g_snoop_active = false;
unsigned int g_band_cache_idle_ms = 0;
volatile bool g_band_settle_active = false;
unsigned int g_band_settle_elapsed_ms = 0;
volatile bool g_band_verify_active = false;
unsigned int g_band_verify_mismatch_ms = 0;
/* A band is "established" for the current transmission when it is backed by a real measurement
   or by the first-dit memory. This is what gates keying: with no RF the classifier reports its
   160m no-signal default, and the amplifier must never key on a band that was never measured. */
volatile bool g_band_established = false;
/* UNDEFINED/UNKEYABLE interlock: set when a keyed band lock lost its measurement. Read by the LCD
   so the bench sees why the amplifier is refusing to key, and cleared once a fresh decode exists. */
volatile bool g_unkeyable = false;
/* The longest-holding failing self-test check, in ms. Published for the simulator harnesses. */
unsigned int g_lock_loss_ms = 0;
/* The self-test's verdict for the CURRENT key-down (tx_selftest_run()). */
volatile bool g_selftest_failed = false;
volatile unsigned int g_selftest_reason = TX_SELFTEST_OK;
/* Consecutive-ms counters, one per check bit, indexed by bit position. */
unsigned int g_selftest_hold[TX_SELFTEST_CHECK_COUNT] = { 0 };
/* How long the current unkey has been unwinding, in ms: TX_SELFTEST_BIAS_PIN_STUCK_AFTER_TX's window. */
unsigned int g_selftest_unkey_ms = 0;

volatile bool g_startup_inhibit = true;
volatile bool g_comparator_reset_active = false;
volatile unsigned char g_comparator_reset_elapsed_ms = 0;
volatile menu_page_t g_menu_page = MENU_PAGE_POWER_TEMPERATURE;
volatile menu_page_t g_saved_user_menu_page = MENU_PAGE_POWER_TEMPERATURE;
ui_mode_t g_ui_mode = UI_MODE_HOME;
volatile bool g_transient_menu_display = false;
volatile bool g_boot_message_active = false;
volatile bool g_ptt_complete_display_active = false;
volatile unsigned int g_ptt_complete_display_elapsed_ms = 0;
volatile bool g_menu_changed = true;
unsigned int g_sequence_elapsed_ms = 0;
unsigned char g_sequence_stage = SEQ_IDLE;
/* Current stage as text. Refreshed once per main-loop pass so it can be used by the LCD debug
   read-out and read by the simulator harnesses. Initialised with a literal rather than
   SEQUENCE_STAGE_NAMES[SEQ_IDLE]: XC8 rejects a volatile pointer initialised from a ROM array
   element ("(712) can't generate code for this expression"). */
volatile const char *g_sequence_stage_text = "IDLE";
unsigned int g_post_fwd_rms_w = 0;
unsigned int g_post_fwd_pep_w = 0;
unsigned int g_swr1_live_hundredths = 100;
unsigned int g_swr2_live_hundredths = 100;
unsigned int g_live_temperature_c = 0;
unsigned int g_live_current_a = 0;
unsigned int g_current_peak_a = 0;
unsigned int g_live_overdrive_mw = 0;
unsigned int g_pep_decay_elapsed_ms = 0;
unsigned int g_current_peak_decay_elapsed_ms = 0;
unsigned int g_status_refresh_ms = 0;
unsigned int g_startup_elapsed_ms = 0;
volatile unsigned char g_timer_ticks_pending = 0;
menu_page_t g_lcd_drawn_page = MENU_PAGE_COUNT;
system_state_t g_lcd_drawn_state = STATE_RESET_WAIT;
unsigned char g_lcd_drawn_trip_reason = 0;
unsigned int g_menu_idle_ms = 0;
volatile bool g_settings_dirty = false;
unsigned int g_settings_save_delay_ms = 0;
volatile unsigned char g_adc_scan_index = 0;
volatile unsigned char g_adc_active_index = 0;
/* Defaults until the first real ADC scan completes for each channel: 0 (idle,
   no fault) for power/current/overdrive/drain, and a mid-scale ~2.5V reading
   for temp (raw 0 would otherwise map to a false 150C thermal trip). */
volatile unsigned int g_adc_samples[8] = {0, 0, 0, 0, 511, 0, 0, 0};

protection_thresholds_t g_thresholds = {
    30, 20,
    1500, 1500,
    1, 100,
    100,
    150,
    40,
    20, 20,
    TX_ACTIVE_HIGH_DEFAULT,
    TX_VCC_ACTIVE_HIGH_DEFAULT,
    TX_BIAS_ACTIVE_HIGH_DEFAULT,
    FAN_ACTIVE_HIGH_DEFAULT,
    TRIP_ACTIVE_HIGH_DEFAULT,
    true, false, PEAK_HOLD_DEFAULT_MS, PEAK_DECAY_DEFAULT_MS
};
