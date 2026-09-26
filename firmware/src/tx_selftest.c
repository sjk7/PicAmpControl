#include <stdbool.h>
#include "../include/pin_map.h"
#include "../include/settings.h"
#include "../include/state.h"
#include "../include/freq_counter.h"
#include "../include/outputs.h"
#include "../include/tx_selftest.h"

/* TX self-test causes. Bit flags, exactly like the trip causes and for the same reason: more than
   one check can fail at once, so the mask reports them all instead of picking a winner.

   The mask is a RECORD of the current key-down, not a latch: it is held until the NEXT key-down, so
   the operator can always read why the amplifier refused to key. Every check is one question about
   where the firmware is; nothing here re-tests the RF chain.

   The VALUES are a contract with the simulator harnesses (SELFTEST_REASON_NAMES in
   tools/simulate/trace_ptt_sequence.py) - keep the bit positions, the names and their ORDER aligned
   with that table. */

/* One name per cause, indexed by bit position, so this array and the tx_selftest_reason_t enum in
   state.h must stay in the same order. Deliberately short: the panel has ONE 16-column line for the
   WHOLE combined reason, and with '+' separators two names have to fit in it. */
static const char *const TX_SELFTEST_NAMES[] = {
    "NO_RF",     /* TX_SELFTEST_NO_RF      0x0001 */
    "BAD_BAND",  /* TX_SELFTEST_BAD_BAND   0x0002 */
    "LOCK_LOST", /* TX_SELFTEST_LOCK_LOST  0x0004 */
    "BAND_CHG",  /* TX_SELFTEST_BAND_CHG   0x0008 */
    "NO_LOCK",   /* TX_SELFTEST_NO_LOCK    0x0010 */
    "TX_SENSE",  /* TX_SELFTEST_TX_SENSE   0x0020 */
    "STALLED",   /* TX_SELFTEST_STALLED    0x0040 */
    "NO_BAND",   /* TX_SELFTEST_NO_BAND    0x0080 */
    "REL_STUCK"  /* TX_SELFTEST_REL_STUCK  0x0100 */
};

/* Append `text` to the NUL-terminated `buffer`, inserting a '+' first when it is not the first
   name, and never writing more than `limit` characters (the truncation marker is the caller's). */
static bool tx_selftest_text_append(char *buffer, unsigned char *used, unsigned char limit, const char *text) {
    unsigned char length = 0;
    while (text[length] != '\0') {
        length++;
    }
    if (*used == 0) {
        if (length > limit) {
            return false;
        }
    } else {
        if ((unsigned int)*used + 1U + length > limit) {
            return false;
        }
        buffer[(*used)++] = '+';
    }
    while (*text != '\0') {
        buffer[(*used)++] = *text++;
    }
    buffer[*used] = '\0';
    return true;
}

unsigned char tx_selftest_reason_text(unsigned int reason, char *buffer, unsigned char size) {
    unsigned char used = 0;
    unsigned char index;
    unsigned char limit;
    bool wrote = false;
    bool truncated = false;

    if (size == 0) {
        return 0;
    }
    buffer[0] = '\0';
    if (size < 3) {
        return 0;   /* no room for even a one-character name plus the marker and the NUL */
    }
    limit = (unsigned char)(size - 2);   /* the last column is the truncation marker's */

    for (index = 0; index < TX_SELFTEST_CHECK_COUNT; index++) {
        if ((reason & (unsigned int)(1u << index)) == 0) {
            continue;
        }
        if (!tx_selftest_text_append(buffer, &used, limit, TX_SELFTEST_NAMES[index])) {
            truncated = true;
            break;
        }
        wrote = true;
    }
    if (!wrote) {
        tx_selftest_text_append(buffer, &used, (unsigned char)(size - 1),
                                reason == TX_SELFTEST_OK ? "OK" : "UNKNOWN");
        return used;
    }
    if (truncated) {
        buffer[used++] = '+';
        buffer[used] = '\0';
    }
    return used;
}

void tx_selftest_reset(void) {
    unsigned char index;
    g_selftest_failed = false;
    g_selftest_reason = TX_SELFTEST_OK;
    g_lock_loss_ms = 0;
    g_selftest_unkey_ms = 0;
    /* A new key-down also releases the stuck-output latch: the operator is explicitly re-keying,
       so the previous undefined/unkeyable state is gone. */
    g_unkeyable = false;
    for (index = 0; index < TX_SELFTEST_CHECK_COUNT; index++) {
        g_selftest_hold[index] = 0;
    }
}

/* How long an unkey may take before it counts as stuck. The two release stages are the configured
   VCC and bias delays, so the window is twice their sum, plus a margin for a relay that is still
   moving and for the TX_SELFTEST_TICK_MS granularity this check rides on. */
static unsigned int tx_selftest_unkey_window(void) {
    return ((unsigned int)g_thresholds.tx_vcc_delay_ms + g_thresholds.tx_bias_delay_ms) * 2U + 20U;
}

/* The hold window per check bit, in ms. Indexed by bit position (same order as the enum). BAD_BAND
   (bit 1) latches on the first gate; TX_SENSE (bit 5) gets one extra gate so a relay driver still
   slewing on the gate after set_tx_output() is not a false trip. Everything else keeps the long
   LOCK_LOSS_UNKEYABLE_MS debounce. */
static unsigned int tx_selftest_window(unsigned char index) {
    switch (index) {
        case 1: return 0U;                        /* TX_SELFTEST_BAD_BAND: act immediately */
        case 5: return TX_SELFTEST_TICK_MS * 2U;  /* TX_SELFTEST_TX_SENSE: tolerate one slewing gate */
        default: return LOCK_LOSS_UNKEYABLE_MS;
    }
}

/* Advance the hold counters for the checks failing on this evaluation, latch the ones that have held
   for LOCK_LOSS_UNKEYABLE_MS, and take the remedy. Shared by the keyed checks and the unkey check,
   so there is exactly one window, one latch and one action no matter which half noticed the fault. */
static void tx_selftest_apply(unsigned int failing) {
    unsigned char index;
    unsigned int longest = 0;
    unsigned int latched_now = 0;

    for (index = 0; index < TX_SELFTEST_CHECK_COUNT; index++) {
        unsigned int bit = (unsigned int)(1u << index);
        unsigned int window = tx_selftest_window(index);
        if (failing & bit) {
            if (g_selftest_hold[index] < window) {
                g_selftest_hold[index] += TX_SELFTEST_TICK_MS;
                if (g_selftest_hold[index] > window) {
                    g_selftest_hold[index] = window;
                }
            }
            if (g_selftest_hold[index] > longest) {
                longest = g_selftest_hold[index];
            }
            if (g_selftest_hold[index] >= window) {
                g_selftest_reason |= bit;
                latched_now |= bit;
            }
        } else {
            g_selftest_hold[index] = 0;
        }
    }
    g_lock_loss_ms = longest;

    if (g_selftest_reason != TX_SELFTEST_OK) {
        g_selftest_failed = true;
    }
    if (latched_now == 0) {
        return;
    }

    /* THE ACTION, split by cause (user instruction, 2026-09-25):
       * a FATAL check latches the undefined/unkeyable state - an unknown/out-of-spec measurement
         (BAD_BAND) or an output that did not obey its command (TX_SENSE, STALLED, REL_STUCK) must
         not be re-keyed into, because re-keying would re-engage the same fault, the one case that can
         damage the LDMOS. The amplifier stays in bypass until the operator keys again.
       * a recoverable check folds back: open the RF path, unlock the band so the selection can follow
         live RF again, and let the bypass-snoop path re-select the next valid measurement and key
         once more. */
    bool permanent = g_unkeyable || (latched_now & TX_SELFTEST_LATCH_MASK) != 0;

    apply_bypass();
    freq_counter_unlock_band();
    invalidate_established_band();
    g_sequence_stage = SEQ_IDLE;
    g_state = STATE_BYPASS_SNOOP;

    if (permanent) {
        g_unkeyable = true;
        g_snoop_active = false;
    } else {
        g_snoop_active = true;
    }

    /* Restart every window: a condition that is still there must hold for another full window before
       it acts again, so the action cannot repeat faster than the window and the panel's reason mask is
       the only thing that accumulates. */
    for (index = 0; index < TX_SELFTEST_CHECK_COUNT; index++) {
        g_selftest_hold[index] = 0;
    }
    g_lock_loss_ms = 0;
}

void tx_selftest_run(void) {
    freq_counter_status_t status;
    rf_band_t measured;
    unsigned int failing = TX_SELFTEST_OK;
    unsigned char index;

    if (g_startup_inhibit || g_comparator_reset_active || g_fault_latched) {
        /* Nothing this self-test is about is running (still coming up, in the comparator-reset window,
           or a trip is latched). A LATCHED TRIP is in this list on purpose: a tripped amplifier is not
           transmitting, so its stage being forced idle is not a self-test failure. The REASON is
           deliberately left alone here: it is held until the next key-down so the operator can still
           read it after unkeying. */
        for (index = 0; index < TX_SELFTEST_CHECK_COUNT; index++) {
            g_selftest_hold[index] = 0;
        }
        g_lock_loss_ms = 0;
        g_selftest_unkey_ms = 0;
        return;
    }

    if (!g_ptt_active) {
        /* THE UNKEY. A release is the half the operator can least afford to be lied to about: the
           amplifier must unwind in order and end cold. REL_STUCK is raised when the unwind does not
           finish in the window, when the bias is dropped while TX_VCC is still asserted, or when the
           sequence reports idle with an output still asserted on the pin. */
        if (g_sequence_stage == SEQ_RELEASE_RELAYS || g_sequence_stage == SEQ_RELEASE_VCC) {
            if (g_selftest_unkey_ms < 0xFFFFU) {
                g_selftest_unkey_ms += TX_SELFTEST_TICK_MS;
            }
            if (g_selftest_unkey_ms > tx_selftest_unkey_window()) {
                failing |= TX_SELFTEST_REL_STUCK;
            }
            if (SENSE_TX_VCC == output_level(false, g_thresholds.tx_vcc_active_high) &&
                SENSE_TX_BIAS != output_level(false, g_thresholds.tx_bias_active_high)) {
                failing |= TX_SELFTEST_REL_STUCK;
            }
        } else {
            g_selftest_unkey_ms = 0;
            if (g_sequence_stage == SEQ_IDLE &&
                (SENSE_TX != output_level(false, g_thresholds.tx_active_high) ||
                 SENSE_TX_VCC != output_level(false, g_thresholds.tx_vcc_active_high) ||
                 SENSE_TX_BIAS != output_level(false, g_thresholds.tx_bias_active_high))) {
                failing |= TX_SELFTEST_REL_STUCK;
            }
        }
        tx_selftest_apply(failing);
        return;
    }

    if (g_sequence_stage > SEQ_BIAS_ON) {
        /* Keyed while the release stages are somehow still running: nothing coherent to verify. */
        tx_selftest_apply(TX_SELFTEST_OK);
        return;
    }

    g_selftest_unkey_ms = 0;

    freq_counter_get_status(&status);
    measured = freq_counter_measured_band();

    /* Is the band lock still justified? It is the sequencer's own reason for closing the T/R relay,
       so it is the first thing that has to hold. */
    if (status.raw_pulses == 0) {
        failing |= TX_SELFTEST_NO_RF;
    } else if (status.frequency_khz < 1000U || status.frequency_khz > 32000U) {
        failing |= TX_SELFTEST_BAD_BAND;
    } else if (status.band_locked) {
        if (measured == BAND_OUT_OF_SPEC) {
            failing |= TX_SELFTEST_LOCK_LOST;
        } else if (measured != status.locked_band) {
            failing |= TX_SELFTEST_BAND_CHG;
        }
    }
    if (!status.band_locked) {
        failing |= TX_SELFTEST_NO_LOCK;
    }

    /* Are the outputs the running stage claims actually asserted? SENSE_* reads the PIN, not the
       latch (pin_map.h), so this catches a driver that never came up as well as a wrong command. */
    if (g_sequence_stage >= SEQ_TX_ON && g_sequence_stage <= SEQ_BIAS_ON) {
        if (SENSE_TX != output_level(true, g_thresholds.tx_active_high) ||
            (g_sequence_stage >= SEQ_VCC_ON &&
             SENSE_TX_VCC != output_level(true, g_thresholds.tx_vcc_active_high)) ||
            (g_sequence_stage >= SEQ_BIAS_ON &&
             SENSE_TX_BIAS != output_level(true, g_thresholds.tx_bias_active_high))) {
            failing |= TX_SELFTEST_TX_SENSE;
        }
    }

    /* Is the sequence where it should be? Keyed and not at BIAS-ON for the whole window is either
       a band that was never established (NO_BAND) or a band that IS established and whose engage is
       not completing (STALLED). */
    if (g_sequence_stage != SEQ_BIAS_ON) {
        failing |= g_band_established ? TX_SELFTEST_STALLED : TX_SELFTEST_NO_BAND;
    }

    tx_selftest_apply(failing);
}
