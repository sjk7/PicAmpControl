/* Firmware-only diagnostic self-test (docs/firmware-self-test-diagnostic.md).

   Runs, only while the amplifier is cold, an assert-and-verify loop over every output
   (SENSE_* read-back), the 0->1->2->3->0 sequencer walk, an LCD liveness pattern and a settings
   EEPROM round-trip. Each check is its own function (diag_outputs_step / diag_sequencer_step /
   diag_lcd_check / diag_eeprom_check), and the menu can run them all or one at a time.

   The harness (tools/simulate/trace_ptt_sequence.py) triggers a run by writing g_diag_request
   through its .sym address and reads the verdict from g_diag_result / g_diag_done - it never
   re-derives a pin level. Keep those global names stable. */

#include <xc.h>
#include <stdbool.h>
#include "../include/pin_map.h"
#include "../include/lcd_parallel.h"
#include "../include/nvm.h"
#include "../include/settings.h"
#include "../include/outputs.h"
#include "../include/self_test.h"

/* Shared state/functions defined in main.c. (Phase 3 of the refactor moves the definitions into
   dedicated modules and turns these into proper header declarations.) */
extern volatile bool g_ptt_active;
extern volatile bool g_fault_latched;
extern volatile bool g_menu_changed;

/* How long each output is held asserted/deasserted before its SENSE_* read-back. */
#define DIAG_HOLD_MS 5U
/* Scratch EEPROM address for the round-trip, clear of the settings record (address 0). */
#define DIAG_EEPROM_ADDR 0x80
/* Number of outputs the assert-and-verify loop walks (TX, VCC, BIAS, fan, trip, 6 bands). */
#define DIAG_OUTPUT_COUNT 11

static const char *const DIAG_CHECK_NAMES[] = {
    "OUTPUT",    /* DIAG_OUTPUTS   0x01 */
    "SEQ",       /* DIAG_SEQUENCER 0x02 */
    "LCD",       /* DIAG_LCD       0x04 */
    "EEPROM"     /* DIAG_EEPROM    0x08 */
};

/* Menu selection: index 0 = run all, 1..4 = run one check. Maps to the run mask. */
static const unsigned char DIAG_SELECT_MASKS[] = {
    DIAG_CHECK_ALL, DIAG_OUTPUTS, DIAG_SEQUENCER, DIAG_LCD, DIAG_EEPROM
};
#define DIAG_SELECT_COUNT 5
static const char *const DIAG_SELECT_NAMES[] = { "ALL", "OUTPUT", "SEQ", "LCD", "EEPROM" };

/* The globals the harness reads/writes. `g_diag_request` is the trigger (menu or simulator);
   `g_diag_result` is the PASS/FAIL mask it asserts. All volatile so the simulator reads them
   directly. */
volatile bool g_diag_request = false;
static volatile bool g_diag_running = false;
static volatile bool g_diag_done = false;
static volatile unsigned char g_diag_result = DIAG_OK;
static unsigned char g_diag_selected = DIAG_CHECK_ALL;
static unsigned char g_diag_run_mask = DIAG_CHECK_ALL;
static unsigned char g_diag_phase = 0;   /* 0=outputs, 1=sequencer, 2=lcd, 3=eeprom, 4=done */
static unsigned char g_diag_index = 0;   /* current output (0..10) or sequencer stage */
static unsigned char g_diag_sub = 0;     /* 0=assert, 1=hold+verify-active, 2=deassert, 3=hold+verify-inactive */
static unsigned int g_diag_elapsed_ms = 0;

const char *diag_check_name(unsigned char index) {
    if (index >= DIAG_CHECK_COUNT) {
        return "?";
    }
    return DIAG_CHECK_NAMES[index];
}

void diag_select_cycle(void) {
    unsigned char index;
    for (index = 0; index < DIAG_SELECT_COUNT; index++) {
        if (DIAG_SELECT_MASKS[index] == g_diag_selected) {
            g_diag_selected = DIAG_SELECT_MASKS[(index + 1) % DIAG_SELECT_COUNT];
            g_menu_changed = true;
            return;
        }
    }
    g_diag_selected = DIAG_SELECT_MASKS[0];
    g_menu_changed = true;
}

unsigned char diag_selected_index(void) {
    unsigned char index;
    for (index = 0; index < DIAG_SELECT_COUNT; index++) {
        if (DIAG_SELECT_MASKS[index] == g_diag_selected) {
            return index;
        }
    }
    return 0;
}

const char *diag_selected_name(void) {
    return DIAG_SELECT_NAMES[diag_selected_index()];
}

/* Drive output `idx` (0..4 = TX/VCC/BIAS/fan/trip, 5..10 = bands 160m..10m) via its LAT write. */
static void diag_set_output(unsigned char idx, bool active) {
    switch (idx) {
        case 0: set_tx_output(active); break;
        case 1: set_tx_vcc_output(active); break;
        case 2: set_tx_bias_output(active); break;
        case 3: set_fan_output(active); break;
        case 4: set_trip_output(active); break;
        case 5: OUTPUT_BAND_160M = active ? 1 : 0; break;
        case 6: OUTPUT_BAND_80M  = active ? 1 : 0; break;
        case 7: OUTPUT_BAND_40M  = active ? 1 : 0; break;
        case 8: OUTPUT_BAND_20M  = active ? 1 : 0; break;
        case 9: OUTPUT_BAND_15M  = active ? 1 : 0; break;
        case 10: OUTPUT_BAND_10M = active ? 1 : 0; break;
    }
}

/* True when output `idx` reads back ASSERTED at the pin (SENSE_* PORT read, not the latch). */
static bool diag_sense_active(unsigned char idx) {
    switch (idx) {
        case 0: return SENSE_TX == output_level(true, g_thresholds.tx_active_high);
        case 1: return SENSE_TX_VCC == output_level(true, g_thresholds.tx_vcc_active_high);
        case 2: return SENSE_TX_BIAS == output_level(true, g_thresholds.tx_bias_active_high);
        case 3: return SENSE_FAN == output_level(true, g_thresholds.fan_active_high);
        case 4: return SENSE_TRIP == output_level(true, g_thresholds.trip_active_high);
        case 5: return SENSE_BAND_160M == 1;
        case 6: return SENSE_BAND_80M == 1;
        case 7: return SENSE_BAND_40M == 1;
        case 8: return SENSE_BAND_20M == 1;
        case 9: return SENSE_BAND_15M == 1;
        case 10: return SENSE_BAND_10M == 1;
    }
    return false;
}

/* The three TX outputs read back at the commanded stage level (0 = all off, 1 = TX, 2 = TX+VCC,
   3 = TX+VCC+BIAS). Used by the sequencer walk. */
static bool diag_sequencer_stage_ok(unsigned char stage) {
    bool tx_ok = SENSE_TX == output_level(stage >= 1, g_thresholds.tx_active_high);
    bool vcc_ok = SENSE_TX_VCC == output_level(stage >= 2, g_thresholds.tx_vcc_active_high);
    bool bias_ok = SENSE_TX_BIAS == output_level(stage >= 3, g_thresholds.tx_bias_active_high);
    return tx_ok && vcc_ok && bias_ok;
}

static void diag_sequencer_apply(unsigned char stage) {
    set_tx_output(stage >= 1);
    set_tx_vcc_output(stage >= 2);
    set_tx_bias_output(stage >= 3);
}

/* CHECK 1 - outputs: assert -> hold -> verify-active -> deassert -> hold -> verify-inactive,
   once per output. Time-sliced because each hold is DIAG_HOLD_MS long. */
static void diag_outputs_step(unsigned int elapsed_ms) {
    unsigned char idx = g_diag_index;
    g_diag_elapsed_ms += elapsed_ms;
    if (g_diag_sub == 0) {
        diag_set_output(idx, true);
        g_diag_sub = 1;
        g_diag_elapsed_ms = 0;
        return;
    }
    if (g_diag_sub == 1) {
        if (g_diag_elapsed_ms < DIAG_HOLD_MS) return;
        if (!diag_sense_active(idx)) g_diag_result |= DIAG_OUTPUTS;
        diag_set_output(idx, false);
        g_diag_sub = 2;
        g_diag_elapsed_ms = 0;
        return;
    }
    if (g_diag_elapsed_ms < DIAG_HOLD_MS) return;
    if (diag_sense_active(idx)) g_diag_result |= DIAG_OUTPUTS;
    g_diag_index++;
    if (g_diag_index >= DIAG_OUTPUT_COUNT) {
        g_diag_phase = 1;
        g_diag_index = 0;
    }
    g_diag_sub = 0;
    g_diag_elapsed_ms = 0;
}

/* CHECK 2 - sequencer walk 0 -> 1 -> 2 -> 3 -> 0: apply, hold, verify each stage's outputs. */
static void diag_sequencer_step(unsigned int elapsed_ms) {
    g_diag_elapsed_ms += elapsed_ms;
    if (g_diag_sub == 0) {
        diag_sequencer_apply(g_diag_index);   /* 0..3, then index 4 = back to idle */
        g_diag_sub = 1;
        g_diag_elapsed_ms = 0;
        return;
    }
    if (g_diag_elapsed_ms < DIAG_HOLD_MS) return;
    if (!diag_sequencer_stage_ok(g_diag_index & 0x03)) g_diag_result |= DIAG_SEQUENCER;
    g_diag_index++;
    if (g_diag_index >= 4) {
        /* stage 4: walk back to idle and verify the amplifier is cold. */
        diag_sequencer_apply(0);
        g_diag_phase = 2;
        g_diag_index = 0;
    }
    g_diag_sub = 0;
    g_diag_elapsed_ms = 0;
}

/* CHECK 3 - LCD liveness. Best-effort: the panel bus is not read back, so "liveness" is a known
   pattern written for the operator to confirm. It cannot fail on a healthy board. */
static void diag_lcd_check(void) {
    lcd_write_byte_now(0x01, false);
    __delay_ms(2);
    lcd_set_cursor(0, 0);
    lcd_write_text("0123456789ABCDEF");
    lcd_set_cursor(1, 0);
    lcd_write_text("SELF-TEST");
}

/* CHECK 4 - settings-EEPROM round-trip: write a known pattern to a scratch address, read it back
   and compare byte-for-byte. The settings record itself (address 0) is not touched. */
static void diag_eeprom_check(void) {
    static const unsigned char pattern[8] = {0xA5, 0x5A, 0x00, 0xFF, 0x69, 0x96, 0x3C, 0xC3};
    unsigned char buffer[8];
    unsigned char index;
    if (!internal_eeprom_write(DIAG_EEPROM_ADDR, pattern, sizeof pattern)) {
        g_diag_result |= DIAG_EEPROM;
        return;
    }
    if (!internal_eeprom_read(DIAG_EEPROM_ADDR, buffer, sizeof buffer)) {
        g_diag_result |= DIAG_EEPROM;
        return;
    }
    for (index = 0; index < sizeof buffer; index++) {
        if (buffer[index] != pattern[index]) {
            g_diag_result |= DIAG_EEPROM;
            return;
        }
    }
}

/* Begin a run only when the amplifier is cold; force bypass first and reset the verdict. Cold
   means PTT not active and no latched fault. The outputs are re-forced to bypass before and after,
   so a diagnostic can never key the LDMOS. */
void diag_start(void) {
    if (g_diag_running || g_ptt_active || g_fault_latched) {
        return;
    }
    apply_bypass();
    g_diag_run_mask = g_diag_selected;
    g_diag_running = true;
    g_diag_done = false;
    g_diag_result = DIAG_OK;
    g_diag_phase = 0;
    g_diag_index = 0;
    g_diag_sub = 0;
    g_diag_elapsed_ms = 0;
    g_menu_changed = true;
}

bool diag_busy(void) {
    return g_diag_running;
}

bool diag_done(void) {
    return g_diag_done;
}

unsigned char diag_result(void) {
    return g_diag_result;
}

/* Advance the diagnostic by `elapsed_ms` ticks. Called once per main-loop pass while busy; every
   other subsystem is frozen, so nothing re-drives the outputs under test. */
void diag_tick(unsigned int elapsed_ms) {
    if (g_diag_phase >= DIAG_CHECK_COUNT) {
        apply_bypass();
        g_diag_running = false;
        g_diag_done = true;
        g_menu_changed = true;
        return;
    }
    /* Skip any phase whose check is not in the run mask (menu "run one" selection). */
    while (g_diag_phase < DIAG_CHECK_COUNT && !(g_diag_run_mask & (unsigned char)(1u << g_diag_phase))) {
        g_diag_phase++;
        g_diag_index = 0;
        g_diag_sub = 0;
        g_diag_elapsed_ms = 0;
    }
    if (g_diag_phase >= DIAG_CHECK_COUNT) {
        apply_bypass();
        g_diag_running = false;
        g_diag_done = true;
        g_menu_changed = true;
        return;
    }
    switch (g_diag_phase) {
        case 0: diag_outputs_step(elapsed_ms); break;
        case 1: diag_sequencer_step(elapsed_ms); break;
        case 2: diag_lcd_check(); g_diag_phase = 3; break;
        case 3: diag_eeprom_check(); g_diag_phase = 4; break;
    }
}
