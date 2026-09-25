# The TX Sequencer

**What this file is:** a complete, first-principles description of the transmit sequencer in the
PicAmpControl firmware - what it is, why it exists, what it does in order, and how that order
protects the two things that can be destroyed by getting it wrong: the LPF band relays and the
LDMOS output devices.

**Where the code is:** `firmware/src/main.c` (`update_tx_sequence()`,
`update_protection_state()`, `handle_ptt_transition()`, `apply_bypass()`,
`release_band_if_cold()`), with the output macros in `firmware/include/pin_map.h` and the settings
structure declared in the same file. Pin numbers are **not** repeated here - the single source of
truth is [hardware/PIC18F47Q10_pin_map_and_setup.md](hardware/PIC18F47Q10_pin_map_and_setup.md).

---

## 1. What the sequencer is

It is a **time-ordered output controller** for one transmit cycle. On key-down it brings up the
amplifier's three outputs in a fixed order with a configurable delay between each pair; on key-up it
tears them down in a fixed order; and at every instant in between it is the one place that decides
whether it is safe to have RF flowing through the LDMOS.

It is *not*:

- the RF path itself (that is the LPF relays, the T/R relay and the LDMOS stages);
- the protection hardware (the analogue comparators act independently - see §7);
- the band classifier (that is the frequency counter, see
  [first-dit-band-detection.md](first-dit-band-detection.md)).

It sits between them: it consumes "which band is safe to transmit on" from the classifier and "is
anything out of limits" from the protection logic, and it drives exactly three outputs plus the
band-select lines:

| Output | Purpose | Default polarity |
|---|---|---|
| `OUTPUT_TX` (the **T/R relay**) | connects the amplifier into the RF path instead of passing the antenna straight through | active-low |
| `OUTPUT_TX_VCC` | the LDMOS drain supply | active-low |
| `OUTPUT_TX_BIAS` | the LDMOS gate bias | active-low |
| `OUTPUT_BAND_160M` … `OUTPUT_BAND_10M` | one pin per LPF band relay (K1-K6) | active-high |

The three TX outputs are written through the `LAT` registers; the two places that must know what the
**hardware** actually did (`release_band_if_cold()` and the PTT COMPLETE check) read the matching
`SENSE_TX*` `PORT` bits instead, because reading a latch only echoes back what the firmware
commanded.

## 2. Why it exists

Three physical facts drive the whole design.

1. **A relay must not be switched onto a live RF path.** Moving an LPF relay while RF is flowing
   arcs the contacts and puts power through a filter that is mid-change. Worse, if the *band*
   selection moves while the amplifier is keyed, the LDMOS sees a mismatched load for the duration
   of the move. This is the "hot switch" the design refuses to allow.
2. **The amplifier must not be keyed on a band nobody has measured.** With no RF present the
   classifier reports its "no signal" default (160 m). Keying on that would put full drive into the
   wrong low-pass filter - the classic way to destroy a PA.
3. **Drain, gate bias and RF connection have an order.** The firmware applies them in the configured
   order and removes them in its own configured order, so the LDMOS is never left in an
   indeterminate state during a transition. On engage: RF path, then drain, then gate. On release:
   RF path first, then drain, then gate. On a trip: drain first, then the RF path and gate.

The delays between the stages are **user-configurable from 0 to 1000 ms in 5 ms steps, default
20 ms each** (`TX-VCC DLY` and `TX-BIAS DLY` on the LCD menu). They exist to give a relay or a
supply time to actually settle before the next thing happens.

## 3. The stage machine

`g_sequence_stage` is the whole state. It is published on the LCD and on the simulator trace, so the
numbers below are a contract - a bare "stage 4" is meaningless without its name.

| # | Name | Outputs while in this stage | Waiting for |
|---|---|---|---|
| 0 | `SEQ_IDLE` | everything off: RF path open, drain and gate off | a key-down, or the tail of a release |
| 1 | `SEQ_TX_ON` | **T/R relay closed**, drain and gate still off | `tx_vcc_delay_ms` |
| 2 | `SEQ_VCC_ON` | T/R relay closed, **drain up**, gate off | `tx_bias_delay_ms` |
| 3 | `SEQ_BIAS_ON` | all three up and **read back at the pins** = transmitting | key-up, or a trip |
| 4 | `SEQ_RELEASE_RELAYS` | **RF path opened**, drain still up, gate still up | `tx_vcc_delay_ms` |
| 5 | `SEQ_RELEASE_VCC` | **drain removed**, gate still up | `tx_bias_delay_ms`, then stage 0 |

Engage runs `0 -> 1 -> 2 -> 3`. Release runs `3 -> 4 -> 5 -> 0`, and a release from stage 2 unwinds
through the same path as stage 3 so a key-up in the middle of the ramp cannot leave the drain
asserted for the whole receive period. A key-up in stage 1 (`SEQ_TX_ON`) simply opens the relay and
returns to stage 0.

Every stage transition is a *counter*, not a `__delay_ms()`: the sequencer is called once per
approximately-1 ms Timer2 tick and increments `g_sequence_elapsed_ms`, so nothing in the firmware
blocks the main loop (the LCD, the ADC and the protection logic all keep running while a delay
counts out; hardware overcurrent protection is asynchronous and unaffected).

## 4. A complete sequence, step by step

### 4.1 Power-up and the startup inhibit

1. **Startup inhibit (about 1000 ms).** `apply_startup_inhibit()` forces bypass (`apply_bypass()`),
   holds the comparator-reset line low, drops any remembered band and clears `g_band_established`.
   The sequencer cannot leave bypass while `g_startup_inhibit` is set, and a key-down during this
   window is **ignored** - `handle_ptt_transition()` returns early, so there is no edge to act on.
2. When the inhibit expires the comparator-reset line is released (a single low-to-high transition
   signalling the hardware has settled). Only now is PTT actionable.

### 4.2 Key-down (PTT falls low)

PTT is **active-low**: the pin going low *is* the key-down. The sequence is:

3. **Ignore-if-inhibited check.** During the startup inhibit, nothing happens (§4.1).
4. **Latched basics, all in one pass** (`handle_ptt_transition(true)`): mark PTT active, force the
   stage back to `SEQ_IDLE`, clear the band-settle and verify timers, and **force bypass** before
   anything else. Forcing bypass first is deliberate: a re-key can arrive while the previous
   over is still unwinding with the drain still up, and every branch below can move the relay
   selection.
5. **Comparator reset pulse.** `start_comparator_reset()` holds the reset line low for **10 ms**.
   While it is active the sequencer is held in bypass with the stage at 0, so the TX sequence cannot
   begin underneath it. This pulse clears the hardware overcurrent comparator latch.
6. **Fault re-arm.** If the overcurrent comparator input is still asserted, **nothing is cleared and
   the amplifier stays disabled** - a live hardware fault cannot be bypassed by pressing PTT. If it
   is clear, the latched software fault state is cleared here (this is the *only* place a latched
   trip is cleared) and the state machine moves to `STATE_OPERATE`.
7. **Band decision, in priority order:**
   - *Live measurement already confirmed* - `freq_counter_band_confirmed()`: that band is fresher
     than anything remembered, so it wins, is remembered, and the relay settle timer starts.
   - *A remembered band exists* - first-dit: engage on it. But if the counter holds a **different**
     live measurement, the remembered band is discarded and the amplifier goes to bypass-snoop
     instead. The remembered band is also verified against the first usable measurement of this
     transmission (§4.3).
   - *Nothing known* - **bypass-snoop**: hold the amplifier in bypass (RF straight through, drain
     and gate off) and let the relay selection follow the incoming RF while the radio's first burst
     is measured.
8. **Snoop decode.** Once `freq_counter_band_confirmed()` is true, the band is remembered, the
   counter's band is **locked**, and the **relay settle timer** (`BAND_SETTLE_MS`, 20 ms) starts.
   The T/R relay stays open for that entire window: this is the guarantee that it never closes onto
   a relay that is still moving. Note that `band_confirmed()` - not "a signal is present" - is
   required, because after silence the 10 ms tick has already classified an empty gate as 160 m and
   that stale guess must never be locked.
9. **Stage 1 - `SEQ_TX_ON`.** With a settled, locked band, the sequencer locks the band, closes the
   T/R relay and starts the drain delay.
10. **Stage 2 - `SEQ_VCC_ON`.** After `tx_vcc_delay_ms` the drain supply is applied and the gate
    delay starts.
11. **Stage 3 - `SEQ_BIAS_ON`.** After `tx_bias_delay_ms` the gate bias is applied, and then the
    three outputs are **read back at the pins**. Only if all three are actually at their active
    levels does the stage advance to 3 and the "PTT COMPLETE" screen appear. A commanded level is
    not evidence that the hardware reached it.

At this point the amplifier is transmitting on a locked, settled band.

### 4.3 Holding the band while transmitting

12. **The band is frozen.** While locked, a new measurement does **not** move `current_band` and
    **does not** move the band-select outputs. That is what allows the filter to be a filter and not
    a moving target during a transmission.
13. **Verification of a remembered band.** If the engage came from the remembered band (no live
    measurement to back it - the radio had not started transmitting yet), the band is re-checked
    against the first usable measurement of this transmission. A mismatch that persists for
    `BAND_VERIFY_MS` (20 ms) forces bypass first, discards the lock, re-selects the measured band
    **cold**, and re-engages. If instead there is no usable measurement at all, the amplifier holds
    bypass rather than keying on an unverified band.
14. **Protection keeps running.** The SWR trips and the drain/current/temperature/overdrive trips
    are evaluated continuously (§6).

### 4.4 Key-up (PTT returns high)

15. **Stage 4 - `SEQ_RELEASE_RELAYS`.** The T/R relay opens immediately, taking the amplifier out of
    the RF path. The drain and gate are still on for `tx_vcc_delay_ms`.
16. **Stage 5 - `SEQ_RELEASE_VCC`.** The drain supply is removed. The gate bias is still on for
    `tx_bias_delay_ms`.
17. **Stage 0 - idle.** The gate bias is removed and the stage returns to `SEQ_IDLE`, and *then*
    `release_band_if_cold()` is called. The band lock is released **only if all three TX outputs read
    back inactive at the pins**. Until that is true the relay selection stays frozen, because the
    relays must not start following live RF while any part of the amplifier is still up.

The cycle is complete: the amplifier is cold, the RF path is straight through to the antenna, and
the band may follow the next measurement.

## 5. The invariant that ties it together

> **The LPF relay selection may only move while the amplifier is cold, and the amplifier may only
> key on a band that has been measured and settled.**

In code that is one rule with three consequences, all of them enforced by putting the amplifier in
bypass *before* the selection can change:

- `apply_bypass()` is the only "make it safe" primitive - it de-asserts the T/R relay, the drain and
  the gate.
- Any path that is about to let the selection move - restoring a remembered band, entering
  bypass-snoop, following live RF after a trip recovery - calls `apply_bypass()` first.
- `release_band_if_cold()` will not unlock the band until the pins confirm all three outputs are
  inactive.

## 6. How this protects the relays and the LDMOS

| Threat | What prevents it |
|---|---|
| T/R relay closes onto a still-moving LPF relay | the relay settle window (`BAND_SETTLE_MS`, 20 ms) is held in bypass before stage 1; the T/R relay is the *last* thing to close |
| An LPF relay moves while RF is flowing | the band lock freezes the selection for the whole transmission, and the lock is only released when the pins confirm the amplifier is cold |
| Keying into the wrong filter | the amplifier will not leave bypass without a **confirmed** band; with no measurement it stays in bypass and refuses to transmit |
| Keying on a stale remembered band after a band change | the remembered band is verified against the first usable measurement, with a mismatch forcing a cold re-select |
| A transient/glitch causing RF into an open or moving path | the 10 ms comparator-reset window holds bypass with the stage forced to 0, so the sequence cannot start under it |
| A relay driver latching up when an unrelated write touches the same port | outputs are written via `LAT`, never via a read-modify-write of `PORT`; the LCD data lines share PORTC with the TX outputs, so this is a live hazard, not a theoretical one |
| The firmware *believing* it has shut down when the hardware has not | the two safety confirmations (`release_band_if_cold()`, PTT COMPLETE) read the `SENSE_*` `PORT` bits, not the latches |

## 7. Trips: the sequencer's emergency path

Protection is evaluated every pass and can override the sequencer at any point.

- **Which trips are armed.** The SWR trips are armed **only in stages 1-3** - the stages that hold
  the T/R relay closed. During bypass the RF bridges see nothing meaningful (the relay selection may
  legitimately be moving), so an SWR reading taken then is not evidence of anything. The
  overcurrent, current, temperature, overdrive and drain-peak trips are **not** gated: they are
  always live.
- **On a trip** the drain supply is removed **immediately**, the trip output is asserted, and 5 ms
  later the T/R relay and the gate bias are dropped. The fault is **latched**: it stays latched, and
  the amplifier stays disabled, even after the condition itself goes away.
- **Clearing a latch** happens only on the next PTT re-arm edge, and only after the 10 ms comparator
  reset pulse and only if the hardware overcurrent comparator is clear (§4.2, step 6). This is why
  the normal bench action is "release, then key again".
- **Temperature is the one exception**: a temperature trip clears itself once the reading falls
  below the trip point minus the recovery hysteresis; it still needs a band re-established before it
  may key.
- **Hardware protection is independent.** The overdrive, drain-peak and overcurrent comparators
  combine into one active-high `INPUT_HARD_FAULT` signal, and the overcurrent comparator has its own
  asynchronous path. The firmware's thresholds *supplement* those comparators; they never replace
  them, and no firmware state can defeat them.
- **The panel is the read-out.** The trip screen always prints the fault **name**; the stage is shown
  as `TX <STAGE-NAME>` while keyed, and the status page shows `SEQ <STAGE-NAME>` whenever the
  sequence is not idle. With no test harness attached the LCD is the only instrument you have, so a
  stall and a trip are both legible from it.

## 8. Configuration, defaults and what is not implemented

- `TX-VCC DLY`, `TX-BIAS DLY`: 0-1000 ms in 5 ms steps, default 20 ms. These set the length of
  stages 1, 2, 4 and 5.
- `TX ACTIVE`, `TX-VCC POL`, `TX-BIAS POL`: per-output active-high/active-low, default **active-low**.
- `FAN POL`: the fan output's polarity is configurable and the output exists, but **temperature-driven
  fan control is not implemented yet** - the firmware initialises the fan output inactive and never
  asserts it.
- The sequencer's delays are **locked out from editing during transmit**, so the timing cannot be
  changed underneath a running sequence.
- The sequencer does not read the band-select outputs back; it reads back only the three TX outputs,
  and those only at the two points where a safety decision depends on it.

## 9. The TX self-test: the amplifier's own verdict

While PTT is low the firmware tests **itself**, once per 10 ms counter gate (`tx_selftest_run()`, from
the same place `freq_counter_tick_10ms()` samples TMR1), and reports its own verdict. It does not
measure the RF chain; it answers one question: **is the firmware where the PTT and the sequencer say
it should be?**

- PTT is low and a stage claims to be running.
- The outputs that stage says are asserted are actually asserted **on the pin** (`SENSE_*`, not the
  latch) - the same rule the PTT-COMPLETE confirmation follows.
- The band lock is still backed by a measurement. That is not an extra frequency test: the lock is the
  sequencer's own justification for holding the T/R relay closed.

**Granular, and reported together.** Every failing check is a bit in `g_selftest_reason`
(`tx_selftest_reason_t` in `main.c`), and several failures are reported at once, ORed:

| bit | name on the panel | what it means while keyed |
| --- | --- | --- |
| 0x01 | `NO_RF` | the counter saw no pulses at all in the gate window |
| 0x02 | `BAD_BAND` | pulses, but the frequency is outside the classifier's 1000-32000 kHz range |
| 0x04 | `LOCK_LOST` | pulses in range, but no stable measurement backs the frozen band selection |
| 0x08 | `BAND_CHG` | a usable measurement on a DIFFERENT band: the rig moved while keyed |
| 0x10 | `NO_LOCK` | keyed with no band lock held at all |
| 0x20 | `TX_SENSE` | an output the stage claims is asserted is not reading back asserted |
| 0x40 | `STALLED` | the band IS established, but the sequence has not reached BIAS-ON |
| 0x80 | `NO_BAND` | keyed and nothing has decoded - correctly still in bypass, but it cannot say where it is |

**A check must HOLD to count** - see the next subsection for the mechanism, the counters and the
numbers.

### The 200 ms hold, precisely

The hold is `LOCK_LOSS_UNKEYABLE_MS` (200) in `firmware/src/main.c`. It is the only timing the
self-test has, and it appears in exactly three places, all the same number on purpose:

1. **The tick that counts it.** `tx_selftest_run()` is evaluated on the 10 ms counter gate
   (`TX_SELFTEST_TICK_MS`, beside `freq_counter_tick_10ms()`), so a check can never know more than the
   counter window it is reading, and the verdict costs one evaluation per gate instead of one per
   millisecond. Each evaluation produces one `failing` mask of bits.
2. **The per-check counters.** `g_selftest_hold[TX_SELFTEST_CHECK_COUNT]` is one consecutive-ms counter
   per check, indexed by bit position, advanced by `TX_SELFTEST_TICK_MS`. For every bit set in
   `failing` the matching counter advances (capped at the window); for every bit clear that counter is
   **reset to 0**. So a counter is not "how long since the last good gate" but "how long this condition
   has held without a break", and each check resets only its own.
3. **The expiry.** When a counter reaches 200, that check's bit is ORed into `g_selftest_reason`,
   `g_selftest_failed` is set, and `tx_selftest_run()` takes the action itself (bypass, band unlock,
   snoop - the sequencer picks it up on its next tick). Every counter is zeroed on the way out, so a
   condition that is still present must hold for another full 200 ms before it acts again - and
   re-acting is harmless, because the amplifier is already in bypass by then.

Consequences worth stating, because each one is a way to get this wrong:

- A check that fails for 199 ms and then passes **never flags**; a check that passes for any length of
  time **never clears a reason that has already latched**. The reason is held until the next key-down
  (`tx_selftest_reset()`), not until the next good sample.
- Nothing else in the self-test is timed. There is no second window, no per-check timeout and no
  delay between the expiry and the action.
- `g_lock_loss_ms` only **publishes** the longest-holding failing check (milliseconds) for the test
  harness; it is not what makes the decision.
- The hold is why a keyed amplifier does not drop out of transmit on one bad gate: a torn counter
  read (`T1CON.nSYNC = 1` makes TMR1 genuinely asynchronous), one empty gate window, or one gate with
  a relay driver still slewing can all happen legitimately. 200 ms is the other side of the same
  trade - longer than a dit, far shorter than anything that could damage the LDMOS - and it is the
  same window the undefined/unkeyable state used before the self-test existed, so the bench figure
  still applies.
- **Do not move this onto the per-millisecond path.** Measured 2026-09-25: evaluating the self-test
  every 1 ms lengthened each main-loop pass enough that the SWR1 scenario's trip window was missed
  (the amplifier sat keyed at BIAS-ON with the bridge deliberately over-threshold and never tripped);
  compiling the call out made it pass, and moving it onto the 10 ms gate made it pass. The
  protection chain is evaluated once per main-loop pass, so anything added to the per-millisecond path
  starves it.
- **Trips do not do this.** A protection trip latches on the sample that sees it; only the self-test
  waits, because "the firmware cannot vouch for this transmission" is a judgement that needs the
  condition to persist, not an event.

**The action, and the panel.** When a check first latches, the amplifier is in a transmission it cannot
vouch for: the T/R relay is closed on a band whose only justification has gone. The firmware opens the
RF path (bypass), unlocks the band so the selection can follow live RF again, and requires a fresh
decode before it will key. The panel then reads:

```
STATE: UNDEFINED
LOCK_LOST+NO_RF
```

Line 1 is the `+`-joined reason mask (truncated to the 16 columns with a trailing `+`), and it is never
blank - `OK` when nothing failed, `UNKNOWN` for a code the table does not know. This is **not** a
latched trip: it clears itself as soon as a fresh decode verifies a band, and unlike a trip it needs no
operator action. The **reason**, however, is held until the next key-down, so it can still be read
after the amplifier has recovered. The check is deliberately not in an interrupt:
`freq_counter_tick_10ms()` is where TMR1 is read and reset, so no check can know more than that 10 ms
gate, and the action is far too heavy for ISR context.
## 10. How this is tested

The machine is exercised in the simulator, and the invariants - not just the happy path - are
asserted (`tools/simulate/trace_ptt_sequence.py`):

- the ordered engage and release, including the 5 ms windows in stages 4 and 5 (`SEQ_RELEASE_RELAYS`
  is short by design and needs 1 ms sampling to be observed at all);
- **band changes are cold**: no band-select output may change while the amplifier is keyed;
- the T/R relay must close only after the band relay has settled;
- no keying on an unlocked band;
- every trip path raises the outputs in the shutdown order and latches.

Every scenario reads the **firmware's own verdict** (`g_selftest_failed` / `g_selftest_reason`) rather
than re-deriving it from the model: for each band either the keyed band lock is verified, or the
firmware named the reason it refused to key (and a flag with no name is a failure in its own right -
the panel is the only read-out on the bench). No **keyed** `g_fc_status.frequency_khz` reading is
asserted: the firmware resets TMR1 on every 10 ms gate and nothing in the simulator clocks it, so that
reading measures the model's pacing, not the firmware (2026-09-25).

This document describes intended behaviour. The firmware is the source of truth; if the two ever
disagree, the firmware is right and this file is the bug. Related reading:
[keying-and-band-selection.md](keying-and-band-selection.md) (the band model),
[steves-sequence.md](steves-sequence.md) (the operator's own statement of the key-down rule),
[project-architecture.md](project-architecture.md) (the system around this).
