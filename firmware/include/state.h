#ifndef STATE_H
#define STATE_H

#include <stdbool.h>
#include "freq_counter.h"

/* Shared system state: the enums, the shared constants, and the `extern` declarations for the
   volatile state globals. The globals are DEFINED once, in main.c, and only there - the simulator
   harnesses read them by .sym address and depend on their names and layout, so a second definition
   in another translation unit would be a duplicate-symbol error and a rename would break the suite.
   Every other module declares them here and uses them through these externs.

   The enums and name tables split across modules:
     - the enums live here (state.h) because more than one module needs them;
     - each name table + its `_name()` accessor lives beside its consumer in labels.c / tx_selftest.c. */

typedef enum {
    STATE_STANDBY = 0,
    STATE_IDLE,
    STATE_OPERATE,
    STATE_TRIP,
    STATE_FAULT_LATCHED,
    STATE_RESET_WAIT,
    /* First-dit bypass snoop: PTT is latched but the amplifier stays in bypass (all TX
       outputs inactive) until the radio's first RF burst decodes a usable band.
       Appended last so the existing state numbering stays stable. */
    STATE_BYPASS_SNOOP
} system_state_t;

typedef enum {
    UI_MODE_HOME = 0,
    UI_MODE_SETTINGS
} ui_mode_t;

typedef enum {
    MENU_PAGE_STATUS = 0,
    MENU_PAGE_POWER_TEMPERATURE,
    MENU_PAGE_SWR_METER,
    MENU_PAGE_CURRENT_METER,
    MENU_PAGE_SELF_TEST,
    MENU_PAGE_SWR1_TRIP,
    MENU_PAGE_SWR2_TRIP,
    MENU_PAGE_SWR1_FWD_FULL_SCALE,
    MENU_PAGE_SWR2_FWD_FULL_SCALE,
    MENU_PAGE_TEMP_B_VALUE,
    MENU_PAGE_TEMP_TRIP,
    MENU_PAGE_OVERDRIVE_TRIP,
    MENU_PAGE_DRAIN_TRIP,
    MENU_PAGE_CURRENT_TRIP,
    MENU_PAGE_TX_VCC_DELAY,
    MENU_PAGE_TX_BIAS_DELAY,
    MENU_PAGE_TX_ACTIVE_HIGH,
    MENU_PAGE_TX_VCC_ACTIVE_HIGH,
    MENU_PAGE_TX_BIAS_ACTIVE_HIGH,
    MENU_PAGE_FAN_ACTIVE_HIGH,
    MENU_PAGE_TRIP_ACTIVE_HIGH,
    MENU_PAGE_POWER_DISPLAY_MODE,
    MENU_PAGE_NET_POWER,
    MENU_PAGE_PEAK_HOLD_MS,
    MENU_PAGE_PEAK_DECAY_MS,
    MENU_PAGE_COUNT
} menu_page_t;

/* TX sequence stages. The VALUES are a contract with the simulator harnesses, which read
   `g_sequence_stage` by number (tools/simulate/trace_ptt_sequence.py, test_first_dit.py), so keep
   them aligned with `SEQ_STAGE_NAMES` in the build-test skill.

   Engage - PTT falls low (key down):  0 -> 1 -> 2 -> 3
   Release - PTT rises high (unkey):   3 or 2 -> 4 -> 5 -> 0 */
typedef enum {
    SEQ_IDLE = 0,           /* Not transmitting: TX path open, VCC and TX_BIAS off. */
    SEQ_TX_ON = 1,          /* RELAYS closed (TX path connected); waiting tx_vcc_delay_ms. */
    SEQ_VCC_ON = 2,         /* TX_VCC up; waiting tx_bias_delay_ms before the bias. */
    SEQ_BIAS_ON = 3,        /* TX_BIAS up and sensed: transmitting, PTT COMPLETE displayed. */
    SEQ_RELEASE_RELAYS = 4, /* Unkey: RELAYS already opened, TX_VCC still up; waiting. */
    SEQ_RELEASE_VCC = 5     /* Unkey: TX_VCC removed, TX_BIAS still up; waiting, then -> IDLE. */
} sequence_stage_t;

/* Trip causes. Bit flags, one per protection, and the VALUES are a contract with the simulator
   harnesses (TRIP_REASON_BITS in tools/simulate/trace_ptt_sequence.py) - keep both the bit
   positions and the names aligned with the fault-name table in the build-test skill. */
typedef enum {
    TRIP_REASON_NONE = 0x00,
    TRIP_REASON_SWR1 = 0x01,
    TRIP_REASON_SWR2 = 0x02,
    TRIP_REASON_HWFAULT = 0x04,
    TRIP_REASON_CURRENT = 0x08,
    TRIP_REASON_TEMP = 0x10,
    TRIP_REASON_OVERDRIVE = 0x20,
    TRIP_REASON_DRAIN = 0x40
} trip_reason_t;

/* TX self-test causes. Bit flags, exactly like the trip causes above. See tx_selftest.c for the
   full contract note; the VALUES are read by the simulator harnesses
   (SELFTEST_REASON_NAMES in tools/simulate/trace_ptt_sequence.py). */
typedef enum {
    TX_SELFTEST_OK = 0x0000,
    TX_SELFTEST_NO_RF = 0x0001,
    TX_SELFTEST_BAD_BAND = 0x0002,
    TX_SELFTEST_LOCK_LOST = 0x0004,
    TX_SELFTEST_BAND_CHG = 0x0008,
    TX_SELFTEST_NO_LOCK = 0x0010,
    TX_SELFTEST_TX_SENSE = 0x0020,
    TX_SELFTEST_STALLED = 0x0040,
    TX_SELFTEST_NO_BAND = 0x0080,
    TX_SELFTEST_BIAS_PIN_STUCK_AFTER_TX = 0x0100
} tx_selftest_reason_t;

/* The two remedies, split by cause (see tx_selftest.c). A FATAL check latches the
   undefined/unkeyable state; every other check folds back. */
#define TX_SELFTEST_LATCH_MASK \
    (TX_SELFTEST_BAD_BAND | TX_SELFTEST_TX_SENSE | TX_SELFTEST_STALLED | TX_SELFTEST_BIAS_PIN_STUCK_AFTER_TX)
#define TX_SELFTEST_CHECK_COUNT 9
#define TRIP_REASON_NAME_MAX 11
#define TX_SELFTEST_NAME_MAX 11

/* Shared timing / scaling constants (see main.c for the full rationale on the band-memory,
   settle and verify windows). */
#define MENU_IDLE_TIMEOUT_MS 8000
#define TEMPERATURE_RECOVERY_HYSTERESIS_C 5U
#define CURRENT_SENSOR_ZERO_RAW 512U
#define CURRENT_SENSOR_POSITIVE_COUNTS 511U
#define CURRENT_SENSOR_FULL_SCALE_A 70U
#define PEAK_HOLD_DEFAULT_MS 1200U
#define PEAK_DECAY_DEFAULT_MS 100U
#define PEAK_DECAY_MIN_MS 50U
#define PEAK_DECAY_SHIFT 5U
#define ENCODER_LONG_PRESS_MS 1200U
#define ENCODER_FAULT_CLEAR_MS 1500U
#define ENCODER_ROTATION_LOCKOUT_MS 5U
#define BAND_CACHE_IDLE_TIMEOUT_MS 60000U
#define BAND_SETTLE_MS 20U
#define BAND_VERIFY_MS 20U
#define TX_SELFTEST_TICK_MS 10U
#define LOCK_LOSS_UNKEYABLE_MS 200U

/* --- State globals, defined in main.c, declared here for the other modules. --- */

extern volatile system_state_t g_state;
extern volatile bool g_fault_latched;
extern volatile unsigned char g_trip_reason;
extern volatile bool g_trip_shutdown_active;
extern volatile unsigned char g_trip_shutdown_elapsed_ms;
extern volatile bool g_ptt_active;

/* First-dit band memory (see docs/first-dit-band-detection.md). */
extern volatile bool g_band_cache_valid;
extern volatile rf_band_t g_band_cache_band;
extern volatile bool g_snoop_active;
extern unsigned int g_band_cache_idle_ms;
extern volatile bool g_band_settle_active;
extern unsigned int g_band_settle_elapsed_ms;
extern volatile bool g_band_verify_active;
extern unsigned int g_band_verify_mismatch_ms;
extern volatile bool g_band_established;
extern volatile bool g_unkeyable;

/* TX self-test verdict state. */
extern unsigned int g_lock_loss_ms;
extern volatile bool g_selftest_failed;
extern volatile unsigned int g_selftest_reason;
extern unsigned int g_selftest_hold[TX_SELFTEST_CHECK_COUNT];
extern unsigned int g_selftest_unkey_ms;

extern volatile bool g_startup_inhibit;
extern volatile bool g_comparator_reset_active;
extern volatile unsigned char g_comparator_reset_elapsed_ms;

extern volatile menu_page_t g_menu_page;
extern volatile menu_page_t g_saved_user_menu_page;
extern ui_mode_t g_ui_mode;
extern volatile bool g_transient_menu_display;
extern volatile bool g_boot_message_active;
extern volatile bool g_ptt_complete_display_active;
extern volatile unsigned int g_ptt_complete_display_elapsed_ms;
extern volatile bool g_menu_changed;

extern unsigned int g_sequence_elapsed_ms;
extern unsigned char g_sequence_stage;
extern volatile const char *g_sequence_stage_text;

/* Live measurement / display state. */
extern unsigned int g_post_fwd_rms_w;
extern unsigned int g_post_fwd_pep_w;
extern unsigned int g_swr1_live_hundredths;
extern unsigned int g_swr2_live_hundredths;
extern unsigned int g_live_temperature_c;
extern unsigned int g_live_current_a;
extern unsigned int g_current_peak_a;
extern unsigned int g_live_overdrive_mw;
extern unsigned int g_pep_decay_elapsed_ms;
extern unsigned int g_current_peak_decay_elapsed_ms;
extern unsigned int g_status_refresh_ms;
extern unsigned int g_startup_elapsed_ms;

extern volatile unsigned char g_timer_ticks_pending;

extern menu_page_t g_lcd_drawn_page;
extern system_state_t g_lcd_drawn_state;
extern unsigned char g_lcd_drawn_trip_reason;
extern unsigned int g_menu_idle_ms;

extern volatile bool g_settings_dirty;
extern unsigned int g_settings_save_delay_ms;

/* ADC scan state. Defaults until the first real scan completes: 0 for power/current/overdrive/
   drain, and a mid-scale ~2.5V reading (511) for temp so a raw 0 cannot read as a false thermal
   trip. */
extern volatile unsigned char g_adc_scan_index;
extern volatile unsigned char g_adc_active_index;
extern volatile unsigned int g_adc_samples[8];
#define ADC_SAMPLE_SWR1_FWD g_adc_samples[0]
#define ADC_SAMPLE_SWR1_REF g_adc_samples[1]
#define ADC_SAMPLE_SWR2_FWD g_adc_samples[2]
#define ADC_SAMPLE_SWR2_REF g_adc_samples[3]
#define ADC_SAMPLE_TEMP g_adc_samples[4]
#define ADC_SAMPLE_CURRENT g_adc_samples[5]
#define ADC_SAMPLE_OVERDRIVE g_adc_samples[6]
#define ADC_SAMPLE_DRAIN g_adc_samples[7]

#endif
