#include <xc.h>
#include <stdbool.h>
#include <stddef.h>
#include "../include/pin_map.h"
#include "../include/lcd_parallel.h"
#include "../include/nvm.h"
#include "../include/freq_counter.h"

#pragma config FEXTOSC = OFF

/* PIC18F47Q10 is the ONLY device in this project (decided 2026-09-23; the PIC16F18875 port,
   and with it every 16F code path, build option and note, was removed). Config words therefore
   use this part's names only: RSTOSC must name the HFINTOSC rate,
   MCLR is EXTMCLR/INTMCLR, and BORV uses VBOR_xxx names - see the DFP's 18f47q10.cfgmap.
   
   THE CLOCK IS NOT A FREE CHOICE: this part's config map offers only two reset oscillator
   settings, `HFINTOSC_64MHZ` and `HFINTOSC_1MHZ` (there is no HFINT32 name here). Choose the
   64 MHz setting - the part's highest internal rate - and match `_XTAL_FREQ` to it (pin_map.h)
   so the XC8 `__delay_*` loops are compiled for the real core. Timer2 takes Fosc/8 so its input
   is 8 MHz and the 1 ms tick falls out of the PR2/prescaler chain below. */
#pragma config RSTOSC = HFINTOSC_64MHZ

#pragma config WDTE = OFF
#pragma config PWRTE = OFF

/* RA6 doubles as CLKOUT/OSC2 on this part, and the CLKOUTEN default is ON (the config bit
   reads clear = enabled; see the DFP's 18f47q10.cfgdata, CVALUE:1:OFF / CVALUE:0:ON). RA6 is
   OUTPUT_LCD_E in this design, so leaving the default silently hands the LCD enable line to the
   clock-output function and the panel never latches.

   Found on 2026-09-22 by reading the pin back under MDB in the boot trace: it reported
   `RA6 Ain 5.0V (RA6)/IOCA6/ANA6/CLKOUT/OSC2` even though the firmware had configured it as an
   output, which is what pointed at the undocumented-by-us config default. */
#pragma config CLKOUTEN = OFF

#pragma config MCLRE = EXTMCLR

#pragma config CP = OFF
#pragma config BOREN = ON

#pragma config BORV = VBOR_190

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

#define SETTINGS_MAGIC 0xA5
#define SETTINGS_VERSION 9
#define MENU_SETTING_U8 0
#define MENU_SETTING_U16 1
#define MENU_SETTING_BOOL 2

#define TRIP_REASON_SWR1 0x01
#define TRIP_REASON_SWR2 0x02
#define TRIP_REASON_HWFAULT 0x04
#define TRIP_REASON_CURRENT 0x08
#define TRIP_REASON_TEMP 0x10
#define TRIP_REASON_OVERDRIVE 0x20
#define TRIP_REASON_DRAIN 0x40

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
/* First-dit band memory: how long a remembered band stays trusted after the last PTT
   before the firmware assumes the operator may have changed bands and reverts to
   bypass-snoop. 60 s is a starting guess - confirm on the bench. */
#define BAND_CACHE_IDLE_TIMEOUT_MS 60000U
/* After the first RF burst decodes the band the LPF relays have just been commanded.
   The amplifier must not be keyed into a relay that is still moving, so the engage waits
   for the contacts to settle. Bypass (RF straight through) is held for this window, so
   the radio's first burst is unaffected. Confirm against the fitted relay's operate time
   on the bench. */
#define BAND_SETTLE_MS 20U
/* A band engage that came from the first-dit memory was chosen with no RF to verify it: at
   keydown the radio has not started transmitting yet. The remembered band is therefore
   checked against the first usable measurement of that transmission, and a band mismatch must
   persist this long before the amplifier is folded back to bypass and re-engaged on the band
   actually being received. Confirm on the bench that this is short enough to be inaudible. */
#define BAND_VERIFY_MS 20U

static volatile system_state_t g_state = STATE_STANDBY;
static volatile bool g_fault_latched = false;
static volatile unsigned char g_trip_reason = 0;
static volatile bool g_trip_shutdown_active = false;
static volatile unsigned char g_trip_shutdown_elapsed_ms = 0;
static volatile bool g_ptt_active = false;
/* First-dit band memory (see docs/first-dit-band-detection.md). Declared volatile so the
   simulator/debugger can read and drive the cache state directly. */
static volatile bool g_band_cache_valid = false;
static volatile rf_band_t g_band_cache_band = BAND_UNKNOWN;
static volatile bool g_snoop_active = false;
static unsigned int g_band_cache_idle_ms = 0;
static volatile bool g_band_settle_active = false;
static unsigned int g_band_settle_elapsed_ms = 0;
static volatile bool g_band_verify_active = false;
static unsigned int g_band_verify_mismatch_ms = 0;
/* A band is "established" for the current transmission when it is backed by a real measurement
   or by the first-dit memory. This is what gates keying: with no RF the classifier reports its
   160m no-signal default, and the amplifier must never key on a band that was never measured. */
static volatile bool g_band_established = false;
static volatile bool g_startup_inhibit = true;
static volatile bool g_comparator_reset_active = false;
static volatile unsigned char g_comparator_reset_elapsed_ms = 0;
static volatile menu_page_t g_menu_page = MENU_PAGE_POWER_TEMPERATURE;
static volatile menu_page_t g_saved_user_menu_page = MENU_PAGE_POWER_TEMPERATURE;
static ui_mode_t g_ui_mode = UI_MODE_HOME;
static volatile bool g_transient_menu_display = false;
static volatile bool g_boot_message_active = false;
static volatile bool g_ptt_complete_display_active = false;
static volatile unsigned int g_ptt_complete_display_elapsed_ms = 0;
static volatile bool g_menu_changed = true;
static unsigned int g_sequence_elapsed_ms = 0;

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

static unsigned char g_sequence_stage = SEQ_IDLE;

/* Text for a stage, for the LCD/debug read-out and for matching a trace line to the state machine.
   Indexed directly by the enum value, so the two must stay in the same order. */
static const char *const SEQUENCE_STAGE_NAMES[] = {
    "IDLE",         /* SEQ_IDLE           */
    "TX-ON",        /* SEQ_TX_ON          */
    "VCC-ON",       /* SEQ_VCC_ON         */
    "BIAS-ON",      /* SEQ_BIAS_ON        */
    "UNKEY-RELAYS", /* SEQ_RELEASE_RELAYS */
    "UNKEY-VCC"     /* SEQ_RELEASE_VCC    */
};

const char *sequence_stage_name(unsigned char stage) {
    if (stage >= (unsigned char)(sizeof SEQUENCE_STAGE_NAMES / sizeof SEQUENCE_STAGE_NAMES[0])) {
        return "?";
    }
    return SEQUENCE_STAGE_NAMES[stage];
}

/* Current stage as text. Refreshed once per main-loop pass so it can be used by the LCD debug
   read-out and read by the simulator harnesses, which otherwise see only the number. Initialised
   with a literal rather than SEQUENCE_STAGE_NAMES[SEQ_IDLE]: XC8 rejects a volatile pointer
   initialised from a ROM array element ("(712) can't generate code for this expression"). */
volatile const char *g_sequence_stage_text = "IDLE";
static unsigned int g_post_fwd_rms_w = 0;
static unsigned int g_post_fwd_pep_w = 0;
static unsigned int g_swr1_live_hundredths = 100;
static unsigned int g_swr2_live_hundredths = 100;
static unsigned int g_live_temperature_c = 0;
static unsigned int g_live_current_a = 0;
static unsigned int g_current_peak_a = 0;
static unsigned int g_live_overdrive_mw = 0;
static unsigned int g_pep_decay_elapsed_ms = 0;
static unsigned int g_current_peak_decay_elapsed_ms = 0;
static unsigned int g_status_refresh_ms = 0;
static unsigned int g_startup_elapsed_ms = 0;
static volatile unsigned char g_timer_ticks_pending = 0;
static menu_page_t g_lcd_drawn_page = MENU_PAGE_COUNT;
static system_state_t g_lcd_drawn_state = STATE_RESET_WAIT;
static unsigned char g_lcd_drawn_trip_reason = 0;
static unsigned int g_menu_idle_ms = 0;
static volatile bool g_settings_dirty = false;
static unsigned int g_settings_save_delay_ms = 0;
static volatile unsigned char g_adc_scan_index = 0;
static volatile unsigned char g_adc_active_index = 0;
/* Defaults until the first real ADC scan completes for each channel: 0 (idle,
   no fault) for power/current/overdrive/drain, and a mid-scale ~2.5V reading
   for temp (raw 0 would otherwise map to a false 150C thermal trip). */
static volatile unsigned int g_adc_samples[8] = {0, 0, 0, 0, 511, 0, 0, 0};
#define ADC_SAMPLE_SWR1_FWD g_adc_samples[0]
#define ADC_SAMPLE_SWR1_REF g_adc_samples[1]
#define ADC_SAMPLE_SWR2_FWD g_adc_samples[2]
#define ADC_SAMPLE_SWR2_REF g_adc_samples[3]
#define ADC_SAMPLE_TEMP g_adc_samples[4]
#define ADC_SAMPLE_CURRENT g_adc_samples[5]
#define ADC_SAMPLE_OVERDRIVE g_adc_samples[6]
#define ADC_SAMPLE_DRAIN g_adc_samples[7]
/* Minimum sample-and-hold settling time after switching ADC channel, before
   starting a conversion; confirm against the datasheet's acquisition-time
   formula for each detector's actual source impedance during bench validation. */
#define ADC_ACQUISITION_US 5
static const unsigned char g_ntc_adc[3][16] = {
    {190, 166, 141, 116, 94, 75, 59, 46, 37, 29, 23, 19, 15, 12, 10, 8},
    {197, 171, 142, 114, 89, 68, 51, 38, 29, 22, 17, 13, 10, 8, 6, 5},
    {201, 174, 143, 113, 86, 64, 47, 34, 25, 19, 14, 11, 8, 6, 5, 4}
};
static const unsigned char g_adc_scan_channels[8] = {0, 1, 2, 3, 5, 9, 10, 11};
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
#define TX_ACTIVE_HIGH_DEFAULT false
#define TX_VCC_ACTIVE_HIGH_DEFAULT false
#define TX_BIAS_ACTIVE_HIGH_DEFAULT false
#define FAN_ACTIVE_HIGH_DEFAULT false
#define TRIP_ACTIVE_HIGH_DEFAULT false
/* Labels are kept as short as clarity allows: string literals live in STRCODE, which is the
   class the linker fails to place first, so every character here is flash. */
static const char *const g_setting_menu_labels[] = {
    "SWR1 TRIP", "SWR2 TRIP", "SWR1 FWD", "SWR2 FWD",
    "NTC B", "TEMP TRIP", "INPUT TRIP", "DRAIN TRIP", "CURR TRIP",
    "TX-VCC DLY", "TX-BIAS DLY", "TX ACTIVE",
    "TX-VCC POL", "TX-BIAS POL", "FAN POL", "TRIP POL",
    "POWER MODE", "NET POWER", "PK HOLD", "PK DECAY"
};
static protection_thresholds_t g_thresholds = {
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

/* XC8 does not merge duplicate string literals, so the few that appear on more than one
   screen are defined once here instead of being repeated at each call site. */
static const char LCD_TEXT_SWR1[] = "SWR1 ";
static const char LCD_TEXT_SWR2[] = "SWR2 ";
static const char LCD_TEXT_MAX[] = "MAX ";
static const char LCD_TEXT_TEMP[] = "TEMP ";

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

void __interrupt() timer0_isr(void) {
    freq_counter_isr();

    bool tick = false;
    if (PIR4bits.TMR2IF != 0) {
        PIR4bits.TMR2IF = 0;
        tick = true;
        if (g_timer_ticks_pending != 255) {
            g_timer_ticks_pending++;
        }
    }

    if (PIR1bits.ADIF != 0) {
        unsigned int sample = (unsigned int)ADRES;
        PIR1bits.ADIF = 0;

        /* The ADCC is 12-bit (0..4095) while every converter below - temperature_c(),
           drain_voltage(), overdrive_power_mw(), current_amperes() and the SWR maths - treats
           the raw value as 10-bit (0..1023). Downscale once here, at capture, so all eight
           channels stay on the 10-bit scale the firmware already assumes. Measured 2026-09-22:
           without this, 2.5 V on the temp pin reads 2048 and temperature_c(2048) -> 2048>>2 =
           512 > 250 -> 150C fault sentinel. */
        sample >>= 2;

        /* Indexed store rather than an 8-case switch: g_adc_active_index is always a valid
           channel index (it is only ever loaded from g_adc_scan_index), and the switch cost
           eight copies of the same store in flash. */
        if (g_adc_active_index < 8) {
            g_adc_samples[g_adc_active_index] = sample;
        }
    }

    /* Refresh every trip ADC on the same bounded cadence. At one channel per
       1 ms tick, any ADC-based trip input is at most one 8-channel scan old. */
    if (tick && ADCON0bits.GO_nDONE == 0) {
        g_adc_active_index = g_adc_scan_index;
        ADPCH = g_adc_scan_channels[g_adc_scan_index];
        g_adc_scan_index++;
        if (g_adc_scan_index >= 8) {
            g_adc_scan_index = 0;
        }
        ADCON0bits.GO_nDONE = 1;
    }

}

void timer0_init(void) {
    /* Timer2 (not Timer0) drives the ~1ms system tick: TMR0's Fosc/4 overflow model
       stalls under MDB after the first interrupt, and Timer2's simpler compare-based
       architecture doesn't hit that issue on either real hardware or the simulator.

       Timer2 is clocked so that (clock / prescale / (PR2+1)) = 1 kHz:
         PIC18F47Q10: 64 MHz core, Fosc/8 = 8 MHz, 1:64, PR2 = 124 -> 8e6/64/125   = 1.000 kHz
       T2CLK is a code, not a divisor: 0x01 = Fosc/4, 0x02 = Fosc/8 (per the DFP). */
    T2CLK = 0x02;         /* Fosc/8: 64 MHz core -> 8 MHz Timer2 input */
    T2CONbits.CKPS = 6;   /* 1:64 prescale */
    T2CONbits.OUTPS = 0;  /* 1:1 postscale */
    PR2 = 124;            /* (124+1) * 64 / 8MHz = 1.000ms */
    TMR2 = 0;
    PIR4bits.TMR2IF = 0;
    PIE4bits.TMR2IE = 1;

    /* This family needs its priority mechanism armed before anything is dispatched. Measured on
       the simulator: with IPEN = 0 no interrupt ever reaches the ISR, even though TMR2IF sets and
       the peripheral enable is set. IPEN = 1, the source's IPRx priority bit, and the matching
       global (GIE/GIEH) make it run at once. */
    INTCONbits.IPEN = 1;
    IPR4bits.TMR2IP = 1;    /* system tick at high priority */

    T2CONbits.ON = 1;

    freq_counter_init();

    INTCONbits.GIE = 1;
}

unsigned int temperature_c(unsigned int raw);
bool is_live_menu_page(menu_page_t page);

void lcd_write_spaces(unsigned char count) {
    while (count > 0) {
        lcd_write_byte(' ', true);
        count--;
    }
}

/* Right-justifies value within a fixed digit width so repeated redraws never
   leave a stale digit behind from a previous, wider value. */
void lcd_write_unsigned_padded(unsigned int value, unsigned char digits) {
    unsigned int threshold = 1;
    unsigned char pad;

    for (pad = digits; pad > 1; pad--) {
        threshold *= 10;
    }
    for (pad = digits; pad > 1; pad--) {
        if (value >= threshold) {
            break;
        }
        lcd_write_spaces(1);
        threshold /= 10;
    }
    lcd_write_unsigned(value);
}

void lcd_write_power_bar(unsigned int power_w, unsigned int full_scale_w, unsigned char width) {
    unsigned char bar_segment;
    unsigned char bar_segments;

    if (full_scale_w == 0) {
        full_scale_w = 1;
    }

    /* 16-bit on purpose: power_w is bounded by the configured forward full scale (2500 W max)
       and width by the LCD columns, so the product cannot overflow 16 bits. Using longs here
       pulled the 32-bit divide/multiply helpers into the image for no reason. */
    bar_segments = (unsigned char)((power_w * width) / full_scale_w);

    if (bar_segments > width) {
        bar_segments = width;
    }

    for (bar_segment = 0; bar_segment < width; bar_segment++) {
        lcd_write_byte(bar_segment < bar_segments ? '|' : '.', true);
    }
}

void lcd_write_swr_right(unsigned char field_width, unsigned int swr_hundredths) {
    unsigned int whole = swr_hundredths / 100U;
    unsigned int fraction = swr_hundredths % 100U;
    unsigned char text_len = (unsigned char)(4 + (whole >= 10 ? 2 : 1) + 3);

    while (field_width > text_len) {
        lcd_write_byte(' ', true);
        field_width--;
    }
    lcd_write_text("SWR=");
    lcd_write_unsigned(whole);
    lcd_write_byte('.', true);
    lcd_write_unsigned_padded(fraction, 2);
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
        lcd_set_cursor(0, 0);
        if (g_trip_reason & TRIP_REASON_TEMP) {
            lcd_write_text(LCD_TEXT_TEMP);
            lcd_write_unsigned(g_live_temperature_c);
            lcd_write_byte('/', true);
            lcd_write_unsigned(g_thresholds.temp_trip_c);
            lcd_write_byte('C', true);
        } else if (g_trip_reason & TRIP_REASON_SWR1) {
            if (g_swr1_live_hundredths >= 1000) {
                lcd_write_text("FLTR?? CHECK LPF");
            } else {
                lcd_write_text(LCD_TEXT_SWR1);
                lcd_write_swr_right(11, g_swr1_live_hundredths);
                lcd_set_cursor(1, 0);
                lcd_write_text(LCD_TEXT_MAX);
                lcd_write_swr_right(11, (unsigned int)g_thresholds.swr1_trip_tenths * 10U);
            }
        } else if (g_trip_reason & TRIP_REASON_SWR2) {
            lcd_write_text(LCD_TEXT_SWR2);
            lcd_write_swr_right(11, g_swr2_live_hundredths);
            lcd_set_cursor(1, 0);
            lcd_write_text(LCD_TEXT_MAX);
            lcd_write_swr_right(11, (unsigned int)g_thresholds.swr2_trip_tenths * 10U);
        } else if (g_trip_reason & TRIP_REASON_CURRENT) {
            lcd_write_text("AMPS ");
            lcd_write_unsigned(g_live_current_a);
            lcd_write_byte('/', true);
            lcd_write_unsigned(g_thresholds.current_trip_a);
            lcd_write_byte('A', true);
        } else if (g_trip_reason & TRIP_REASON_OVERDRIVE) {
            lcd_write_text("OVDR ");
            lcd_write_unsigned(g_live_overdrive_mw / 1000U);
            lcd_write_byte('/', true);
            lcd_write_unsigned((unsigned int)g_thresholds.overdrive_trip_tenths_w / 10U);
            lcd_write_byte('W', true);
        } else {
            lcd_write_text("FAULT: TRIP");
            lcd_set_cursor(1, 0);
            if (g_trip_reason & TRIP_REASON_HWFAULT) lcd_write_text("HARDWARE");
            else if (g_trip_reason & TRIP_REASON_DRAIN) lcd_write_text("DRAIN");
        }
        return;
    }
    if (g_ptt_complete_display_active) {
        lcd_set_cursor(0, 0);
        lcd_write_text("PTT COMPLETE");
        lcd_set_cursor(1, 0);
        lcd_write_text("TX ACTIVE");
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
        lcd_write_power_bar(power_w, g_thresholds.swr2_fwd_full_scale_w, 16);
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

void adc_init(void) {
    FVRCON = 0x00;
    ANSELA = 0x2F;
    ANSELA &= ~0x10; /* RA4 must stay digital: it drives OUTPUT_LCD_RS */
    ANSELB = 0x0E;
    ADCON1 = 0x20;
    ADPCH = 0;
    // The result must be a plain right-justified 0-1023 count: temperature_c(),
    // drain_voltage() and overdrive_power_mw() all treat the raw ADC value as 0-1023.
    //
    // ADCC ADFM is a SINGLE bit, ADCON0<2>, and 0 means LEFT-justified. The 10-bit result then
    // sits in ADRES<15:6>, so a 2.5V temperature input (raw 512) reads as 512<<6 = 32768 and
    // temperature_c() returns its 150C fault sentinel, which is exactly the spurious TEMPERATURE
    // trip the bring-up hit (probe_q10_ptt_path.py, 2026-09-22).
    ADCON0 = 0x88;
    ADCON0bits.ADFM = 1;
    PIR1bits.ADIF = 0;
    PIE1bits.ADIE = 1;
    INTCONbits.PEIE = 1;
    __delay_us(ADC_ACQUISITION_US);
    ADCON0bits.GO_nDONE = 1;
}

void apply_startup_inhibit(void) {
    apply_bypass();
    set_fan_output(false);
    set_trip_output(false);
    OUTPUT_COMP_RESET = 0; // SETTLE held low for the startup-inhibit window
    g_startup_inhibit = true;
    /* Power-up has no idea which band the operator is on: drop any remembered band and
       require a fresh first-dit measurement before the amplifier may key. */
    g_band_cache_valid = false;
    g_band_cache_band = BAND_UNKNOWN;
    g_band_cache_idle_ms = 0;
    g_snoop_active = false;
    g_band_settle_active = false;
    g_band_settle_elapsed_ms = 0;
    g_band_verify_active = false;
    g_band_verify_mismatch_ms = 0;
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

void handle_ptt_transition(bool ptt_asserted) {
    if (g_startup_inhibit)
        return; // Ignore PTT changes until system settles (RC1 low)
    if (ptt_asserted) {
        g_ptt_active = true;
        g_sequence_stage = 0;
        g_band_cache_idle_ms = 0;
        g_band_settle_active = false;
        g_band_settle_elapsed_ms = 0;
        g_band_verify_mismatch_ms = 0;
        /* Never move the LPF relays while the amplifier is keyed: a PTT re-assert
           during the release ramp can still have TX_VCC/TX_BIAS asserted, and both
           branches below touch the band selection. Forcing bypass first means the
           relay change (if any) always happens with the amplifier cold. */
        apply_bypass();
        if (!g_transient_menu_display) {
            if (is_live_menu_page(g_menu_page)) {
                g_saved_user_menu_page = g_menu_page;
            }
            g_ui_mode = UI_MODE_HOME;
            g_transient_menu_display = true;
            g_menu_page = MENU_PAGE_STATUS;
            g_menu_changed = true;
        }
        start_comparator_reset();
        if (!g_fault_latched) {
            g_state = STATE_RESET_WAIT;
        }
        if (INPUT_OVERCURRENT_FAULT == 0) {
            clear_fault_latches();
            g_state = STATE_OPERATE;
        }
        if (freq_counter_band_confirmed()) {
            /* The counter has already confirmed a band from live RF. That is fresher evidence
               than the remembered band, so it wins: the operator may have changed bands and be
               transmitting on the new one right now. Remember it and engage on it. */
            freq_counter_status_t status;
            freq_counter_get_status(&status);
            g_band_cache_band = status.current_band;
            g_band_cache_valid = true;
            g_band_cache_idle_ms = 0;
            g_snoop_active = false;
            g_band_verify_active = false;
            g_band_verify_mismatch_ms = 0;
            /* The confirmed band can be one the relay was only just commanded to (the counter
               reclassifies on a band change), so hold bypass for the relay settle exactly like the
               remembered-band path. Without this the T/R relay closes onto a still-moving relay -
               measured 2026-09-22 as a 7.0ms HOT SWITCH in the FREQ_CTR scenario. */
            g_band_settle_active = true;
            g_band_settle_elapsed_ms = 0;
            g_band_established = true;
            return;
        }
        if (g_band_cache_valid) {
            /* First-dit: there is no usable live measurement yet (the radio has only just
               been keyed), so use the band decoded from the previous transmission and engage
               immediately. The remembered band is verified against the first measurement of
               this transmission by update_tx_sequence(). */
            /* Decisive guard: if the counter already holds a stable live measurement that
               disagrees with the remembered band, the live RF wins. Restoring the stale band
               would move the relay to the wrong position, then the verify step would fold it
               back - a transient where current_band and the relay disagree (I4) and, worse,
               a hot-switch if the fold-back happens after keying. Prefer the live band and let
               the snoop path decode it cleanly. */
            rf_band_t live = freq_counter_measured_band();
            if (live != BAND_OUT_OF_SPEC && live != g_band_cache_band) {
                freq_counter_unlock_band();
                g_snoop_active = true;
                g_band_verify_active = false;
                g_band_verify_mismatch_ms = 0;
                g_band_cache_valid = false;
                g_state = STATE_BYPASS_SNOOP;
                return;
            }
            if (freq_counter_restore_locked_band(g_band_cache_band)) {
                /* The remembered band differs from the one the LPF relays are sitting on, so
                   they have just been commanded to move. The T/R relay must not close onto a
                   moving relay, so hold bypass for the relay's switching time exactly as the
                   decode path does after a snoop. When the selection does not move (the common
                   warm re-key on the same band) there is nothing to wait for and the T/R relay
                   is closed on the normal sequencer timing. */
                g_band_settle_active = true;
                g_band_settle_elapsed_ms = 0;
            }
            g_snoop_active = false;
            g_band_verify_active = true;
            g_band_verify_mismatch_ms = 0;
            g_band_established = true;
            return;
        }
        /* First-dit bypass snoop: no band is known yet, so hold the amplifier in bypass
           (LDMOS bias off, RF path straight through) while the radio's first RF burst is
           measured. Bypass was already forced at the top of this transition; the band is
           deliberately NOT locked here - the relay selection stays live so the first burst
           can be classified. */
        freq_counter_unlock_band();
        g_snoop_active = true;
        g_band_verify_active = false;
        g_band_verify_mismatch_ms = 0;
        g_state = STATE_BYPASS_SNOOP;
    } else {
        g_ptt_active = false;
        g_snoop_active = false;
        g_band_settle_active = false;
        g_band_verify_active = false;
        g_band_verify_mismatch_ms = 0;
        invalidate_established_band();
        g_state = STATE_STANDBY;
        if (g_ptt_complete_display_active) {
            g_ptt_complete_display_elapsed_ms = 0;
        } else if (g_transient_menu_display) {
            g_menu_page = g_saved_user_menu_page;
            g_transient_menu_display = false;
            g_menu_changed = true;
        }
    }
}

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

bool is_live_menu_page(menu_page_t page) {
    return page < MENU_PAGE_SWR1_TRIP;
}

void step_home_page(bool clockwise) {
    if (clockwise) {
        g_menu_page = (menu_page_t)(g_menu_page + 1);
        if (!is_live_menu_page(g_menu_page)) {
            g_menu_page = MENU_PAGE_STATUS;
        }
    } else if (g_menu_page == MENU_PAGE_STATUS) {
        g_menu_page = MENU_PAGE_CURRENT_METER;
    } else {
        g_menu_page = (menu_page_t)(g_menu_page - 1);
    }

    g_saved_user_menu_page = g_menu_page;
    g_menu_changed = true;
    mark_settings_dirty();
}

void step_settings_page(void) {
    if (g_menu_page < MENU_PAGE_SWR1_TRIP || g_menu_page >= MENU_PAGE_PEAK_DECAY_MS) {
        g_menu_page = MENU_PAGE_SWR1_TRIP;
    } else {
        g_menu_page = (menu_page_t)(g_menu_page + 1);
    }
    g_menu_changed = true;
}

void enter_settings(void) {
    if (!g_ptt_active) {
        g_ui_mode = UI_MODE_SETTINGS;
        g_menu_page = MENU_PAGE_SWR1_TRIP;
        g_menu_changed = true;
    }
}

void exit_settings(void) {
    g_ui_mode = UI_MODE_HOME;
    g_menu_page = g_saved_user_menu_page;
    g_menu_changed = true;
    mark_settings_dirty();
}

void adjust_selected_setting(bool increase) {
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

void handle_encoder_rotation(bool clockwise) {
    if (g_state == STATE_TRIP || g_transient_menu_display) {
        return;
    }
    if (g_ui_mode == UI_MODE_SETTINGS) {
        if (!g_ptt_active) {
            adjust_selected_setting(clockwise);
            g_menu_changed = true;
            mark_settings_dirty();
        }
    } else if (is_live_menu_page(g_menu_page)) {
        step_home_page(clockwise);
    }
}

void handle_encoder_short_press(void) {
    if (g_state == STATE_TRIP || g_transient_menu_display) {
        return;
    }
    if (g_ui_mode == UI_MODE_SETTINGS) {
        step_settings_page();
    } else {
        enter_settings();
    }
}

void handle_encoder_long_press(void) {
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

void update_tx_sequence(void) {
    if (g_startup_inhibit || g_comparator_reset_active) {
        apply_bypass();
        g_sequence_stage = 0;
        release_band_if_cold();
        return;
    }
    if (g_fault_latched) {
        return;
    }

    if (g_snoop_active) {
        /* First-dit bypass snoop: the amplifier stays in bypass (all TX outputs inactive)
           until the radio's first RF burst decodes a band. freq_counter_band_confirmed()
           rather than freq_counter_signal_valid() is required here: after silence the
           10 ms tick has already classified an empty gate window as 160m, and that stale
           band must never be cached or locked. */
        freq_counter_status_t status;

        if (!freq_counter_band_confirmed()) {
            /* Still bypassed: the amplifier must not key on an unverified band, and the
               relay selection is still free to follow the incoming RF. */
            apply_bypass();
            g_sequence_stage = 0;
            g_state = STATE_BYPASS_SNOOP;
            return;
        }
        freq_counter_get_status(&status);
        g_band_cache_band = status.current_band;
        g_band_cache_valid = true;
        g_band_cache_idle_ms = 0;
        freq_counter_lock_band();
        g_snoop_active = false;
        g_band_established = true;
        /* The band selection has just moved to the decoded band. Stay in bypass until the
           relay contacts have settled, then engage on that band (see BAND_SETTLE_MS). */
        g_band_settle_active = true;
        g_band_settle_elapsed_ms = 0;
    }

    if (g_band_settle_active) {
        /* Bypass (no bias, RF straight through) until the newly selected LPF relay has
           settled, so the amplifier is never keyed into a relay that is still moving. */
        apply_bypass();
        g_sequence_stage = 0;
        if (g_band_settle_elapsed_ms < BAND_SETTLE_MS) {
            g_band_settle_elapsed_ms++;
            return;
        }
        g_band_settle_active = false;
    }

    if (g_band_verify_active) {
        /* The engage came from the remembered band, which was chosen with no RF to verify it:
           at keydown the radio has not started transmitting yet. Verify it against the first
           usable measurement of this transmission - if the operator changed bands and keyed
           straight away, this is where that is caught. The relay selection must not move while
           the amplifier is keyed, so a confirmed mismatch forces bypass first; the snoop path
           then re-selects the measured band cold and re-engages on it. */
        freq_counter_status_t status;
        rf_band_t measured = freq_counter_measured_band();

        freq_counter_get_status(&status);
        if (measured == BAND_OUT_OF_SPEC) {
            g_band_verify_mismatch_ms = 0;   /* nothing usable to compare against yet */
            /* No usable measurement yet: the radio has not started transmitting. Hold bypass
               rather than engaging on an unverified remembered band. */
            apply_bypass();
            g_sequence_stage = 0;
            return;
        } else if (measured == status.locked_band) {
            g_band_verify_active = false;    /* the remembered band is confirmed */
            g_band_verify_mismatch_ms = 0;
        } else if (g_band_verify_mismatch_ms < BAND_VERIFY_MS) {
            /* A mismatch is being counted toward fold-back. Hold bypass so the amplifier is not
               keyed onto the remembered band while the measured band is settling, and so the
               relay can fold back cold once the mismatch window elapses. */
            apply_bypass();
            g_sequence_stage = 0;
            g_band_verify_mismatch_ms++;
            return;
        } else {
            apply_bypass();
            freq_counter_unlock_band();
            g_band_verify_active = false;
            g_band_verify_mismatch_ms = 0;
            g_snoop_active = true;
            g_sequence_stage = 0;
            g_state = STATE_BYPASS_SNOOP;
            return;
        }
    }

    if (g_ptt_active) {
        if (g_sequence_stage == SEQ_IDLE) {
            if (!g_band_established) {
                /* The relay selection is not backed by any measurement for this transmission
                   (with no RF the classifier reports its 160m no-signal default), so the
                   amplifier must not key. Wait in bypass until the first burst decodes a band. */
                apply_bypass();
                freq_counter_unlock_band();
                g_snoop_active = true;
                g_state = STATE_BYPASS_SNOOP;
                return;
            }
            freq_counter_lock_band();
            set_tx_output(true);
            g_sequence_elapsed_ms = 0;
            g_sequence_stage = SEQ_TX_ON;
        } else if (g_sequence_stage == SEQ_TX_ON) {
            g_sequence_elapsed_ms++;
            if (g_sequence_elapsed_ms >= g_thresholds.tx_vcc_delay_ms) {
                set_tx_vcc_output(true);
                g_sequence_elapsed_ms = 0;
                g_sequence_stage = SEQ_VCC_ON;
            }
        } else if (g_sequence_stage == SEQ_VCC_ON) {
            g_sequence_elapsed_ms++;
            if (g_sequence_elapsed_ms >= g_thresholds.tx_bias_delay_ms) {
                set_tx_bias_output(true);
                /* SENSE_* reads the pin, not the latch - PTT COMPLETE must mean the outputs
                   have actually reached their active levels, not that they were commanded to. */
                if (SENSE_TX == output_level(true, g_thresholds.tx_active_high) &&
                    SENSE_TX_VCC == output_level(true, g_thresholds.tx_vcc_active_high) &&
                    SENSE_TX_BIAS == output_level(true, g_thresholds.tx_bias_active_high)) {
                    g_sequence_stage = SEQ_BIAS_ON;
                    g_ptt_complete_display_active = true;
                    g_ptt_complete_display_elapsed_ms = 0;
                    g_menu_changed = true;
                }
            }
        }
        return;
    }

    // PTT released: open relays first, then remove VCC and bias in order.
    if (g_sequence_stage == SEQ_BIAS_ON || g_sequence_stage == SEQ_VCC_ON) {
        /* Stage 2 (SEQ_VCC_ON) is TX + TX_VCC already up with the bias still ramping. It must
           unwind through the same ordered path as stage 3, otherwise releasing PTT in that
           20 ms window would leave TX_VCC asserted (and, before release_band_if_cold(),
           the band unlocked) for the rest of the receive period. */
        set_tx_output(false);
        g_sequence_elapsed_ms = 0;
        g_sequence_stage = SEQ_RELEASE_RELAYS;
    } else if (g_sequence_stage == SEQ_RELEASE_RELAYS) {
        g_sequence_elapsed_ms++;
        if (g_sequence_elapsed_ms >= g_thresholds.tx_vcc_delay_ms) {
            set_tx_vcc_output(false);
            g_sequence_elapsed_ms = 0;
            g_sequence_stage = SEQ_RELEASE_VCC;
        }
    } else if (g_sequence_stage == SEQ_RELEASE_VCC) {
        g_sequence_elapsed_ms++;
        if (g_sequence_elapsed_ms >= g_thresholds.tx_bias_delay_ms) {
            set_tx_bias_output(false);
            g_sequence_stage = SEQ_IDLE;
            release_band_if_cold();
        }
    } else if (g_sequence_stage == SEQ_TX_ON) {
        set_tx_output(false);
        g_sequence_stage = SEQ_IDLE;
        release_band_if_cold();
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
    g_state = g_snoop_active ? STATE_BYPASS_SNOOP : STATE_OPERATE;
    set_trip_output(false);
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
    unsigned int current_raw = 0;

    /* Internal oscillator at 64 MHz, written explicitly.
     *
     * On silicon the config word (`#pragma config RSTOSC = HFINTOSC_64MHZ`) selects this at reset,
     * which is why it was implicit until now. The MDB simulator does NOT apply the config word -
     * after a full boot its `OSCCON1`/`OSCFRQ` still read 0 (measured 2026-09-24) - so a simulated
     * run is not at the design clock unless the clock is programmed in code. Writing what the config
     * word already implies is harmless on hardware and makes the simulation match:
     *   NDIV = 0 (/1), NOSC = 0b0110 = HFINTOSC, HFFRQ = 0x07 = 64 MHz
     * (HFFRQ has no 32 MHz step above 16: 0 = 1, 1 = 2, 2 = 4, 3 = 8, 4 = 12, 5 = 16, 6 = 32, 7 = 64.) */
    OSCCON1 = 0x60;
    OSCFRQ = 0x07;

    TRISAbits.TRISA0 = 1;
    TRISAbits.TRISA1 = 1;
    TRISAbits.TRISA2 = 1;
    TRISAbits.TRISA3 = 1;
    TRISAbits.TRISA4 = 0;
    TRISAbits.TRISA5 = 1;
    TRISAbits.TRISA6 = 0;
    TRISAbits.TRISA7 = 0;
    ANSELC = 0x00;
    TRISCbits.TRISC0 = 1;
    WPUCbits.WPUC0 = 1;
    TRISCbits.TRISC1 = 0;
    TRISCbits.TRISC2 = 1;
    WPUCbits.WPUC2 = 1;
    TRISCbits.TRISC3 = 0;
    TRISCbits.TRISC4 = 0;
    TRISCbits.TRISC5 = 0;
    TRISCbits.TRISC6 = 0;
    TRISCbits.TRISC7 = 0;

    TRISB = 0x5F;
    TRISBbits.TRISB6 = 1;
    PORTB = 0x00;
    WPUB = 0x43;

    /* Port D for parallel LCD D7 pin; RD1 (freq counter) and RD2-RD7 (band
       outputs) are configured separately by freq_counter_init(). */
    TRISD = 0xFE;  /* RD0 = output (LCD D7), rest inputs for now */

    set_tx_output(false);
    set_tx_vcc_output(false);
    set_tx_bias_output(false);
    set_fan_output(false);
    set_trip_output(false);

    /* ORDER MATTERS, AND IT IS A SAFETY PROPERTY.
     *
     * The 1 ms system tick is the only periodic supervision this amplifier has: it is what
     * advances the startup-inhibit window, the band-settle delay, the band-verify timeout and
     * every trip debounce. Nothing below this point may run with the amplifier able to key and
     * no tick, because a stall anywhere in the remaining bring-up would then leave the outputs
     * latched with no supervision at all.
     *
     * It used to run at the *end* of initialisation - after `lcd_init()` and
     * `show_boot_message()` - and the Q10 bring-up run on 2026-09-22 showed exactly why that is
     * wrong: 200,000 simulator steps in, `T2CON` and `OSCCON1` still read 0 because the LCD boot
     * sequence had not finished, so the tick was not yet armed. The LCD is the slowest and least
     * trustworthy thing in the boot path (a held E line or a missing panel can block it), and it
     * must never be a prerequisite for the protection tick.
     *
     * So the sequence is now: force every output safe -> arm the tick -> then talk to the LCD and
     * the rest. `apply_startup_inhibit()` immediately follows, so the outputs stay inhibited while
     * the slow peripherals come up. */
    timer0_init();
    apply_startup_inhibit();

    adc_init();
    load_settings();
    lcd_init();
    show_boot_message();
    g_boot_message_active = true;

    while (1) {
        swr1_fwd_raw = ADC_SAMPLE_SWR1_FWD;
        swr1_ref_raw = ADC_SAMPLE_SWR1_REF;
        swr2_fwd_raw = ADC_SAMPLE_SWR2_FWD;
        swr2_ref_raw = ADC_SAMPLE_SWR2_REF;
        temp_raw = ADC_SAMPLE_TEMP;
        temp_c = temperature_c(temp_raw);
        overdrive_raw = ADC_SAMPLE_OVERDRIVE;
        drain_raw = ADC_SAMPLE_DRAIN;
        overdrive_power = overdrive_power_mw(overdrive_raw);
        drain_voltage_v = drain_voltage(drain_raw);
        current_raw = ADC_SAMPLE_CURRENT;
        update_post_filter_power(swr2_fwd_raw, swr2_ref_raw);
        g_swr2_live_hundredths = compute_swr_hundredths(swr2_fwd_raw, swr2_ref_raw);
        g_swr1_live_hundredths = compute_swr_hundredths(swr1_fwd_raw, swr1_ref_raw);
        g_live_temperature_c = temp_c;
        g_live_current_a = current_amperes(current_raw);
        update_current_peak(g_live_current_a);
        g_live_overdrive_mw = overdrive_power;

        bool swr1_fault = swr_trip(swr1_fwd_raw, swr1_ref_raw,
                       g_thresholds.swr1_trip_tenths);
        bool swr2_fault = swr_trip(swr2_fwd_raw, swr2_ref_raw,
                       g_thresholds.swr2_trip_tenths);
        bool hw_fault = (INPUT_OVERCURRENT_FAULT == 1);
        unsigned int current_trip_raw = CURRENT_SENSOR_ZERO_RAW +
            (unsigned int)(((unsigned long)g_thresholds.current_trip_a *
                            CURRENT_SENSOR_POSITIVE_COUNTS) /
                           CURRENT_SENSOR_FULL_SCALE_A);
        bool current_fault = (current_raw >= current_trip_raw);

        if ((INPUT_PTT == 0) != g_ptt_active) {
            handle_ptt_transition(INPUT_PTT == 0);
        }

        update_protection_state(temp_c, overdrive_power, drain_voltage_v,
                                swr1_fault,
                                swr2_fault,
                                hw_fault,
                                current_fault);

        unsigned int elapsed_ms = 0;
        while (g_timer_ticks_pending != 0) {
            g_timer_ticks_pending--;
            elapsed_ms++;
            if (g_comparator_reset_active) {
                g_comparator_reset_elapsed_ms++;
                if (g_comparator_reset_elapsed_ms >= 10) {
                    OUTPUT_COMP_RESET = 1;
                    g_comparator_reset_active = false;
                }
            }
            if (g_trip_shutdown_active) {
                g_trip_shutdown_elapsed_ms++;
                if (g_trip_shutdown_elapsed_ms >= 5) {
                    set_tx_output(false);
                    set_tx_bias_output(false);
                    g_trip_shutdown_active = false;
                }
            }
            if (g_ptt_complete_display_active) {
                g_ptt_complete_display_elapsed_ms++;
                if (g_ptt_complete_display_elapsed_ms >= 500) {
                    g_ptt_complete_display_active = false;
                    g_ptt_complete_display_elapsed_ms = 0;
                    if (!g_fault_latched) {
                        g_transient_menu_display = false;
                        g_menu_page = g_saved_user_menu_page;
                    }
                    g_menu_changed = true;
                }
            }
            if (g_startup_inhibit) {
                g_startup_elapsed_ms++;
                if (g_startup_elapsed_ms >= 1000) {
                    g_startup_inhibit = false;
                    g_boot_message_active = false;
                    g_menu_changed = true;
                    // Single low->high transition signals hardware has settled; PTT
                    // is only actionable after this (SETTLE then idles high, pulsing
                    // low again on each subsequent PTT transition).
                    OUTPUT_COMP_RESET = 1;
                }
            } else {
                update_peak_decay(&g_post_fwd_pep_w, &g_pep_decay_elapsed_ms, 1);
                update_peak_decay(&g_current_peak_a, &g_current_peak_decay_elapsed_ms, 1);
                update_tx_sequence();
            }
            /* First-dit band memory ages only while receiving. After a long idle period
               the operator may have changed bands, so the remembered band is dropped and
               the next PTT goes back to bypass-snoop. */
            if (!g_ptt_active && g_band_cache_valid) {
                if (g_band_cache_idle_ms < BAND_CACHE_IDLE_TIMEOUT_MS) {
                    g_band_cache_idle_ms++;
                } else {
                    g_band_cache_valid = false;
                    g_band_cache_band = BAND_UNKNOWN;
                    g_band_cache_idle_ms = 0;
                }
            }
            static unsigned char fc_tick_ms = 0;
            fc_tick_ms++;
            if (fc_tick_ms >= 10) {
                fc_tick_ms = 0;
                freq_counter_tick_10ms();
            }

            if (g_settings_save_delay_ms > 0) {
                g_settings_save_delay_ms--;
            }
            g_status_refresh_ms++;
        }

        poll_menu_inputs(elapsed_ms);

        /* Publish the sequence stage as text: `sequence_stage_name()` is the one conversion and
           this keeps the published copy in step with the state machine. */
        g_sequence_stage_text = sequence_stage_name(g_sequence_stage);

        if (!g_boot_message_active &&
            (g_menu_page == MENU_PAGE_STATUS ||
             g_menu_page == MENU_PAGE_POWER_TEMPERATURE ||
             g_menu_page == MENU_PAGE_SWR_METER ||
             g_menu_page == MENU_PAGE_CURRENT_METER)) {
            if (g_status_refresh_ms >= 100 || g_menu_changed) {
                show_menu_page();
                g_status_refresh_ms = 0;
                g_menu_changed = false;
            }
        } else if (!g_boot_message_active && g_menu_changed) {
            show_menu_page();
            g_menu_changed = false;
        }

        /* Drain a few queued LCD bytes per pass instead of blocking for a
           whole page, so update_protection_state() above is never starved by
           an in-progress screen redraw (see bench-validation.md timing budget). */
        lcd_service(2);

        service_settings_save();
    }
}
