#!/usr/bin/env python3
"""Standalone proof of the first-dit band-detection model.

Spec: docs/first-dit-band-detection.md

Runs one MDB session against out/My_Pic_Project/default.elf (build Debug first - mdb
needs the debug symbols) and proves, clause by clause:

  (a) PTT with no decoded band latches PTT but holds the amplifier in bypass: every TX
      output stays inactive and the band is never locked.
  (b) The first RF burst is decoded *in bypass*: the LPF relays are selected, the band is
      remembered, and only then does active TX engage on that band.
  (c) The next PTT on the same band engages immediately from the remembered band, with
      NO RF at all in that window (so no fresh snoop can be responsible).
  (d) After BAND_CACHE_IDLE_TIMEOUT_MS of inactivity the cache is dropped and the next
      PTT goes back to bypass-snoop.
  (e) A different band on the next first dit is re-detected and re-selected.
  (f) Hot-switch fault injection: re-key during the release ramp with a deliberately wrong
      cached band; the relays may only move once the amplifier has been forced into bypass.
  (g) Operator changed bands and keyed straight away (no RF at keydown, so the remembered band
      was used blind): the first measurement of the transmission must catch the mismatch, fold
      the amplifier back to bypass, re-select the LDMOS cold and re-engage on the real band.

It also enforces the safety invariants that make first-dit safe, over every sample of the
whole session (see validate_no_hot_switch):

  I1  no band-select change between two consecutive keyed samples: the relay selection is
      frozen for the whole keyed run
  I2  the amplifier is only ever keyed while the band is locked
  I3  while bypass-snooping, every TX output is inactive
  I4  band-select outputs always agree with the firmware's current_band
  I5  every observed band-select change is seen with the amplifier cold: the first sample
      carrying a new selection has every TX output inactive, and the keying that follows it
      is a strictly later sample (the decode path holds BAND_SETTLE_MS of bypass so the
      amplifier is never keyed into a relay that is still moving)

Simulator caveats (see TESTING.md):
  * Timer1's external clock is not modelled, so the "first RF burst" is injected by writing
    TMR1H/TMR1L directly, exactly as tools/simulate/trace_ptt_sequence.py does. The T1CKI
    pin, PPS routing and prescaler are therefore NOT covered here.
  * mdb cannot write a C variable by symbol name in this version (it fails with
    `For input string: "<addr> "`), so the two fault-injection writes below address the
    variables through out/My_Pic_Project/default.sym. Regression-tested 2026-09-21.
  * Simulating the full BAND_CACHE_IDLE_TIMEOUT_MS (60 s) would need ~480M instructions,
    which is far too slow (~6 min of wall clock for this one clause). Clause (d) therefore
    proves the timer really advances 1 ms/ms and then injects an idle count just below the
    threshold, so the real expiry boundary runs in the firmware rather than in the harness.

Usage:
    python3 tools/simulate/test_first_dit.py
    python3 tools/simulate/test_first_dit.py --csv
"""
import sys
from contextlib import contextmanager
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent.parent
sys.path.insert(0, str(TOOLS_DIR))

# Reuse the one MDB launcher (process-group cleanup, timeout handling, stderr capture), the
# one transcript parser, and the one set of band-selection invariants rather than keeping
# second copies of any of them.
import trace_ptt_sequence as harness  # noqa: E402
from first_dit_invariants import (  # noqa: E402
    BAND_PINS, TX_PINS, describe, keyed, millis, selected_band_pin,
)
import first_dit_invariants as inv  # noqa: E402

ELF_PATH = REPO_ROOT / "out" / "My_Pic_Project" / "default.elf"
SYM_PATH = REPO_ROOT / "out" / "My_Pic_Project" / "default.sym"
DEVICE = "PIC16F18875"

INSTRUCTIONS_PER_MS = 8000  # 32 MHz / 4 = 8 MIPS

PTT_PIN = "RC0"
SETTLE_PIN = "RC1"
PINS = [PTT_PIN, SETTLE_PIN] + TX_PINS + BAND_PINS
fmt = describe

IDLE_TIMEOUT_MS = 60000  # BAND_CACHE_IDLE_TIMEOUT_MS in firmware/src/main.c
STATE_BYPASS_SNOOP = 6   # STATE_BYPASS_SNOOP in firmware/src/main.c (appended last)

STATE_VARS = [
    "g_startup_inhibit", "g_comparator_reset_active", "g_fault_latched",
    "g_ptt_active", "g_sequence_stage", "g_state",
    "g_snoop_active", "g_band_cache_valid", "g_band_cache_band", "g_band_cache_idle_ms",
    "g_fc_status.current_band", "g_fc_status.band_locked", "g_fc_status.frequency_khz",
]
SYSTEM_SYMBOLS = ["g_band_cache_idle_ms", "g_band_cache_band"]


def symbol_address(name: str) -> int:
    """Read a variable's data-space address from the linker symbol file.

    `print /a <var>` is broken in this mdb build and `write <var> <value>` fails with
    `For input string: "<addr> "`, so fault injection has to go through `write /r <addr>`.
    """
    if not SYM_PATH.exists():
        sys.exit(f"error: {SYM_PATH} not found - build the firmware first")
    for line in SYM_PATH.read_text().splitlines():
        fields = line.split()
        if fields and fields[0] == f"_{name}":
            return int(fields[1], 16)
    sys.exit(f"error: symbol {name} not found in {SYM_PATH}")


class Builder:
    def __init__(self, addrs):
        self.addrs = addrs
        self.lines = [
            f"device {DEVICE}", "hwtool sim", f"program {ELF_PATH}",
            # Safe idle stimulus: no SWR, mid-scale NTC, no current/overdrive/drain,
            # hardware overcurrent fault clear, encoder contacts released.
            "write pin RA0 0v", "write pin RA1 0v", "write pin RA2 0v", "write pin RA3 0v",
            "write pin RA5 2.5v", "write pin RB1 0v", "write pin RB2 0v", "write pin RB3 0v",
            "write pin RB4 0v", "write pin RC2 5v", "write pin RB0 5v", "write pin RB6 5v",
        ]
        self.sample_count = 0
        self.spans = {}

    def _sample(self):
        for pin in PINS:
            self.lines.append(f"print pin {pin}")
        for var in STATE_VARS:
            self.lines.append(f"print {var}")
        self.sample_count += 1

    def step(self, count, ms=10):
        for _ in range(count):
            self.lines.append(f"Stepi {ms * INSTRUCTIONS_PER_MS}")
            self._sample()

    def inject(self, freq_khz):
        counts = int(round((freq_khz * 1000.0) / 400.0))
        self.lines.append(f"write TMR1L 0x{counts & 0xFF:02X}")
        self.lines.append(f"write TMR1H 0x{(counts >> 8) & 0xFF:02X}")

    def inject_step(self, freq_khz, count, ms=10):
        for _ in range(count):
            self.inject(freq_khz)
            self.step(1, ms)

    def write_u8(self, name, value):
        self.lines.append(f"write /r 0x{self.addrs[name]:03X} 0x{value & 0xFF:02X}")

    def write_u16(self, name, value):
        self.lines.append(f"write /r 0x{self.addrs[name]:03X} "
                          f"0x{value & 0xFF:02X} 0x{(value >> 8) & 0xFF:02X}")

    def ptt(self, asserted):
        self.lines.append(f"write pin {PTT_PIN} {'0v' if asserted else '5v'}")

    def pin(self, name, value):
        self.lines.append(f"write pin {name} {value}")

    @contextmanager
    def phase(self, name):
        start = self.sample_count
        yield
        self.spans[name] = (start, self.sample_count)


def build_script(addrs):
    b = Builder(addrs)
    b.ptt(False)
    # Startup inhibit is 1000 ms counted from when the main loop's ms tick starts; 1050 ms
    # of simulated time also covers the LCD/ADC init before the loop.
    with b.phase("startup"):
        b.step(105)

    with b.phase("a_ptt_without_band"):
        # PTT drops with no RF at all: no band can be decoded.
        b.ptt(True)
        b.step(10)

    with b.phase("b_first_burst"):
        # The radio's first RF burst (20m), still with PTT held down. Sampled every 1 ms so
        # the relay move, the BAND_SETTLE_MS bypass window and the keying that follows are
        # separately observable. Injection stops once the band is locked.
        b.inject_step(14000, 25, ms=1)
        b.step(65, ms=1)

    with b.phase("c_warm_start"):
        b.ptt(False)
        b.step(10)              # release ramp unwinds; cache must survive
        b.ptt(True)
        b.step(40, ms=1)        # 1 ms resolution; no TMR1 writes anywhere in this phase
        # Release during sequencer stage 2 (TX + TX_VCC up, bias still ramping): TX_VCC
        # must still be spun down and the band must stay locked until the amplifier is cold.
        b.ptt(False)
        b.step(10)

    with b.phase("d_timeout"):
        b.ptt(False)
        b.step(10)
        # Inject an idle count just below the threshold (the real 60 s is not affordable
        # to simulate: 60 s x 8 MIPS = 480M instructions) and let the firmware's own
        # threshold comparison expire the cache.
        b.write_u16("g_band_cache_idle_ms", IDLE_TIMEOUT_MS - 20)
        b.step(1, ms=1)         # read the injected count back
        b.step(3)               # cross the threshold
        b.ptt(True)
        b.step(8)               # no RF: must snoop again

    with b.phase("e_band_change"):
        b.inject_step(7000, 25, ms=1)   # operator moved to 40m
        b.step(65, ms=1)

    with b.phase("f_hot_switch_attempt"):
        # Fault injection: pretend the remembered band is wrong (15m) and then re-key
        # during the release ramp, while TX_VCC/TX_BIAS are still asserted. The relays
        # must not move until the amplifier is cold.
        b.write_u8("g_band_cache_band", 5)
        b.ptt(False)
        b.step(3, ms=5)         # 15 ms after release: TX off, TX_VCC and TX_BIAS still on
        b.ptt(True)
        b.step(14, ms=5)

    with b.phase("g_band_change_foldback"):
        # The operator changed bands and keyed straight away, so the remembered band was used
        # blind (there was no RF to verify it against at keydown). The amplifier is already keyed
        # on it here - 15m from phase (f). The first measurement of this transmission must catch
        # the mismatch, fold back to bypass, re-select the LDMOS cold and re-engage on 40m.
        b.inject_step(7000, 30, ms=1)
        b.inject_step(7000, 40, ms=5)

    with b.phase("h_rx_hold"):
        # Release and leave the radio silent: with nothing to measure the relay selection must
        # HOLD. It used to follow the classifier's 160m no-signal default, which parked the LPF
        # relays on 160m after every over and made almost every warm re-key move them - right as
        # the T/R relay closed. Sampled at 5 ms so the hold is checked over several scheduler ticks.
        b.ptt(False)
        b.step(4)
        b.step(12, ms=5)

    with b.phase("i_remembered_band_move"):
        # Force the remembered band to differ from the selection the relays are actually sitting
        # on, so the warm engage has to MOVE the band relays. The T/R relay must not close onto
        # contacts that are still moving, so the engage has to hold bypass for BAND_SETTLE_MS
        # first - exactly as the decode path does after a snoop. 1 ms sampling resolves the gap.
        b.write_u8("g_band_cache_band", 5)     # 15m, while the relays sit on 40m
        b.step(1, ms=1)
        b.ptt(True)
        b.step(45, ms=1)

    with b.phase("j_swr_while_bypassed"):
        # A hard SWR fault injected while the amplifier is bypassed must not latch a trip. The SWR
        # bridges sit in the TX train, which the T/R relay only connects to the RF path while it is
        # closed, so during bypass the reading is meaningless - and the band selection may be
        # moving. Expiring the band memory through the firmware's own timeout puts the next PTT
        # back into bypass-snoop (the 60 s itself is not affordable to simulate).
        b.ptt(False)
        b.step(10)
        b.write_u16("g_band_cache_idle_ms", IDLE_TIMEOUT_MS - 5)
        b.step(1, ms=1)
        b.step(3)
        b.ptt(True)
        b.step(4)
        b.pin("RA0", "5v")     # SWR1 forward
        b.pin("RA1", "5v")     # SWR1 reflected: far past the 3:1 default trip
        b.step(6)
        b.pin("RA0", "0v")
        b.pin("RA1", "0v")
        b.step(2)

    b.lines.append("quit")
    return "\n".join(b.lines), b.spans


def parse(output):
    harness.PINS = PINS
    harness.ADC_PINS = []   # ADC pins are stimulus-only here; fewer prints, faster runs
    harness.STATE_VARS = STATE_VARS
    return harness.parse_trace(output)


def show(title, samples, limit=6):
    print(f"    {title}")
    for sample in samples[:limit]:
        print(f"      {fmt(sample)}")
    if len(samples) > limit:
        print(f"      ... {len(samples) - limit} more")


def validate_clause_a(samples):
    if not samples:
        raise AssertionError("clause (a): no samples")
    if any(sample[1][PTT_PIN] != 0 for sample in samples):
        raise AssertionError("clause (a): the PTT stimulus never drove RC0 low")
    if any(sample[2]["g_ptt_active"] != "true" for sample in samples):
        raise AssertionError("clause (a): PTT was not latched while snooping")
    if any(keyed(sample) for sample in samples):
        raise AssertionError("clause (a): a TX output went active with no band decoded")
    if any(sample[2]["g_sequence_stage"] != "0" for sample in samples):
        raise AssertionError("clause (a): the TX sequence advanced with no band decoded")
    if any(sample[2]["g_fc_status.band_locked"] == "true" for sample in samples):
        raise AssertionError("clause (a): the band was locked with no band decoded")
    if any(sample[2]["g_band_cache_valid"] == "true" for sample in samples):
        raise AssertionError("clause (a): a band was cached with no RF measured")
    snooping = [sample for sample in samples if sample[2]["g_snoop_active"] == "true"]
    if not snooping:
        raise AssertionError("clause (a): the firmware never entered bypass-snoop")
    if any(sample[2]["g_state"] != str(STATE_BYPASS_SNOOP) for sample in snooping):
        raise AssertionError("clause (a): snooping did not report STATE_BYPASS_SNOOP")
    show("(a) PTT low, no band: PTT latched, amplifier held in bypass", samples[:3])
    print(f"  PASS  (a) {len(samples)} samples with no band decoded: PTT latched, "
          f"TX/TX_VCC/TX_BIAS inactive, stage 0, band unlocked, "
          f"g_state=STATE_BYPASS_SNOOP for {len(snooping)} samples")


def validate_clause_b(samples):
    decoded = next((sample for sample in samples
                    if sample[2]["g_fc_status.current_band"] == "4"), None)
    if decoded is None:
        raise AssertionError("clause (b): the 20m first burst was never classified")
    # The relay selection must have moved to 20m while the amplifier was cold, and the
    # keying must be observed strictly later (BAND_SETTLE_MS of bypass).
    move_index = next((index for index, sample in enumerate(samples) if sample[1]["RD5"] == 1), None)
    if move_index is None:
        raise AssertionError("clause (b): RD5 (20m) was never selected")
    if keyed(samples[move_index]):
        raise AssertionError("clause (b): the 20m relays were selected while keyed\n"
                             f"      {fmt(samples[move_index])}")
    key_index = next((index for index, sample in enumerate(samples) if keyed(sample)), None)
    if key_index is None:
        raise AssertionError("clause (b): active TX never engaged after the decode")
    if key_index <= move_index:
        raise AssertionError("clause (b): the amplifier was keyed in the same sample interval "
                             "as the relay selection moved")
    settle_ms = millis(samples[key_index]) - millis(samples[move_index])
    if settle_ms < 10:
        raise AssertionError(f"clause (b): only {settle_ms:.1f}ms of bypass between the relay "
                             "selection and keying")
    cached = [sample for sample in samples if sample[2]["g_band_cache_valid"] == "true"]
    if not cached:
        raise AssertionError("clause (b): the decoded band was not remembered")
    if any(sample[2]["g_band_cache_band"] != "4" for sample in cached):
        raise AssertionError("clause (b): the wrong band was cached")
    engaged = next((sample for sample in samples
                    if sample[2]["g_sequence_stage"] == "3"
                    and (sample[1]["RC5"], sample[1]["RC6"], sample[1]["RC7"]) == (0, 0, 0)), None)
    if engaged is None:
        raise AssertionError("clause (b): active TX never engaged after the decode")
    if engaged[1]["RD5"] != 1:
        raise AssertionError("clause (b): TX engaged on the wrong band selection")
    if engaged[2]["g_fc_status.band_locked"] != "true":
        raise AssertionError("clause (b): TX engaged without locking the decoded band")
    show("(b) first RF burst (20m) decoded in bypass, then active TX engages",
         [samples[move_index], samples[key_index], engaged])
    print(f"  PASS  (b) 20m first burst classified in bypass, RD5 selected with the amplifier "
          f"cold, {settle_ms:.1f}ms of relay settling, band cached, then "
          "TX/TX_VCC/TX_BIAS engaged on the locked 20m band")


def validate_clause_c(samples):
    if any(sample[2]["g_snoop_active"] == "true" for sample in samples):
        raise AssertionError("clause (c): the warm-start PTT went back to snooping")
    assert_index = next((index for index, sample in enumerate(samples)
                         if sample[1][PTT_PIN] == 0), None)
    if assert_index is None:
        raise AssertionError("clause (c): the warm-start PTT was never asserted")
    asserted = samples[assert_index]
    keyed_sample = next((sample for sample in samples[assert_index:] if keyed(sample)), None)
    if keyed_sample is None:
        raise AssertionError("clause (c): the warm-start PTT never keyed the amplifier")
    delay_ms = millis(keyed_sample) - millis(asserted)
    if delay_ms > 30:
        raise AssertionError(f"clause (c): engaging from the remembered band took "
                             f"{delay_ms:.1f}ms, which is not an immediate engage")
    if keyed_sample[1]["RD5"] != 1:
        raise AssertionError("clause (c): the remembered 20m band was not restored")
    if keyed_sample[2]["g_band_cache_band"] != "4":
        raise AssertionError("clause (c): the cache did not still hold 20m")
    show("(c) second PTT on the remembered band, with no RF stimulus at all",
         [asserted, keyed_sample])
    print(f"  PASS  (c) PTT engaged from the remembered band {delay_ms:.1f}ms after the "
          "PTT falling edge with zero RF injected (no snoop, RD5 selected, cached band 20m)")
    if not any(sample[2]["g_sequence_stage"] == "2" for sample in samples):
        raise AssertionError("clause (c): the sequencer never reached stage 2, so the "
                             "stage-2 PTT-release path was not exercised")
    tail = samples[-1]
    if keyed(tail):
        raise AssertionError("clause (c): the stage-2 release left a TX output asserted\n"
                             f"      {fmt(tail)}")
    if tail[2]["g_fc_status.band_locked"] == "true":
        raise AssertionError("clause (c): the band stayed locked after the release completed")
    print("  PASS  (c) PTT released during stage 2: TX_VCC was spun down, the release ended "
          "cold and only then was the band released")


def idle_runs(release_samples):
    """Released samples split into runs that are adjacent in the transcript.

    The idle counter is only meaningful *within* a run: a keyed sample in between resets it, so a
    delta taken across that gap is meaningless. Keeping the runs separate is what makes clause (d)
    independent of exactly where the phase boundary lands - a single-sample shift used to split one
    boundary delta into a small positive plus a large negative, which made the clause fail with two
    "resets" for reasons that had nothing to do with the idle counter.
    """
    runs = []
    current = []
    for index, sample in enumerate(release_samples):
        if sample[2]["g_ptt_active"] == "true":
            if current:
                runs.append(current)
                current = []
            continue
        if current and index != current[-1][0] + 1:
            runs.append(current)
            current = []
        current.append((index, sample))
    if current:
        runs.append(current)
    return [[sample for _, sample in run] for run in runs]


def validate_clause_d(samples, release_samples, timeout_ms):
    idle_samples = [sample for sample in release_samples
                    if sample[2]["g_ptt_active"] == "false"]
    if len(idle_samples) < 5:
        raise AssertionError("clause (d): not enough released samples to check the idle timer")
    if any(sample[2]["g_band_cache_valid"] != "true" for sample in idle_samples):
        raise AssertionError("clause (d): the cache expired well before the timeout")
    # The counter must climb while idle, and only while idle. Each released run is checked on its
    # own: deltas are never taken across a keyed gap (see idle_runs()), and each run's growth is
    # compared against that run's own measured span rather than an assumed sample spacing, because
    # these phases mix 10 ms and 1 ms steps.
    runs = idle_runs(release_samples)
    checked = 0
    growth = 0
    expected_ms = 0.0
    for run in runs:
        deltas = [int(later[2]["g_band_cache_idle_ms"]) - int(earlier[2]["g_band_cache_idle_ms"])
                  for earlier, later in zip(run, run[1:])]
        if not deltas:
            continue
        checked += len(deltas)
        if any(delta <= 0 for delta in deltas):
            raise AssertionError("clause (d): the idle counter did not increase monotonically "
                                 f"within a released run (deltas {deltas})")
        span_ms = millis(run[-1]) - millis(run[0])
        run_growth = sum(deltas)
        if span_ms <= 0 or not 0.7 * span_ms <= run_growth <= 1.5 * span_ms:
            raise AssertionError(f"clause (d): the idle counter grew {run_growth} over a "
                                 f"{span_ms:.0f}ms released run")
        growth += run_growth
        expected_ms += span_ms
    if checked < 5:
        raise AssertionError("clause (d): not enough released samples to check the idle timer")
    # A PTT assert must reset the counter, not merely cap it: every released run after the first
    # was preceded by a keyed gap, so it has to restart from near zero.
    for run in runs[1:]:
        start_count = int(run[0][2]["g_band_cache_idle_ms"])
        if start_count > 20:
            raise AssertionError("clause (d): the idle counter did not reset across a PTT "
                                 f"assert (restarted at {start_count})")
    injected = [sample for sample in samples
                if int(sample[2]["g_band_cache_idle_ms"]) >= timeout_ms - 50
                and sample[2]["g_band_cache_valid"] == "true"]
    if not injected:
        raise AssertionError("clause (d): the injected near-threshold idle count did not land")
    expired = [sample for sample in samples if sample[2]["g_band_cache_valid"] == "false"]
    if not expired:
        raise AssertionError("clause (d): the band cache never expired after the timeout")
    after = samples[samples.index(expired[0]):]
    if not any(sample[2]["g_snoop_active"] == "true" for sample in after):
        raise AssertionError("clause (d): the firmware did not revert to bypass-snoop")
    if any(keyed(sample) for sample in after):
        raise AssertionError("clause (d): a TX output went active after the cache expired")
    show("(d) idle counter running, then threshold crossing drops the cache",
         idle_samples[:2] + expired)
    print(f"  PASS  (d) idle counter grew {growth} over {expected_ms:.0f}ms inside "
          f"{len(runs)} released run(s), resetting at each PTT assert; "
          f"injected idle count {injected[0][2]['g_band_cache_idle_ms']} of {timeout_ms}ms "
          "expired the cache, and the next PTT went back to bypass-snoop with TX outputs "
          "inactive")


def validate_clause_e(samples):
    redecoded = next((sample for sample in samples
                      if sample[2]["g_fc_status.current_band"] == "3"), None)
    if redecoded is None:
        raise AssertionError("clause (e): the 40m first burst was never classified")
    if redecoded[1]["RD4"] != 1 or selected_band_pin(redecoded) != "RD4":
        raise AssertionError("clause (e): the 40m relay was not selected")
    if any(sample[1]["RD5"] == 1 for sample in samples
           if sample[2]["g_fc_status.current_band"] == "3"):
        raise AssertionError("clause (e): the previous 20m relay selection was not dropped")
    cached = [sample for sample in samples if sample[2]["g_band_cache_band"] == "3"]
    if not cached:
        raise AssertionError("clause (e): the new band was not remembered")
    engaged = next((sample for sample in samples
                    if sample[2]["g_sequence_stage"] == "3" and sample[1]["RD4"] == 1), None)
    if engaged is None:
        raise AssertionError("clause (e): TX did not engage on the re-detected band")
    show("(e) operator changed band: 40m re-detected on the next first dit",
         [redecoded, engaged])
    print("  PASS  (e) after the cache expired the band change to 40m was re-detected on "
          "the first burst, RD4 selected (RD5 dropped), cached and engaged")


def validate_clause_f(samples):
    moved = next((sample for sample in samples if sample[1]["RD6"] == 1), None)
    if moved is None:
        raise AssertionError("clause (f): the remembered 15m band was not restored on re-key")
    if keyed(moved):
        raise AssertionError("clause (f): the remembered band moved the relays while keyed")
    engaged = next((sample for sample in samples
                    if sample[2]["g_sequence_stage"] == "3"
                    and (sample[1]["RC5"], sample[1]["RC6"], sample[1]["RC7"]) == (0, 0, 0)), None)
    if engaged is None:
        raise AssertionError("clause (f): the amplifier never re-keyed")
    if selected_band_pin(engaged) != "RD6":
        raise AssertionError("clause (f): the amplifier keyed on the wrong relay selection")
    show("(f) fault injection: re-key during the release ramp with a different cached band",
         [moved, engaged])
    print("  PASS  (f) re-key during the release ramp (TX_VCC/TX_BIAS still asserted) forced "
          "bypass before restoring the band: relays moved cold, then TX engaged on 15m")


def validate_clause_g(samples):
    """The band-change-while-keyed-straight-away case: the remembered band was used blind, and
    the first measurement of the transmission has to correct it."""
    if not keyed(samples[0]):
        raise AssertionError("clause (g): the phase did not start keyed on the remembered band")
    if selected_band_pin(samples[0]) != "RD6":
        raise AssertionError(f"clause (g): expected the remembered 15m selection, got "
                             f"{selected_band_pin(samples[0])}")
    injected = [index for index, sample in enumerate(samples)
                if sample[2]["g_fc_status.frequency_khz"] == "7000"]
    if not injected:
        raise AssertionError("clause (g): the 40m measurement was never seen")
    foldback = next((index for index, sample in enumerate(samples) if not keyed(sample)), None)
    if foldback is None:
        raise AssertionError(
            "clause (g): the amplifier stayed keyed on the remembered band while 40m was being "
            "received - the cached band was never verified")
    moved = next((index for index, sample in enumerate(samples) if sample[1]["RD4"] == 1), None)
    if moved is None:
        raise AssertionError("clause (g): the 40m relay was never selected")
    if keyed(samples[moved]):
        raise AssertionError("clause (g): the relays moved while the amplifier was still keyed")
    latency_ms = millis(samples[foldback]) - millis(samples[injected[0]])
    if latency_ms > 150:
        raise AssertionError(f"clause (g): the fold back to bypass took {latency_ms:.1f}ms")
    engaged = next((index for index, sample in enumerate(samples) if index > moved
                    and sample[2]["g_sequence_stage"] == "3"
                    and selected_band_pin(sample) == "RD4"
                    and sample[2]["g_fc_status.band_locked"] == "true"), None)
    if engaged is None:
        raise AssertionError("clause (g): the amplifier never re-engaged on the measured band")
    show("(g) cached band corrected by the first measurement of the transmission",
         [samples[0], samples[injected[0]], samples[foldback], samples[moved], samples[engaged]])
    print(f"  PASS  (g) the blind cached-band engage was corrected {latency_ms:.1f}ms after the "
          "40m measurement appeared: bypass first, relays re-selected cold, then re-engaged on "
          "the locked 40m band")


def validate_clause_h(samples):
    """The relay selection holds through RX: with no RF to measure there is nothing to follow."""
    held = inv.selected_band_pin(samples[0])
    if held is None:
        raise AssertionError("clause (h): no single band was selected at the start of the phase")
    if all(sample[2]["g_fc_status.band_locked"] == "true" for sample in samples):
        raise AssertionError("clause (h): the band was never released, so the hold was not tested")
    for sample in samples:
        if inv.selected_band_pin(sample) != held:
            raise AssertionError(
                f"clause (h): the relay selection moved from {held} to "
                f"{inv.selected_band_pin(sample)} with the amplifier cold and no RF to measure - "
                "it followed the 160m no-signal default instead of holding the last real band\n"
                f"      {fmt(sample)}")
    print(f"  PASS  (h) the relay selection held {held} through "
          f"{inv.millis(samples[-1]) - inv.millis(samples[0]):.0f}ms of released, signal-free "
          "time instead of following the 160m no-signal default")


def validate_clause_i(samples):
    """A remembered-band engage that has to move the relays settles before the T/R relay closes."""
    move_index = next((index for index in range(1, len(samples))
                       if inv.band_pattern(samples[index]) != inv.band_pattern(samples[index - 1])),
                      None)
    if move_index is None:
        raise AssertionError("clause (i): the relay selection never moved, so the remembered-band "
                             "settle window was not exercised")
    moved = samples[move_index]
    if inv.keyed(moved):
        raise AssertionError("clause (i): the relay selection moved while the amplifier was keyed\n"
                             f"      {fmt(moved)}")
    closed = next((index for index in range(move_index, len(samples))
                   if samples[index][1]["RC5"] == 0), None)
    if closed is None:
        raise AssertionError("clause (i): the T/R relay never closed after the relay move")
    settle_ms = inv.millis(samples[closed]) - inv.millis(samples[move_index])
    if settle_ms < 10:
        raise AssertionError(
            f"clause (i): only {settle_ms:.1f}ms of bypass between the band-relay selection change "
            "and the T/R relay closing - the T/R relay closed onto relay contacts that were still "
            "moving")
    print(f"  PASS  (i) the remembered-band engage moved "
          f"{inv.selected_band_pin(samples[move_index - 1])} -> {inv.selected_band_pin(moved)} "
          f"with the amplifier cold, then held {settle_ms:.1f}ms of bypass before the T/R relay "
          "closed")


def validate_clause_j(samples):
    """An SWR fault injected during bypass must not latch a trip."""
    if not any(sample[2]["g_snoop_active"] == "true" for sample in samples):
        raise AssertionError("clause (j): the amplifier was not bypass-snooping, so the SWR-arming "
                             "gate was not exercised")
    for sample in samples:
        if sample[2]["g_fault_latched"] == "true":
            raise AssertionError(
                "clause (j): an SWR fault injected while the amplifier was bypassed latched a "
                "trip\n"
                f"      {fmt(sample)}")
    print("  PASS  (j) an SWR fault far past the 3:1 default injected while bypass-snooping "
          "latched no trip: the SWR trips are only armed while the TX path is engaged")


def write_csv(samples, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ("time_ms," + ",".join(PINS) + "," + ",".join(STATE_VARS) + "\n")
    with path.open("w") as handle:
        handle.write(header)
        for sample in samples:
            handle.write(f"{millis(sample):.6f}," +
                         ",".join(str(sample[1][pin]) for pin in PINS) + "," +
                         ",".join(str(sample[2][var]) for var in STATE_VARS) + "\n")


def main():
    if not ELF_PATH.exists():
        sys.exit(f"error: {ELF_PATH} not found - build firmware first (Debug)")
    addrs = {name: symbol_address(name) for name in SYSTEM_SYMBOLS}
    script, spans = build_script(addrs)
    print(f"first-dit proof: {len(script.splitlines())} mdb commands, "
          f"symbols {addrs}")
    output = harness.run_mdb(mdb_path=harness.find_mdb(), script=script, timeout=300)
    samples = parse(output)
    if not samples:
        sys.exit("error: no samples parsed from mdb output")

    def span(name):
        start, end = spans[name]
        return samples[start:end]

    startup, a, b, c, d, e, f, g, h, i, j = (span(name) for name in
                                             ("startup", "a_ptt_without_band", "b_first_burst",
                                              "c_warm_start", "d_timeout", "e_band_change",
                                              "f_hot_switch_attempt", "g_band_change_foldback",
                                              "h_rx_hold", "i_remembered_band_move",
                                              "j_swr_while_bypassed"))
    for name, group in (("startup", startup), ("a", a), ("b", b), ("c", c), ("d", d),
                        ("e", e), ("f", f), ("g", g), ("h", h), ("i", i), ("j", j)):
        if not group:
            sys.exit(f"error: no samples for phase {name} - mdb script failed? "
                     f"transcript tail:\n{output[-2000:]}")

    print(f"Parsed {len(samples)} samples across {len(spans)} phases")
    print("--- Safety invariants (whole session) ---")
    for line in inv.validate_keyed_band_invariants(samples, "first-dit"):
        print(line)
    for line in inv.validate_band_changes_are_cold(samples, "first-dit"):
        print(line)
    for line in inv.validate_t_r_closes_only_after_band_settle(samples, "first-dit"):
        print(line)
    print("--- Spec clauses ---")
    validate_clause_a(a)
    validate_clause_b(b)
    validate_clause_c(c)
    validate_clause_d(d, c, IDLE_TIMEOUT_MS)
    validate_clause_e(e)
    validate_clause_f(f)
    validate_clause_g(g)
    validate_clause_h(h)
    validate_clause_i(i)
    validate_clause_j(j)
    if "--csv" in sys.argv[1:]:
        csv_path = REPO_ROOT / "_build" / "My_Pic_Project" / "sim" / "csv" / "first_dit_trace.csv"
        write_csv(samples, csv_path)
        print(f"Wrote {csv_path}")
    print("FIRST-DIT PROOF PASSED: clauses (a)-(j), the hot-switch fault injections, and "
          "invariants I1-I6 hold")


if __name__ == "__main__":
    main()
