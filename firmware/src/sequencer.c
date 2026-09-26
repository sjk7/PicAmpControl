#include <stdbool.h>
#include "../include/pin_map.h"
#include "../include/settings.h"
#include "../include/state.h"
#include "../include/freq_counter.h"
#include "../include/outputs.h"
#include "../include/tx_selftest.h"
#include "../include/menu.h"
#include "../include/sequencer.h"

/* The TX sequencer: PTT transition handling and the per-millisecond engage/release state
   machine. The band-memory and bypass-snoop logic lives here because it is the sequencer's own
   justification for closing the T/R relay. */

void handle_ptt_transition(bool ptt_asserted) {
    if (g_startup_inhibit)
        return; // Ignore PTT changes until system settles (RC1 low)
    if (ptt_asserted) {
        g_ptt_active = true;
        g_sequence_stage = 0;
        /* A new key-down is a new verdict: the previous key-down's self-test reason is dropped here
           and nowhere else, after it has been on the panel for as long as the operator needed. */
        tx_selftest_reset();
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
            /* The counter confirmed a live band, so the band IS verified: the undefined/unkeyable
               interlock has done its job. */
            g_unkeyable = false;
            g_lock_loss_ms = 0;
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
            g_unkeyable = false;
            g_lock_loss_ms = 0;
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

    /* The self-test is NOT called here: it runs on the 10 ms counter gate beside
       freq_counter_tick_10ms(), because its verdict is a property of the gate window and its work must
       not lengthen this per-millisecond path (see TX_SELFTEST_TICK_MS). */

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
        /* A fresh decode means the band IS verified again, so the undefined/unkeyable interlock has
           done its job and comes off. */
        g_unkeyable = false;
        g_lock_loss_ms = 0;
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
        if (g_unkeyable) {
            /* A fatal self-test check latched the undefined/unkeyable state: the amplifier must not
               re-engage until the operator keys again. Hold bypass, leave the sequence idle. */
            apply_bypass();
            g_sequence_stage = SEQ_IDLE;
            return;
        }
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
