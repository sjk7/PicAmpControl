# Bug Fixes Log

Tracks bugs found in this codebase (via code review, refactors, or testing) along with
the fix applied. Newest entries at the top. This file is maintained going forward as
part of normal development, not just during large refactors.

## 2026-09-24 — Ambiguity/repetition review of every `.md` and skill; three superseded files removed

A pass over the tracked markdown, the two skills, the agent and the always-on files, looking for
statements that contradict each other or repeat a rule in two places that can drift. Findings and
actions:

- **`mistakes.md` deleted** (folded into the build/test skill first). It was never a mistake log: one
  pasted paragraph correcting a false claim that MDB does not implement interrupts.
- **`blockers.txt` deleted.** 86 lines from another agent, dated 2026-09-22, citing the deleted
  `upgrade/pic18f47q10` branch. Both diagnoses were wrong: its `Stepi 16500000` step-count maths is
  superseded by the measured instruction rate, and its RA6-`FEXTOSC` theory was disproved when
  `ANSELA6` turned out to be already clear. Its surviving content was already in the skill and
  `tools/simulate/test_boot_safety_order.py`.
- **`Eeprom-changes.md` deleted.** Its corrections are implemented in `firmware/src/nvm.c` and logged
  here; its only unique claim was the now-false "device-guarded so the PIC16F18875 keeps
  `eeprom_read`/`eeprom_write`".
- **`README.md` carried three stale facts.** The clock ("internal HFINTOSC at 32 MHz, `RSTOSC =
  HFINT32`") - the part has no `HFINT32` rate at all, and the firmware is `HFINTOSC_64MHZ` with Timer2
  on Fosc/8 so `_XTAL_FREQ` stays the 32 MHz design clock; the CI pack (`PIC16F1xxxx_DFP` 1.32.471 -
  the workflow installs `PIC18F-Q_DFP` 1.30.487); and the suite runtime ("2-3 minutes" - measured
  ~150 s macOS / ~356 s Windows). The README is the entry point, so a wrong line there is the one a
  reader trusts first.
- **`TESTING.md` taught the forbidden method.** It listed first-dit's command as a bare
  `test_first_dit.py`, while `user.cmake` registers `run_suite_with_watchdog.py --test first-dit
  --timeout 600`. Following the doc would have bypassed the watchdog - the exact thing the sticky rule
  forbids - and produced a log tab that never moves. Fixed; the skill now requires grepping the docs
  for the old command whenever a registration or a budget changes. It had also kept a stale
  `--timeout 400` alive in `docs/lcd-test-handoff.md`, a budget that would kill a healthy Windows run.
- **Build directories consolidated.** Seven names were in play (`sim`, `release`, `debug`,
  `q10_release`, `default`, `q10`, `q10_lcdtest`). Canonical now: `release` for the editor, `sim` for
  tests. The two Q10 VS Code tasks and their trees are gone - the Q10 is the default device, so a
  per-device tree is only a second place for a stale database and a stale ELF to hide.
- **`deepseek-pic.md` fought the repo rules** - "comment code heavily" and "enclose all code in
  markdown blocks" against the terse-output rules, plus a `<session_state>` still awaiting an
  assignment. It now opens with a precedence note (the repository wins) and the stale blocks are
  marked rather than silently obeyed.
- **`docs/lcd-test-handoff.md` was a third "where things stand" document.** It presented itself as a
  handoff with done next-steps. It is now scoped to the one item genuinely still open - the parallel
  LCD driver has no working test - and its superseded claims are marked.
- **The instruction-rate disagreement is NOT resolved by this pass.** Editing a harness timing constant
  changes test semantics and, downward, would only shorten every window, so it needs a measurement
  rather than a tidy-up. The skill now states it as UNRESOLVED with the provenance of both numbers
  (`ff931f7` documents 1887 as measured; the macOS re-probe supports 1625) instead of implying both are
  correct, and it records a second, larger contradiction found while repointing references:
  `probe_q10_ptt_path.py` sets `BOOT_STEPS = 16_500_000` for a 1000 ms gate while the direct probe of
  the same boundary found it at ~1.5-1.75M steps - a ~10x gap that needs one measurement to settle.
- **Four stale "do not change the MCU" instructions removed from `Ai-Notes.txt`** (user, 2026-09-24:
  *"Any instructions there about not changing the mcu are out of date and need deleting. They were not
  meant to be permanent."*). They were a temporary evaluation gate that outlived its purpose: the
  `DO NOT START A DEVICE UPGRADE WITHOUT ASKING FIRST, AND DO IT ON A NEW BRANCH` rule with its
  embedded rejected-scope note, the `Before any further 18877 work:` instruction, and the whole
  `DEVICE UPGRADE SPIKE (RE-OPENED 2026-09-22)` section - which still asserted that the PIC16F18875
  was the shipping target and that the port had not started, both false since 2026-09-23. The one
  durable fact buried in them (MPLAB X ships the Q10 DFP under its *own* install root, a different
  root from the user pack repository, so "no DFP installed" was a wrong conclusion) was moved into
  the build/test skill first rather than deleted with the rest. What remains is the history only:
  the record of how a device-swap verdict must not be reached.
- **`Ai-Notes.txt` de-duplicated and corrected: 491 -> 352 lines, most of the reduction moved into the
  build/test skill** (306 -> 433). It had drifted badly enough to describe the wrong device:
  `## Current design` called the repo "the active PIC16F18875-I/P controller", `## References` and the
  CI section pointed at `docs/hardware/PIC16F18875_pin_map.md`, `nvm.c` was described as
  "device-guarded so the PIC16F18875 keeps XC8's legacy eeprom helpers", the Simulation section named
  the 16F in four places (including `run_sim.sh`'s device and `launch.json`), the CTest line gave
  first-dit as a bare `test_first_dit.py`, and `## Device memory usage` quoted the 8192-word 16F map -
  including a "FLASH IS EFFECTIVELY FULL" claim that is simply false on the Q10, where Release measures
  **11214/131072 bytes of program flash (8.6%)** and 368/3359 bytes of RAM. Moved to the skill:
  the whole Simulation method (mdb commands, `run_sim.sh`, `.sym`/`write /r` injection, the idle-ADC
  stimulus recipe, `ANSELC`, `gpsim`, the GUI debug session), the timeout/platform policy
  (`run_mdb(timeout=1500)`, the `platform_process.py` ownership rule, the Python-3 configure check),
  the flash-space policy, the log-following method (`tools/logfollower`, `run_detached.py`, FileTail's
  measured cost, the console-tail trap) and the Windows shell traps. Deleted as duplicates of the
  always-on rules or of `bugfixes.md`: the token/CPU discipline bullet, the commit-and-push bullet,
  the delete-logs bullet, the `git --no-pager` bullet, the "Hmmm" bullet, the write-mistakes-to-the-skill
  bullet, and both `[HISTORY - superseded]` device bullets. **Three of the moves revealed content that
  a document claimed was already in the skill but was not** - the DFP pack-search rule, the Windows
  shell traps, and (earlier in this pass) the `W0106-SIM` scoping. A note saying "see the skill" is not
  evidence that the skill has it.
- **`deepseek-pic.md` merged into a new auto-applied instruction file and deleted** (user, 2026-09-24:
  *"Do what you need to deepseek.md to put as much as possible in a skill or the instructions.md."*).
  Its five bare-metal guardrails were the valuable part; its output-formatting block already fought the
  repo's terse-output rules and its `<session_state>` was stale. The guardrails went to a new
  `.github/instructions/firmware.instructions.md` with `applyTo: "firmware/**"`, so they are
  auto-attached when firmware source is edited and cost nothing on any other request - that file also
  gave the `PORTxbits` read-modify-write trap a home, since it had none. Its three harness-design rules
  became `## Harness design rules` in the build/test skill. Deleted with it: the file itself, the
  `Also read deepseek-pic.md` line in `copilot-instructions.md`, and the two `Ai-Notes.txt` references.
  **This was a user instruction marked "permanent" from 2026-09-22, so it is a deliberate reversal by
  the user, not drift.**
- **Four stale "do not change the MCU" instructions removed from `Ai-Notes.txt`** (user, 2026-09-24:
  *"Any instructions there about not changing the mcu are out of date and need deleting. They were not
  meant to be permanent."*). They were a temporary evaluation gate that outlived its purpose: the
  `DO NOT START A DEVICE UPGRADE WITHOUT ASKING FIRST, AND DO IT ON A NEW BRANCH` rule with its
  embedded rejected-scope note, the `Before any further 18877 work:` instruction, and the whole
  `DEVICE UPGRADE SPIKE (RE-OPENED 2026-09-22)` section - which still asserted that the PIC16F18875
  was the shipping target and that the port had not started, both false since 2026-09-23. The one
  durable fact buried in them (MPLAB X ships the Q10 DFP under its *own* install root, a different
  root from the user pack repository, so "no DFP installed" was a wrong conclusion) was moved into
  the build/test skill first rather than deleted with the rest. What remains is the history only:
  the record of how a device-swap verdict must not be reached.

## 2026-09-23 — OPEN: `run_mdb_probe.py`'s log can omit the probe's printed values (the reason a run went unwrapped)
A rate probe launched through the sanctioned wrapper
(`python tools/simulate/run_mdb_probe.py docs/hardware/q10-bringup/rate_probe_macos.mdb --log ...`)
exited 0 but left a ~180-byte log containing only its `RUN_BEGIN`/heartbeat lines: none of the MDB
`print` values, i.e. none of the data the probe exists to produce. The next attempt went straight to
`mdb.sh <script> > /tmp/x.log`, which did capture everything - and that is exactly the kind of
workaround the user has now forbidden ("everything runs via the watchdog. No cheating!").

So this is not cosmetic: it is the reason the rule got broken, and it should be fixed rather than
worked around. Fix direction: make `run_logged`/`run_mdb_probe` capture the MDB child's stdout into
the log the same way the watchdog captures it for the tests (the watchdog's runs DO contain MDB
output and the harness's prints), then re-measure with the wrapper and delete the raw-mdb habit.
Until it is fixed the probe values can be recovered by having the *test-side* Python print them
(the harnesses do this), rather than by bypassing the wrapper.

## 2026-09-23 — The two harnesses disagree about the simulator's instruction rate (~16%)

`test_first_dit.py` uses `INSTRUCTIONS_PER_MS = 1887`; `trace_ptt_sequence.py` and
`first_dit_invariants.py` use 1625. Both were "measured", by different methods, and at least one has
to be wrong - and a 16% error in that conversion moves a 40 x 1 ms assertion window's end past or
short of the event it is waiting for, which is exactly the kind of difference that makes one clause
pass on one host and fail on another.

Re-measured on macOS with `docs/hardware/q10-bringup/rate_probe_macos.mdb` (the method the original
Windows probe used: bracket the 1000 ms startup inhibit, whose clearing point is a firmware
millisecond boundary the firmware itself maintains). Post-init the clock chain is exactly what
`timer0_init()` writes - `T2CLK=2` (Fosc/8), `PR2=124` - and the 1000 ms boundary falls between
1.50M and 1.75M instructions after the init step: **~1500-1750 instructions per firmware-ms**. That
supports 1625 and not 1887.

Two traps were hit while building this probe, both recorded in the skill: reading SFRs before
stepping answers with *reset defaults* (`T2CLK=0`, `PR2=255`) and reads like a configuration that
never took effect, and `g_band_cache_idle_ms` is not a 1 ms counter (it climbs ~4 counts per
firmware-ms, and stays 0 until the band cache exists), so bracketing it measures nothing.

Open: whether 1887 should simply become 1625 in `test_first_dit.py`, or whether that harness needs
its own re-measurement on the Windows host before being changed - the two hosts should not need
different constants, but that has only been checked on macOS since 2026-09-23.

## 2026-09-23 — First macOS run: the merged suite passes, first-dit fails clause (c) (OPEN)

The Q10-only tree was built and run on macOS for the first time (it had only ever been run on
Windows). Configure and Release build are green, and the merged suite passes: `PTT suite passed: 11
scenarios in one MDB session`, ~110 s, with every I1-I6 invariant line PASS.

`FirstDit_BandDetectionAndHotSwitchGuards` fails:

```
  PASS  first-dit I1-I4 hold over 552 samples and 5 keyed runs ...
  PASS  first-dit I5: all 2 observed band-select changes were seen with the amplifier cold ...
  PASS  first-dit I6: all 5 T/R relay closes followed a band relay selection already settled
        for at least 10ms (tightest 10.5ms)
  PASS  (a) 10 samples with no band decoded: PTT latched, TX/TX_VCC/TX_BIAS inactive, stage 0 ...
  PASS  (b) 20m first burst classified in bypass, RD5 selected with the amplifier cold ...
AssertionError: clause (c): the warm-start PTT never keyed the amplifier
```

Two facts from that transcript, recorded because they narrow the search and are easy to lose:

- **The harness cannot read the settle/verify globals in this run.** Every sample prints
  `settle=? settle_ms=? verify=? verify_ms=?` - it can read `g_band_cache_*`, `g_state`,
  `g_fc_status` and the pins, but not the settle/verify pair. In the merged suite the same fields
  print real numbers (`tightest 92.0ms`). Since clause (c) is about the re-key path and the verify
  state is exactly what decides whether an engage is abandoned, this is the first thing to fix: the
  harness is blind to the state that would explain the failure.
- **Keying itself works.** I1-I4 lists five keyed runs, and one of them (1917-2086 ms, band=20m)
  comes after clause (b)'s engage - so the firmware does key on the remembered band later in the
  session. Clause (c)'s window (PTT re-asserted, 40 x 1 ms samples, no RF) is specifically the one
  with no keyed sample in it.

That is where this stands: not diagnosed, and NOT caused by the 16F removal - the guards that were
deleted were `#if defined(__18F47Q10__)` wrappers whose Q10 branch is byte-identical, and the
merged suite passes on the same ELF.

**Follow-up evidence (same day), after making the harness print the failing window.** Two harness
gaps had to be closed first, and both are worth keeping:

- `test_first_dit.py` keeps its OWN `STATE_VARS` list and had never been given the settle/verify
  globals, so it printed `settle=? verify=?` for every sample while the merged suite printed real
  numbers from the same ELF. `describe()`'s `?` means "key missing from the sample", not "symbol
  unreadable".
- `describe()` did not print the flags that GATE keying, and clause (c) printed its samples only on
  the success path - so the failing run, the one needing evidence, showed nothing.

With those fixed, clause (c) reads:

```
t= 1557.2ms PTT=0 ... ptt_active=false ... inhibit=false crst=false fault=false cache=true cache_band=4
t= 1574.6ms PTT=0 ... ptt_active=true  ... (latched 17.4ms after the pin went low)
t= 1575.8ms PTT=0 ... crst=true settle=true  settle_ms=0
t= 1586.2ms PTT=0 ... settle=true settle_ms=10
t= 1602.5ms PTT=0 ... settle=true settle_ms=19      <- still settling, window ends, no keying
t= 1614.1ms PTT=1 ...                                <- PTT released, engage abandoned
```

So the firmware DOES latch the warm re-key and start the engage; it then holds the band-settle
window and never completes it, and because clause (c) deliberately injects no RF, nothing can move
it on. The window is 40 x 1 ms samples and the latch alone consumed ~17 ms of it.

Two candidate causes, not yet distinguished:

1. The harness's `INSTRUCTIONS_PER_MS = 1887` may not be the rate this image actually steps at, so
   its "1 ms" steps advance less firmware time than the test assumes. Evidence pointing that way:
   inside the same window `g_band_cache_idle_ms` climbs ~4.6 counts per harness-millisecond while
   `g_band_settle_elapsed_ms` climbs ~0.7. Two firmware 1 ms counters cannot both be right, and the
   NOTE in `test_first_dit.py` records 1887 as a measurement while `trace_ptt_sequence.py` uses 1625
   for the same part.
2. The warm engage genuinely requires the settle window to complete (and possibly a verification
   sample) before keying, i.e. the "instant engage from the remembered band" the clause asserts is
   not what the firmware does when nothing moves.

## 2026-09-23 — The pre-flight cleanup was killing live runs, and the editor named the wrong device

**Bug: `cleanup_sim_processes.py` kills a run that is in progress.** Its sweep is driven by
`run_suite_with_watchdog.ORPHAN_PATTERNS`, which contains `run_suite_with_watchdog.py`,
`trace_ptt_sequence.py --suite` and `test_first_dit.py` - that is, the launcher and the tests
themselves, not only the MDB/JVM leftovers it is meant to clear. Running the pre-flight while a run
was live therefore terminated it, and the damage is disguised: the wrapper records
`SUITE_EXIT=143` / `CTEST_EXIT=143` (SIGTERM) and the log simply stops, which reads as a test
failure. It cost one complete merged-suite pass (the harness had already written `PTT suite passed:
11 scenarios in one MDB session`) and a second run before its first test had started. Fix: cleanup
now refuses to act while any process matching those patterns is alive, lists what it found, and says
why. Leftovers are still cleared when nothing is running, which is the only time it should be called.

**Bug: the editor's Problems panel reported three different wrong things about the device.**
`compile_commands.json` in `_build/My_Pic_Project/release` - the directory that both `.clangd` and
`.vscode/settings.json` point at - was a stale 16F configure, so the panel said
`Unknown argument: '-mdfp=.../PIC16F1xxxx_DFP/1.32.471/xc8'`. On top of that, `.clangd` hand-added
`-mcpu=18F47Q10`, which clang does not support, producing a second error of its own:
`Unsupported argument '18F47Q10' to option '-mcpu='`. Fix: the hand-added `-mcpu` is gone (the
compile database already carries the device from `device.cmake`, so a fresh configure is the fix for
a stale pack path, not a flag edit), and the canonical build directory is configured for the Q10.

**RESOLVED: the deeper causes, after the panel stayed bad through two restarts.** Five separate
causes, in the order the diagnostics mislead you:

1. `.clangd` hand-added `-mcpu=18F47Q10` - clang has no such CPU (`Unsupported argument ...`) -
   removed; the database carries the part as `__18F47Q10__`.
2. Removing `-mdfp=` from the parsed flags to silence `Unknown argument: '-mdfp=...'` made it far
   worse: clangd resolves `<xc.h>` through that pack path. Only `-mcpu=` is removed.
3. `clangd --query-driver` can never work with XC8: it queries the driver as `xc8-cc -E -v -x c -`,
   which answers `(2042) no target device specified`. So `user.cmake` derives and adds the three
   include directories as plain `-I` flags - compiler include from `${CMAKE_C_COMPILER}`, pack include
   and its `proc` subdirectory from `${PICAMP_DFP_PATH}` - so they stay machine-resolved and nothing
   OS-specific is committed. `proc` is the easy one to miss: `pic18_chip_select.h` does
   `#include <pic18f47q10.h>` with no prefix, because `-mdfp` normally puts it on the path.
4. **The actual root cause: three macros that XC8 defines itself and nothing else does.** `xc.h`'s
   entire body is `#ifdef __XC8`; it reaches `pic18.h` only under `#if defined(__PICC18__)`; and
   `pic18_chip_select.h` tests `_18F47Q10` (single underscores - not `__18F47Q10__`) before including
   the device header. With every header found and none of these defined, `xc.h` expands to *nothing*
   and every register is undeclared. All three are now in the CMake compile options, so any consumer
   of the database gets them.
5. XC8's own C99 header uses types clang has never heard of - `__int24`, `__uint24`, `__bit`, and the
   `__far`/`__at(...)` qualifiers - mapped in `.clangd` only, because redefining a compiler type for
   the real XC8 build would be a risk to the firmware.

`C_Cpp.default.compileCommands` was also removed from `.vscode/settings.json`: when it is set the
C/C++ extension ignores `includePath`/`defines` and parses the XC8 command line instead, which it
cannot do. Verified with `clangd --check` on `firmware/src/main.c`: **0** include/type/undeclared
errors (was 23), leaving only clangd's internal tweak noise. The panel keeps its own cached copy
until the extension is restarted.

## 2026-09-23 — Log Follower: three different defaults, and a cost claim that was the opposite of the code

The in-repo log-following extension (`tools/logfollower`) is the answer to "we need a decent tail
plugin" - the CPU-eater that was rejected is `spacetown.filetail` - but it was telling three
different stories about its own cost:

- `package.json` defaulted `logFollower.coalesceMs` to **250 ms**.
- `extension.js` fell back to **400 ms** (`cfg.get('coalesceMs', 400)`) and its header comment
  described 400 ms as the default.
- the README documented **60 ms** in the settings table, and its cost section asserted "There is no
  interval timer anywhere in the extension" - while `activate()` runs
  `setInterval(pollOnce, settings.coalesceMs)`.
- the README also documented `logFollower.autoFollowGlobs` as defaulting to `[]` when the manifest
  ships three globs (`*.log`, `*progress.log`, `*.out`).
- `extension.js`'s header comment claimed "No filesystem watcher" while v0.7 added
  `armWatcher()`, one watcher per followed file.

A cost claim that contradicts the code is worse than no claim at all: the whole point of this
extension is that it is the cheap alternative to a rejected follower. Fix: **400 ms is now the one
default** in all three places, the globs default is documented as shipped, and both the README cost
section and the header comment now describe what the code actually does - a `stat()` per poll
interval, a revert plus one scroll only on real growth, and an optional per-file watcher that is an
optimisation on top of the poll and never the sole trigger.

## 2026-09-23 — Q10-only conversion: two latent bugs found while stripping the 16F

**Bug: the device launchers defaulted to the removed part.** `tools/simulate/run_sim.sh` and
`run_sim.ps1` both selected `PIC16F18875` (`DEVICE="PIC16F18875"` / `$Device = "PIC16F18875"`) while
the CMake build, the harnesses and `device.cmake` all default to `PIC18F47Q10`. A sim launched
through either script would therefore have asked the simulator for the old part while `out/` held the
Q10 image - the exact image/device mismatch that `parameterise_output_dir.py` exists to prevent, and
one that produces a wrong verdict with no error. Fix: both scripts now select `PIC18F47Q10`.

**Bug: `parameterise_device.py`'s self-check could never pass.** Its "no hardcoded device tokens
left" check ran the regex over the entire rewritten file *including the header it had just
prepended*, and that header names the device. The script therefore printed
`hardcoded device tokens left=1` and exited 1 on every run, even when the body was completely
clean - worse than having no check, because a genuine un-parameterised token would have been
indistinguishable from the known false alarm. Fix: the check now measures the file body only, so a
clean run reports `left=0` and exits 0.

## 2026-09-22 — PIC18F47Q10 spike: two wrong verdicts in a day, both from untested assumptions

The Q10 spike produced two retractions on the same day. Both were my error, both were avoidable, and
the sequence is the reason this entry is long.

**Wrong verdict 1: "the simulator runs no time base on the Q10".** The minimal bring-up wrote
`T2CLKCON = 0x00`, annotated "Fosc/4 (the reset default)" - an assumed value - while
`firmware/src/main.c`'s own `timer0_init()` has carried `T2CLKCON = 0x01; /* Fosc/4 */` all along.
Rebuilt with `0x01`, `T2TMR` counts immediately (`106` then `92`): the earlier build had simply been
clocked from nothing.

**Wrong verdict 2: "the simulator does not dispatch interrupts".** Two independent sources (Timer2
overflow, and an RC0 interrupt-on-change driven from mdb) raised and cleared their flags under
polling with `GIE=1`, `PIE4=2`, `PIE0=16`, while `g_isr_any` stayed `0`. That looked conclusive. It
was not: those builds left `IPEN = 0`, the PIC16F-style plain path. With `IPEN = 1` and
`IPR4bits.TMR2IP = 1`, the ISR runs immediately - `g_isr_any` and `g_tick` both `56 -> 172` over
800,000 instructions, while the polled counter falls to `6 -> 18` because the ISR now consumes the
flags first (`INTCON=231`, `IPR4=63`, `g_ipen=1`, `g_gie=1`).

**What the PIC18F47Q10 actually does**, measured on branch `spike/pic18f47q10-retest`:

| Question | Result |
|---|---|
| PTT reaches the firmware | yes - `g_ptt_active` tracks a driven RC0 |
| Outputs toggle | yes - `RC5` tracks PTT |
| Time base runs | yes - `T2TMR` counts with `T2CLKCON=0x01`; polled tick `g_poll_ticks` `30 -> 161 -> 292` |
| Interrupt reaches the ISR | yes - **with `IPEN=1` and the source's `IPRx` priority bit set**; with `IPEN=0` it never does |
| Tick calibration | ~6,100-6,900 instructions/tick, against the 8,000 the harness assumes for 1 ms at 32 MHz |

The `IPEN` difference is a real family difference in how interrupts are *enabled*, and the interrupt
system itself is modelled correctly - with `IPEN = 1` a pending flag breaks execution and the ISR is
entered, exactly as it should. What this model does not dispatch is the datasheet-legal `IPEN = 0`
path, which is a narrow deviation to work around rather than evidence that interrupts are
unimplemented. So a port must set `IPEN = 1`, assign a priority per source via `IPRx`, and enable the
matching global (`GIE`/`GIEH`, plus `PEIE`/`GIEL` for low priority) instead of the 16F's plain
`GIE = 1`. The scoping of `W0106-SIM` to PPS/clock-source routing, and the explicit statement that
the core and the interrupt controller are modelled, came from the user's `mistakes.md`. That file was
never a mistake log - it was a single pasted paragraph - and it was folded into
`.github/skills/build-test/SKILL.md` and deleted on 2026-09-24, which is where the scoping note now
lives.

`OSCCON3.ORDY` reads `0` throughout, even while the timer and the interrupt-on-change demonstrably
run, so it must not be cited as evidence about the clock.

**The lesson.** Each verdict was reached after *one* configuration, and each was wrong in the same
direction: the model was blamed for a value or an enable the firmware had not set correctly. Before
concluding "the simulator cannot do X", exhaust the configuration space for X - here two clock-select
values and two interrupt-enabling mechanisms - and A/B the suspect constant. The experiment that
settles it takes minutes; both wrong verdicts cost far more than that.

**Recommendation:** the Q10 is a viable candidate, not a rejected one. No `main` firmware has been
touched, the PIC16F18875 remains the shipping target, and any port is the owner's call. The first two
items of any port are the interrupt-enable form and the tick calibration.

The original entry follows, unaltered, so the mistake stays on the record.

---

Second device-upgrade attempt, run on branch `spike/pic18f47q10` (never on `main`) under the gated
brief in `Ai-Notes.txt`. It fails the step-3 gate and the device is rejected. Recorded because the
failure mode is **not** the same as the PIC16F18877's, so without this entry it would be retried by
someone reading only "the 18877 did not see PTT" and expecting a different-looking result.

### What was tested

A deliberately minimal bring-up image (`main_q10_spike.c`, ~200 bytes of program space) - no ADC,
comparators, EEPROM/NVM, PPS, LCD or sequencer, exactly as the brief requires. It contains:
config words for the Q10 family, an oscillator setup, a Timer2 ~1 ms tick with an ISR that
increments `g_tick`, a heartbeating output, a read of `TMR2`, and an active-low PTT input on RC0
driving an output on RC5. Compiled with the DFP that MPLAB X 6.35 already ships
(`PIC18F-Q_DFP/1.30.487`, see the skill - it is not in the user pack repository):

```text
xc8-cc -mcpu=18F47Q10 -mdfp=<…>\PIC18F-Q_DFP\1.30.487\xc8 -O1 -gdwarf-3 -std=c99 \
       -o spike_q10.elf -Wl,-Map=spike_q10.map main_q10_spike.c
```

Config words used (names and values taken from the DFP's `18f47q10.cfgmap`, never copied from the
PIC16F): `FEXTOSC=OFF`, `RSTOSC=HFINTOSC_1MHZ`, `CLKOUTEN=OFF`, `CSWEN=OFF`, `FCMEN=OFF`,
`MCLRE=EXTMCLR`, `PWRTE=OFF`, `WDTE=OFF`, `BOREN=ON`, `BORV=VBOR_190`, `LVP=OFF`, `CP=OFF`,
`CPD=OFF`, `SCANE=OFF`, all `WRT*` and `EBTR*` = OFF. The build is clean: 214 bytes program
(0.2%), 12 bytes data, 6/6 config words; the only warning is
`(1311) missing configuration setting for config word 0x300005; using default`.

### What actually worked

Two of the three gate questions pass, and this is the part that makes the rejection non-obvious:

- **The firmware DOES see PTT.** Driven `RC0` high, then low, then high again across 100 ms steps,
  `g_ptt_active` read back `[0, 0, 0, 1, 1, 0]`. The 18877's killer (PTT invisible to the firmware)
  does **not** reproduce here.
- **Outputs toggle.** `RC5` read `[1, 1, 1, 0, 0, 1]`, following PTT.
- **The CPU executes**, and the main loop runs (`g_loops` advanced 37 → 158 → 24 → 180 → 81 → 202,
  wrapping as a `uint8_t`).

### The blocker: no timer counts, and the oscillator never reports ready

`g_tick` stayed `0` across every sample, so the ISR never ran. Reading the SFRs back after 800,000
stepped instructions shows the configuration is intact and the peripherals are simply not moving:

| Register | Read back | Meaning |
|---|---|---|
| `T2CON` | `224` (0xE0) | Timer2 ON, CKPS=110 (1:64), OUTPS=0 - as written |
| `T2PR` | `124` | period register as written (1 ms at an 8 MHz instruction clock) |
| `T2TMR` / `TMR2` | `0` | **counter never advances** (`TMR2` and `T2TMR` are the same address, 0xFBA) |
| `T2CLKCON` | `0` | reset-default clock selection |
| `T1CON` | `1` | Timer1 enabled from mdb, internal clock |
| `T1CLK`, `TMR1L`, `TMR1H` | `0`, `0`, `0` | **Timer1 never advances either** |
| `T4CON`, `T4CLKCON`, `T4TMR` | `224`, `0`, `0` | **Timer4 never advances either** |
| `OSCCON1` | `96` (0x60) | NOSC=0b110 (HFINTOSC), NDIV=0 - the system clock source is selected |
| `OSCFRQ` | `7` | the requested HFINTOSC frequency code took |
| `OSCCON3` | `0` | **ORDY never asserts - the oscillator never reports ready** |
| `PIE4` / `PIR4` | `2` / `0` | `TMR2IE` is enabled; no `TMR2IF` is ever set |
| `INTCON` | `135` (0x87) | `GIE` set |

Three independent timers, all enabled, all on their internal/reset-default clock selections, all
flat at zero over 800,000 instructions - while `Stepi` happily executes those instructions. A
second build with `RSTOSC=HFINTOSC_64MHZ` instead of `HFINTOSC_1MHZ` behaves identically
(`OSCCON1=0`, `OSCCON3=0`, all three counters `0`), so this is not one oscillator-code choice.
`OSCCON3.ORDY` never asserting points at the clock model itself rather than at any timer mux.

The control is that the *same* Timer2 recipe (`T2CON` CKPS=1:64, period register 124, 8 MHz
instruction clock) does count on the PIC16F18875 - the project's entire suite depends on that tick.

The device also emits `W0106-SIM` warnings for TMR1/TMR3/TMR5 only (the same three the 16F warns
about) plus the `W9602-COMP` DAC-to-comparator warning already noted for this part. Nothing warns
that timers generally are unsupported; the model simply does not advance them.

### Why this is a hard stop rather than something to configure around

Every safety property this project asserts is *time-based*: the PTT sequencing order and its
inter-stage delays, `BAND_SETTLE_MS` before the T/R relay closes, `BAND_VERIFY_MS` fold-back,
trip latching, the first-dit decode window, the band-cache expiry. A simulator with no running time
base cannot verify any of them, and worse, it would let a timing defect pass silently - a green
suite that means nothing is more dangerous here than no suite at all. Trading verified behaviour
for flash headroom was the wrong trade for the 18877 and it is the wrong trade for the Q10.

Deliberately not tried, per the brief's instruction not to treat a non-ticking model as a puzzle:
alternative clock sources (external oscillator, PLL), non-default `T2CLKCON`/`T4CLKCON` codes, and
PPS. The ORDY evidence above makes those unlikely to help, and a port that only runs on one
hand-tuned simulator clock configuration would not be trustworthy evidence anyway.

### Two smaller gotchas found on the way

- **`write T0CON 0x80` aborts an mdb script on this device** (it prints `null` and ends with exit
  `-1`): PIC18F-Q10 splits Timer0 into `T0CON0`/`T0CON1`, so the PIC16F register name does not
  exist. An unknown name kills the rest of the script, so keep speculative register reads last.
- **`print <variable>` and `write <SFR> <value>` do work on this device** - the transcript format is
  the same as the 16F's, so the existing harness parsing contract would have carried over.

The branch was abandoned and the attempt removed; the recipe above is the durable record.


Found while evaluating a device upgrade: comparing the pin map against the datasheet made it
obvious that the map's own figures could not be right.

`docs/hardware/PIC16F18875_pin_map.md` claimed VSS on pins 1 and 19, VDD on 10 and 20, RB0-RB7 on
21-28, RC0-RC7 on 11-18, RD0-RD7 on 29-36 and RE0/RE2/RE3 on 37/39/40, with a "VREF+ (ADC ref)"
on pin 38. The actual PDIP-40 pinout (datasheet DS40001802H) is VPP/MCLR/RE3 on 1, RA0-RA5 on 2-7,
RE0/RE1/RE2 on 8/9/10, VDD on 11 and 32, VSS on 12 and 31, RA7/RA6 on 13/14, RC0-RC3 on 15-18,
RD0/RD1 on 19/20, RD2/RD3 on 21/22, RC4-RC7 on 23-26, RD4-RD7 on 27-30 and RB0-RB7 on 33-40.
**Only RA0-RA5 (pins 2-7) were correct.** The map even carried the hedge "(Pin numbers assume
standard PDIP-40 package conventions)" - the numbers had been assumed, not looked up.

Three separate errors, the first two actively dangerous for anyone wiring from that document:

- `RD2-RD7` were listed both as the six LPF band-select outputs *and* as "genuinely free (not
  claimed by any `pin_map.h` define)". Anyone trusting the free-pin list would have left the
  band-select bus unconnected.
- `VREF+` was given a dedicated pin (38). It has none: it is an alternate function of **RA3**
  (`RA3/ANA3/C1IN1+/VREF+/MDCARL`). Harmless in effect only because `firmware/src/main.c`
  references VDD with the FVR off, so the design never uses it - but RA3 is also `ADC_SWR2_REF`,
  so a future move to an external reference would have silently collided with an ADC input.
- `RE3` was listed as free GPIO while `firmware/src/main.c` sets `#pragma config MCLRE = ON`,
  which makes it the MCLR/VPP pin. The datasheet is explicit: "general purpose input only when
  MCLR is disabled". RE1 was missing from the document entirely.

Verified before editing, because a PCB-facing table is worse than useless if it is confidently
wrong. The datasheet's pin *diagram* was read twice - once in extraction order and once by pairing
text fragments on their y-coordinates - and both agree: each side of the package yields twenty
names and twenty numbers in strictly matching order, and the result is a complete permutation of
pins 1-40 with every port pin appearing exactly once. A third reading via the 40/44-pin allocation
table was abandoned: its columns interleave under extraction and its numbers sit a row out of step
with its names, so it was rejected rather than used to "confirm" anything.

Also corrected in the same pass: the free-GPIO count (9 -> 3; the old figure counted RD2-RD7),
the stale "RE0/RE2/RE3 remain spare" line in the future-uses list, and the document version.

Also fixed in the same pass, once the owner confirmed it: the Power & Ground table labelled the rail
"VDD (3.3V)", while `firmware/src/main.c`'s ADC comments assume a 5 V reference (~4.88 mV per
count), the NTC divider docs specify "the regulated 5 V rail", and the ADC protection note clamps
to "VDD/+5 V". The supply is 5 V, so the 3.3 V label was the error and it has been removed. It was
the only place in the repository that stated 3.3 V: a search for `3.3 V`/`3V3` now finds nothing
outside the historical entries in this log. The rail voltage is now stated explicitly in the pin
map's Power & Ground section so it cannot drift back.

## 2026-09-22 — The simulator harnesses were POSIX-only, and the launcher never reached the simulator on Windows

Found by running the previously macOS-only test workflow on Windows 10 for the first time. The
firmware itself needed no changes: configure and build were already clean, and the Debug image
linked to the same `8117/8192 words (99.1%)` as on macOS. Everything that broke was in
`tools/simulate/*.py`, and every failure was invisible on macOS.

The four defects, each of which failed on a different path:

1. **`kill_orphaned_processes()` called `ps`, which does not exist on Windows, and its
   `except subprocess.CalledProcessError` did not catch the `FileNotFoundError` that
   `subprocess.check_output` actually raises.** The launcher therefore exited before it spawned the
   suite, so a Windows run produced no CTest result at all - which reads as "the firmware failed" if
   you do not check whether the child was ever started.
2. **`kill_previous()` probed the PID file with `os.kill(pid, 0)`.** On Windows, Python's `os.kill`
   maps every signal other than `CTRL_C_EVENT`/`CTRL_BREAK_EVENT` onto `TerminateProcess`, so this
   idiomatic POSIX liveness check **kills the process it is asked about** - and here it would kill
   the previous run's process, or an unrelated process that had inherited the PID.
3. **`signal.SIGKILL`, `os.killpg` and `os.getpgid` do not exist on Windows** and raise
   `AttributeError` - but only on the timeout and interrupt paths, i.e. precisely when a run has
   hung and the cleanup matters. `import signal` succeeds on Windows, so nothing caught this early.
4. **`start_new_session=True` is accepted and silently ignored on Windows**, so `mdb` stayed
   attached to the console and a Ctrl-C aimed at the harness would reach the JVM.

Fixed by adding `tools/simulate/platform_process.py` as the single place that knows the platform,
and routing all four harnesses through it: `temp_dir()` (`%TEMP%` vs `/tmp`),
`isolated_spawn_kwargs()` (`CREATE_NEW_PROCESS_GROUP` vs `start_new_session`),
`pid_is_alive()` (`OpenProcess`/`GetExitCodeProcess` vs `os.kill(pid, 0)`),
`terminate_tree()`/`kill_tree()` (`taskkill /PID <pid> /T /F` vs `os.killpg` + `SIGTERM`/`SIGKILL`),
`running_processes()` (`Get-CimInstance Win32_Process` vs `ps -axo`), and `find_mdb()`.

Verified end to end on Windows 10 + Python 3.14.7 + MPLAB X 6.35 + XC8 4.00: both CTest tests pass,
including the full first-dit proof (`clauses (a)-(j), the hot-switch fault injections, and
invariants I1-I6 hold`).

Three further traps found while doing it, none of which were pre-existing bugs but each of which
cost a cycle:

- **`Path().glob("C:/absolute/pattern")` raises `NotImplementedError: Non-relative patterns are
  unsupported` on Python 3.13+.** The existing harnesses only escaped this by globbing a *relative*
  pattern under an absolute base; factoring the MPLAB install globs into a shared constant made the
  pattern absolute and broke `find_mdb()` immediately. Use `glob.glob()`.
- **MPLAB version directories were sorted as strings.** `sorted(...)[-1]` picks `v6.35` over `v6.20`
  by luck, not by design - it would pick `v6.9` over `v6.35`. `find_mdb()` now compares the version
  tuple, matching what `run_sim.sh` gets from `sort -V`.
- **The orphan pattern must not be a transliteration of the POSIX one.** A Windows run is
  `cmd.exe /c "…\mplab_platform\bin\mdb.bat"` plus `java.exe … "…\lib\mdb.jar"
  com.microchip.mplab.mdb.debugcommands.Main`. Matching `mplab_platform` (the obvious port of
  `/mplab_platform/bin/mdb`) also matches MPLAB X IDE's own JVM and a Java updater daemon, both of
  which must survive; matching a bare `mdb.jar` is a path the IDE's classpath could carry too. The
  JVM is therefore matched on its **main class** (`com.microchip.mplab.mdb`) and the wrapper on
  `mdb.bat`, both chosen from a full `Win32_Process` dump of 262 processes.

And a fifth defect, found only once the port worked well enough to run the suite end to end:

5. **The MDB timeouts were sized for macOS, so a healthy suite run failed on Windows.** MDB is
   about **2.4x slower on Windows** - measured on the same firmware, the merged suite takes 356 s
   against ~150 s and the first-dit proof ~55 s against ~20 s - so the suite ran past
   `run_mdb`'s 280 s default while still printing progress on every 10-second heartbeat. The
   verdict was `error: mdb timed out after 280s and was killed` on a run that was 100% healthy, and
   CTest reported `PTT_SequencerAndTripSuite ***Failed 281.75 sec` / `50% tests passed`, which reads
   exactly like a firmware regression. Nothing in the firmware or the toolchain caused it.

Fixed by sizing the bounds for the slowest supported host and documenting the relationship between
them: `run_mdb(timeout=1500)` is a last-resort net that must sit *above* the launcher's outer
budget (otherwise the child dies first and its message masks the launcher's clean
`TIMEOUT … END code=` line), `run_suite_with_watchdog.py --timeout 1200` is the real budget, and
`user.cmake` passes that same figure with a matching CTest `TIMEOUT 1500`. The `first-dit` and
standalone frequency-counter sessions were raised with it.

## 2026-09-21 — The T/R relay could close onto LPF relays that were still moving (first-dit warm re-key)

Found by code review of the first-dit band-selection ordering, prompted by the question "will the
rig see the relays change over?".

There are **two mechanical relay groups in the RF path**, not one: the T/R relays (`OUTPUT_TX`,
RC5 - confirmed by the release ordering comment "open relays first" and by `PIN_LABELS` in
`tools/simulate/trace_ptt_sequence.py`, which labels RC5 `RELAYS`) and the LPF band relays
(K1-K6, RD2-RD7). In a normal amplifier the band relays are positioned from the rig's band data
*before* key-down, so only the T/R relay moves on PTT and the existing `tx_vcc_delay_ms` wait
covers it. This design has no band data - the band is *measured* - so the band relays can move at
key-down, and the T/R relay must not close until they have settled.

The decode (snoop) path got this right: the band relays move with the T/R relay open, then
`BAND_SETTLE_MS` of bypass is held, and only then does the sequencer close the T/R relay. The
**warm path did not**: `handle_ptt_transition()` called `freq_counter_restore_locked_band()`,
which drives the band-select outputs, and the sequencer reached stage 0 - `set_tx_output(true)` -
on the next pass, roughly 1 ms later, with `g_band_settle_active` explicitly cleared at the top of
the same function.

This was not hypothetical, because of a second problem: `release_band_if_cold()` unlocks the band
after every over and `freq_counter_tick_10ms()` then followed the classifier, which reports its
**160m no-signal default** for an empty gate window (`classify_frequency_khz(<1000)`). So the LPF
relays parked on 160m after each over and had to move back on the next warm re-key - right as the
T/R relay closed on top of them. It also meant the relay selection chattered on every over.

The invariant checks could not catch it: I5 only requires that the *sample in which the selection
changed* was cold, and the move is initiated in the same pass as `apply_bypass()`, so at 1-5 ms
sample granularity it looks cold. This is the sample-granularity limit already noted in
docs/first-dit-band-detection.md.

Fixed by:
- `freq_counter_tick_10ms()` no longer follows an unusable measurement. It updates `current_band`
  (and therefore the relay selection) only when the reading is stable and usable - the frequency
  bound is what separates real 160m (1800-2000 kHz) from silence. The relays now hold their last
  real selection through RX, so a warm re-key on the same band moves nothing.
- `freq_counter_restore_locked_band()` now returns whether the band-select outputs actually moved,
  and when they did the caller starts the existing `g_band_settle_active` window, so bypass is
  held for `BAND_SETTLE_MS` before the T/R relay may close. When nothing moves (the common case)
  the engage stays immediate.

## 2026-09-21 — The SWR trips were armed while the amplifier was in bypass

`swr_trip()` was evaluated on every main-loop pass and its result folded straight into
`any_trip_fault` in `update_protection_state()` with **no gate on the amplifier being keyed** - the
only guard inside `swr_trip()` was `forward_raw < 10`. During bypass the T/R relay is open, so the
SWR bridges are disconnected from the RF path and the band selection may legitimately be moving,
yet a bridge reading in that window could latch `g_fault_latched` and drop the firmware into
`STATE_TRIP`. That is the opposite of what the bypass window is for: the first-dit design depends
on PTT staying latched and the amplifier staying cold while the band is decoded.

Fixed by arming the SWR trips only while the TX path is engaged: sequencer stages 1-3 are exactly
the stages that hold `OUTPUT_TX` asserted, so `update_protection_state()` now requires
`g_sequence_stage >= 1 && g_sequence_stage <= 3` before `swr1_fault`/`swr2_fault` can contribute to
a trip. The hardware overcurrent, current, temperature, overdrive and drain trips are deliberately
left ungated. The gate is applied once, in `update_protection_state()`, rather than at the two call
sites, because the Debug image is at its flash ceiling.

## 2026-09-21 — The developer's macOS account name was published in tracked files

A case-insensitive search for the developer's macOS account name (which is their real name) found it
hard-coded as an absolute home path in five tracked files: `.clangd`, `TESTING.md`,
`.github/skills/build-test/SKILL.md`, `.vscode/settings.json` and
`.vscode/c_cpp_properties.json`. This repository is public, so the name was published in every clone
and on the web. The name is deliberately not repeated here - writing it into this log would recreate
the same leak.

It was also in the local build metadata: the locally built `out/My_Pic_Project/default.elf` and
`default.sym` embed the absolute source path (30 and 31 hits respectively). The flashable
`default.hex` contains none, and neither do the published release assets (`default.elf`,
`default.hex`, `mem.map`, `memoryfile.xml`) - CI builds on a runner under a temporary path. So the
leak was in the repository, not in the shipped firmware.

Fixed in the working tree by replacing the literal home directory with portable forms: `$HOME` in
the shell examples, `${env:HOME}` / `${env:USERPROFILE}` in the VS Code configuration, and a new
`Windows-XC8` configuration alongside `Mac-XC8`. `.clangd` was untracked at first, then restored as
a **portable, tracked** file once its machine paths turned out to be redundant: clangd queries the
compiler named in the compile database for its system includes ("System includes extractor:
successfully executed xc8-cc"), and that database is generated per machine by CMake, so the XC8 and
DFP include directories resolve on either OS without being listed. Verified with `--check` on
`firmware/src/main.c`: 0 errors with no `-I`/`-mdfp` lines. Two dead ends worth not repeating:
clangd does not expand `${workspaceFolder}` (the literal string reaches the compiler), and
`If: PathMatch` fragments cannot select by OS (a POSIX-matching branch and a `C:/**` branch were
both applied to the same file).

**Not fixed, and not fixable by a commit:** the name remains in the history of `main` (six commits
match a history search, from `efbd7a7` through `e4b9c93`) and a personal email address remains in
the commit author metadata. Removing those needs a history rewrite plus a force-push, which changes
every downstream commit SHA and invalidates existing clones and forks - left to the repository owner
to decide. Local, gitignored working directories (`_build/`, `out/`, `build/*.log`,
`tools/simulate/__pycache__/`) also still contain the name; they are not in the repository, but
attaching them to an issue or a chat would leak it.

Out of scope by the owner's decision: the Windows account name in two archived files under
`prototype_reference/` (`C:/Users/<name>/...`) is not sensitive and must not be scrubbed. Do not
re-raise it in a future sweep.

## 2026-09-21 — AI-HANDOFF.md duplicated other docs and stated a release behaviour the firmware no longer has

Two AI carry-over files had grown up side by side, `Ai-Notes.txt` and `AI-HANDOFF.md`. Nothing in
the repository referenced the latter (only this log, and only to record it being wrong), while
`Ai-Notes.txt` is the declared launch point and is referenced from `run_sim.sh`/`run_sim.ps1`. The
handoff file was a partial restatement of content that already has canonical homes:
project-architecture.md (state model, band lockout, sequencing and polarity defaults, encoder UI,
re-arm rules), the pin map (which it restated as an ADC channel table, against the recorded rule),
TESTING.md (the CTest options) and README.md (the diagram links).

It also carried a claim the firmware no longer supports: "sequence requests complete their engage
order even if PTT releases early, then unsequence in order". That was made false by the stage-2
release fix logged below - a release now unwinds the sequencer in order (TX off first) and releases
the band only once every TX output is confirmed inactive, so an in-progress engage is aborted rather
than completed.

Fixed by merging into a single file: `AI-HANDOFF.md` was deleted, the few facts in it that no other
document held were verified against the firmware and folded into `Ai-Notes.txt` (ADC format and
scaling, current-sensor scaling and its 40 A default, release ordering), and the stale SHA/working
tree notes in its handoff section were replaced with "read the current commit from git". The merged
file explicitly records that a second handoff file must not be recreated.

## 2026-09-21 — Docs still described the removed EasyEDA/KiCad schematic automation

Commit `90c7bf7` deleted the whole schematic-automation pipeline (generators, `.kicad_sch`
artifacts, `node_modules`, `package.json`, the KiCad MCP skill setup) but left the documents that
described it, so the repo advertised a workflow with no files behind it:

- `docs/hardware/SCHEMATIC_WORKFLOW.md` documented an EasyEDA pipeline (`easyeda_pro_generator.py`,
  `svg_renderer.py`, `visual_validator.py`, `watch_and_render.py`, `pic_amp_control_full.yaml`,
  `out/picampcontrol_easyeda_*.json`) whose scripts no longer exist, plus three EasyEDA integration
  routes (`easyeda-agent` CLI, the `easyeda-copilot` MCP server, a custom `.eext` extension) that
  were themselves the abandoned approach.
- Three other files still pointed at removed targets: `README.md` linked the workflow doc,
  `AI-HANDOFF.md` listed it as the schematic reference and told the next session to read
  `docs/hardware/schematic-workflow.md` and run `tools/setup_schematic_skill.ps1` (neither exists),
  and `project_schematic_package/README.md` referenced a `schematic-design` MCP skill,
  `mcp-server-kicad`, `.vscode/mcp.json`, a `generated/` tree and a `_SCHEMATIC_TEMPLATE.kicad_sch`
  that are all absent.
- `PIC16F18875_pin_map.md` kept a "KiCad Symbol Reference" section asserting that the design uses
  KiCad's `MCU_Microchip_PIC16:PIC16F18875-xPDIP40` symbol: a pointer into the abandoned toolchain,
  and the last tool-specific reference left anywhere in the docs.

Fixed by deleting the workflow document and repointing the survivors: the schematic package is now
described as what it actually is - static design inputs (block diagram, connection table, component
list, wiring checklist) captured by hand, with no automated path to a schematic file. The pin-map
KiCad section was deleted too, after the user ruled out any further schematic automation ("same for
kicad stuff ... it can all go"). No current-facing doc, README or config in the repository now names
EasyEDA, KiCad, an MCP schematic server or a `.kicad_sch` file - the only mentions left are this log
and the standing instruction in `Ai-Notes.txt`.

## 2026-09-21 — Releasing PTT during sequencer stage 2 left TX_VCC asserted and unlocked the band

Found by the new first-dit proof (`tools/simulate/test_first_dit.py`) the first time it released
PTT while the sequencer was in stage 2: TX and TX_VCC up, bias still ramping.

`update_tx_sequence()` had a release branch for stage 3 (the normal path) plus a separate one for
stage 2 that jumped straight to stage 5:

```c
} else if (g_sequence_stage == 2) {
    set_tx_output(false);
    g_sequence_elapsed_ms = 0;
    g_sequence_stage = 5;
}
```

Stage 5 only removes the bias, so a release in that window never turned TX_VCC off: the drain
supply stayed asserted for the rest of the receive period, and stage 5's completion then unlocked
the band, letting the LPF relays follow live RF with TX_VCC still on. An operator releasing PTT
within ~20 ms of keying hits this, and the reachable window is exactly the `tx_bias_delay_ms`
setting (20 ms by default).

Fixed by unwinding stage 2 through the same ordered path as stage 3 (TX relay first, TX_VCC after
the VCC delay, then TX_BIAS), and by adding `release_band_if_cold()`, which releases the band only
once every TX output is confirmed inactive. The first-dit test asserts the release ends cold with
the band released, and the defect was re-introduced to confirm the test fails on it:
`clause (c): the stage-2 release left a TX output asserted`.

## 2026-09-21 — Simulator suite modelled RF backwards: silent while transmitting, present while receiving

`trace_ptt_sequence.py` injected the 40m Timer1 counts only in the pre-PTT preflight. Because the
firmware resets TMR1 every 10 ms tick, the measurement went stale the moment the preflight ended,
so `g_fc_status.frequency_khz` was already 0 when PTT was asserted.

The old firmware hid this: its assert-time `freq_counter_signal_valid()` check happened to land on
a tick that still held the injected value, and the scenario only passed because of that timing. It
is also physically inverted — a real radio is silent while receiving and transmits once PTT is
asserted — and under the first-dit model the stale measurement correctly leaves the amplifier in
bypass-snoop, so the baseline scenario never reached TX.

The harness now keeps the 40m snoop signal present for the whole keyed window. That models a real
transmission, and it means the baseline scenario now exercises the first-dit decode-and-engage path
instead of relying on pre-PTT RF leakage.

## 2026-09-21 — Band-selection invariants found the amplifier keying on the 160 m no-signal default

The new I1-I5 invariants (checked over every suite scenario) failed the TEMPERATURE scenario:
after the thermal trip cleared, the relay selection had followed live RF while unlocked, and with
no measurement present the classifier reported its no-signal default (160m). Stage 0 then locked
whatever `current_band` happened to hold, so the amplifier keyed on the 160 m filter while the
radio was on 40 m. Old firmware had the same hole (it refused PTT only when no band was known *at
the assertion*, which is not the recovery path).

Fixed by gating keying on an established band: `g_band_established` is set by a live confirmed
measurement, by the first-dit memory, or by the snoop decode, and is invalidated on PTT release,
at startup and on a trip recovery (which is the only mid-over path that frees the relay
selection). Stage 0 now enters bypass-snoop instead of keying when no band is established.

The harness had to model reality for this: the operator keeps the key down through a thermal
cycle, so `TEMPERATURE` now holds the 40m snoop signal present throughout (see the next entry for
why a single injection per long step was not enough).

## 2026-09-21 — Sampling aliased with the frequency-counter tick (FREQ_CTR passed standalone, failed in the suite)

`FREQ_CTR` passed on its own but failed inside the merged suite with `80m TX lock failed while
injecting 1800 kHz`. The firmware resets TMR1 on every 10 ms tick, and the harness sampled on
10 ms boundaries, so when the two aliased the samples *always* landed before the tick that
consumed the injected count - the injected reading was never observed, and the assertion failed
on a stimulus artefact. Standalone runs happened to start at a favourable phase; the suite did
not.

Fixed by sampling injected counts at 5 ms (every tick window then contains a post-tick sample) and
by adding `inject_step_hold()`, which re-injects before each 5 ms chunk inside long steps instead
of injecting once at the start of a 50 ms step.

## 2026-09-21 — Band/frequency-counter tests were weaker than their labels; Timer1 external clock is not modelled

Audited the band/frequency-counter tests in `tools/simulate/trace_ptt_sequence.py` against the
firmware. The core assertions were genuine (the injected counts invert the firmware's own
scaling, and the TX-lock check injects a different band while asserting the band did not
move), but four gaps meant they did not do exactly what they claimed.

- **The band-select outputs were never observed.** `PINS` sampled only RC0/RC1/RC5/RC6/RC7, so
  "each band stayed locked during TX" was verified only through the internal
  `g_fc_status.current_band` variable. A regression in `update_band_outputs()` would have
  passed. RD2-RD7 are now sampled and `validate_band_outputs()` asserts the relay selection
  matches `current_band` (and that nothing is driven when out of spec).
- **`--quick-bands` made the lock assertion vacuous.** It reduced `BAND_TESTS` to one entry, and
  the "inject the next band's frequency" scheme then injected the *same* frequency, which
  cannot detect a failure to freeze. Injection now always picks a frequency different from the
  band under test.
- **`FREQ_CTR_FAIL` never proved PTT was asserted.** It asserted `g_ptt_active` was never true
  but never that RC0 was driven low, so a silent pin-write failure would have passed. It now
  requires an observed RC0 low.
- **The 10m case was not a real 10m frequency.** It used 25000 kHz, outside the documented 10m
  range (28000-29700 kHz); it only passed because the classifier's accept window is wider. A
  true 10m frequency needs 70000-74250 Timer1 counts, beyond the single 16-bit `TMR1` write the
  harness performs, so the limitation is now documented instead of hidden.

End-to-end counter testing is impossible in simulation, and that is now verified rather than
assumed. MDB does provide a stimulus facility that was not being used — `stim <file>.scl`
(SCL, documented in the MPLAB X install under `docs/SCL_Users_Guide`) — and SCL processes do
run during `Stepi`. But the simulator does not implement Timer1's external clock:

```text
W0106-SIM: This device only has partial support for TMR1 peripheral.
Use internal oscillator as timer clock slection is not implemented
```

Measured with an SCL stimulus driving RD1 as fast as the simulator can represent: `print pin
RD1` reported `HIGH`/`Din` (the pin really was driven) and `T1CON` read `0x27` (CS=T1CKI,
CKPS=1:4), yet `TMR1L`/`TMR1H` and `g_tmr1_overflows` stayed `0`. Register injection is
therefore the only option. It covers the frequency maths, band classification, band-select
outputs and TX lock, but not the T1CKI pin, PPS routing, the 1:4 prescaler, or the Timer1
overflow path — those need bench validation.

Related gotcha recorded for future use: SCL pin/SFR assignment uses `<=` (`:=` is for user
variables). `RD1 = '1';` parses but derails the simulator with
`E0101-SIM: Failed to disassemble instruction`.

Verified: `ctest` passes 1/1 in 130 s with all 11 scenarios green, including the new
band-select and PTT-asserted assertions.

## 2026-09-21 — Pin/net assignments were duplicated across the docs and had drifted (single source of truth established)

The same pin and net assignments were restated in at least eight documents, and they no longer
agreed with each other or with `pin_map.h`. This is the underlying cause of the individual doc
bugs fixed earlier today.

- `docs/hardware/PIC16F18855_pin_map.md` was a **misnamed stale duplicate** of the 18875 pin
  map (28-pin SPDIP, I2C LCD backpack, LPF band-decoder bits on RA4/RA6/RA7), and nothing
  linked to it.
- `docs/hardware/wiring-checklist.md` duplicated the entire pin map and contradicted the
  firmware: it claimed a 3.3 V supply, listed RD1–RD7 and RB2/RB3 as "NC / reserved for future
  use", and proposed RA4/RA6/RA7 as future band-select pins — those are the parallel LCD lines.
- `project_schematic_package/connection_table.md` restated the netlist that already existed in
  `connection_table.csv`.
- README, `project-architecture.md`, `section_breakdown.md`, `block_diagram.md`, and the
  package `wiring_checklist.md` each restated pin assignments too.
- `AI-HANDOFF.md` claimed "RA4 and RA6 are available for future band selection" (wrong) and
  linked a `schematic-workflow.md` that does not exist.

Fix — single source of truth treatment:

- `docs/hardware/PIC16F18875_pin_map.md` is now explicitly the one authoritative pin table, and
  must agree with `firmware/include/pin_map.h`.
- `project_schematic_package/connection_table.csv` is the one authoritative netlist;
  `connection_table.md` became a short usage/conventions page instead of a second netlist.
- The misnamed duplicate was replaced with a short "not used" pointer, and
  `docs/hardware/wiring-checklist.md` was rewritten as wiring guidance that refers to signals
  rather than pins.
- README, architecture, block diagram, section breakdown, and both checklists now link to the
  pin map instead of restating it.
- Band selection and lockout are now documented in the block diagram, the architecture doc, and
  the README flow model, following the removal of the 74HC4514 decoder in favour of one
  dedicated output per band.

Rule recorded in `Ai-Notes.txt`: never restate pin numbers or pin tables outside the pin map.

## 2026-09-21 — `ctest` could not run the simulator suite (Python 2 binding + non-portable `timeout`)

`ctest` reported 0/1 passed (exit 8) on a clean checkout. `user.cmake` used
`find_program(PYTHON_EXECUTABLE NAMES python python3 REQUIRED)`, which resolved to
`/Library/Frameworks/Python.framework/Versions/2.7/bin/python`. The suite is Python 3
only, and that interpreter is an Intel-only binary on this Apple Silicon host, so the
test died before starting:

```text
timeout: failed to run command '.../Versions/2.7/bin/python': Bad CPU type in executable
```

The registration also wrapped the test in GNU `timeout`, which is not part of macOS.

Fix in `cmake/My_Pic_Project/default/user.cmake`:

- search `NAMES python3 python` and verify `sys.version_info[0] == 3` at configure time,
  so a Python 2 interpreter fails configuration with an actionable message instead of
  failing the test at run time;
- run the suite through `tools/simulate/run_suite_with_watchdog.py` (owns the MDB
  process group, cleans up stale runs, own timeout, progress logs) instead of invoking
  `trace_ptt_sequence.py --suite` under the external `timeout` binary.

`PYTHON_EXECUTABLE` is cached, so an existing build directory must be reconfigured with
`-U PYTHON_EXECUTABLE` to pick up the change.

## 2026-09-21 — README, TESTING.md, and the pin-map doc were out of sync with the current hardware and test scheme

Found while bringing `ctest` back to green.

- README described the superseded LCD and band-select scheme: a PCF8574 I2C backpack on
  RC3/RC4, and a band-decoder bus on RA4/RA6/RA7/RB6. `pin_map.h` actually drives a 4-bit
  **parallel** LCD (RS=RA4, E=RA6, D4=RA7, D5=RC3, D6=RC4, D7=RD0) and one dedicated
  active-high band-select output per band on RD2-RD7. README also linked
  `firmware/src/lcd_i2c.c`, `docs/hardware/lpf-band-select-netlist.md`,
  `docs/hardware/lpf_band_decoder.kicad_sch`, and `docs/hardware/schematic-workflow.md` —
  none of which exist.
- README claimed a self-hosted Windows x64 runner and manual-only releases.
  `firmware-build.yml` runs on `ubuntu-latest` and installs XC8/DFP itself, and
  `auto-release.yml` tags and publishes a release automatically after a successful `main`
  build.
- TESTING.md listed a non-existent `PTT_FrequencyCounter_BandLock` test, said the suite
  builds the firmware itself, documented trace PNG filenames that are never produced, and
  claimed the simulator tests run in CI on a runner with MPLAB X installed via apt. They do
  not run in CI at all.
- `docs/hardware/PIC16F18875_pin_map.md` described `OUTPUT_COMP_RESET` as an active-high
  pulse. `main.c` idles it high and drives it low for the reset/settle window
  (`apply_startup_inhibit`, `start_comparator_reset`), so it is active-low.

Fix: README now defers to the canonical pin map instead of duplicating a stale copy that
had already drifted, the dead links were replaced with real ones, TESTING.md was rewritten
to the current CTest + watchdog scheme, and the pin-map polarity note was corrected.

## 2026-09-20 — Hardware pin-map doc and sim tests out of sync with actual pinout

`docs/hardware/PIC16F18875_pin_map.md` claimed RA4/RA6/RA7 and RB2/RB3 were free,
but `pin_map.h`/`lcd_parallel.c` actually use RA4/RA6/RA7/RC3/RC4/RD0 for the
parallel LCD and RB2/RB3 for ADC_OVERDRIVE/ADC_DRAIN_PEAK (ANSELB=0x0E). Also fixed
a stale comment in `lcd_parallel.c` (said D5/D6 were RB2/RB3) and in `main.c`'s
`adc_init()` (said RA4 was reserved for an LPF band-select bus it no longer drives).
Doc now lists the true free pins: RD2-RD7, RE0/RE2/RE3 (9 pins).

Separately, `tools/simulate/test_freq_counter.py` never worked: it stimulated the
Timer1 external clock input (RD1/T1CKI) with a static pin voltage, which produces
no clock edges, so frequency_khz stayed 0 and every band assertion failed. Fixed by
writing TMR1H/TMR1L directly (same technique as trace_ptt_sequence.py's FREQ_CTR
scenario) and extending the post-release window so the relay/VCC/bias shutdown
sequence has time to complete before the band unlocks and reclassifies.

Also: `run_mdb()` in both `trace_ptt_sequence.py` and `test_freq_counter.py`
inherited our controlling terminal as stdin, so a killed/hung mdb+JVM process
could leave the shell in raw mode (looked like the terminal was "broken", e.g.
`ls` producing no visible output). Fixed by using `stdin=DEVNULL` +
`start_new_session=True` and killing the whole process group on timeout.

## 2026-09-18 — Front-panel menu now uses a single EC11 rotary encoder

The two-switch menu model became awkward as the normal display pages and saved
settings grew. It also did not match the selected front-panel actuator. Fix: the
firmware now treats RC2/RB0/RB6 as EC11 encoder A/B/push inputs. Rotation selects
normal display pages or edits the active setting, short press enters/advances
settings, and long press exits settings or clears a trip latch. RB6 was freed by
reducing the LPF band decoder bus to the required 3 bits; OFF plus seven bands fit
in codes 0-7, so the external decoder's fourth address input is tied low.

## 2026-09-18 — Peak displays now hold briefly, then decay smoothly

The PEP and current-meter pages are likely operator home pages, but the previous
peak behavior decayed by one display unit per configured interval with no explicit
hold. At the old 500 ms default this made PEP linger for minutes; at short intervals
it still looked mechanically linear. Fix: both peak displays now hold the captured
peak for the configured peak-hold interval, then decay by about 3% per configured
peak-decay interval with a minimum one-unit step. Both settings are stored in the
versioned EEPROM record. The default home page is now the PEP/temperature display;
factory defaults are 1.2 s hold and 100 ms decay interval.

## 2026-09-18 — Normal SWR displays use the available second decimal place

The STATUS and SWR meter pages had enough 16x2 LCD space for `SWR=1.02`, but the
display path rounded live SWR to tenths and left the top-right STATUS cell blank.
Fix: the display-only SWR calculation now carries hundredths, and the normal/trip
SWR render helper prints two fractional digits. Trip thresholds and trip decisions
remain in tenths and keep using the existing integer threshold comparison.

## 2026-09-18 — ADC trip sources now share the fastest bounded scan cadence

SWR/current/drain/temperature ADC faults were not all refreshed at the same rate:
the ADC scheduler gave overdrive an alternating priority slot while every other
trip channel waited on the slower round-robin path. That made non-overdrive trips
slower to observe than necessary once the expensive RF chain was already in TX.
Fix: the scheduler now advances through all eight ADC protection channels once per
1 ms tick, giving every ADC-based trip source the same ~8 ms maximum sample-age
bound. The trip logic still latches immediately once a trip-worthy sample is seen;
the change removes the unequal pre-trip sampling delay.

## 2026-09-15 — ADC ISR self-re-arm starved the main loop of CPU time

Found via MPLAB X simulation (see Ai-Notes.txt "Simulation" section): with PTT
asserted and no faults present, `update_tx_sequence()`/`update_protection_state()`
never ran even once after 30+ simulated seconds - the CPU was always caught inside
the interrupt vector on `Halt`, and the debug console was flooded with continuous
`W0223-ADC` underflow warnings. Root cause: `timer0_isr()`'s ADC branch (added in the
2026-09-12 entry below) immediately re-armed the next conversion
(`ADCON0bits.GO_nDONE = 1`) right after each conversion completed, with a blocking
`__delay_us(ADC_ACQUISITION_US)` in between - all from inside the ISR. This created a
back-to-back interrupt chain with no guaranteed idle time for the main loop between
conversions.
Fix: the ADC branch of `timer0_isr()` now only captures the completed sample and
selects the next channel; it no longer calls `__delay_us()` or re-arms the
conversion. Re-arming (`GO_nDONE = 1`) now happens only once per Timer0 tick
(~1 ms), gated by a new `tick` flag set from the `TMR0IF` branch. This paces the
8-channel scan to a full cycle every ~8 ms (still fast enough for this application)
and guarantees the main loop gets to run for the bulk of each 1 ms tick period
between conversions, regardless of how fast the ADC itself completes. Also removed
the now-redundant acquisition delay's dependency on the ISR: the ~1 ms natural gap
between ticks is vastly longer than the 5 us settle time it replaced, so no
functional accuracy regression versus the 2026-09-12 fix.
Verified via `tools/simulate/run_sim.ps1`: main-loop breakpoints (e.g.
`update_protection_state`) now hit normally and the PC advances through real code
between `Halt`s, instead of being stuck at the interrupt vector.

## 2026-09-12 — Added ADC acquisition delay after channel switch

Per the timing-budget review in docs/hardware/bench-validation.md, the ADC ISR in
`firmware/src/main.c` switched `ADPCH` to the next channel and immediately set
`GO_nDONE = 1`, with no settling time for the sample-and-hold capacitor to charge to
the newly-selected channel's voltage - a real accuracy risk depending on each
detector's source impedance.
Fix: added `ADC_ACQUISITION_US` (5 us, a common conservative industry baseline -
bench-confirm against the datasheet's acquisition-time formula for the actual
detector source impedances) as an explicit `__delay_us()` between the `ADPCH` change
and `GO_nDONE = 1`, both in the round-robin ISR and the one-time kick-off in
`adc_init()`. The delay runs inside the ISR itself, so it briefly (5 us) delays
servicing of other pending interrupts - negligible next to the 1 ms Timer0 tick.
Per-channel time goes from ~11 us to ~16 us (round-robin staleness bound ~88 us ->
~128 us), still far below the LCD-queue-drain latency addressed in the entry below.

## 2026-09-12 — LCD writes made non-blocking (queued, drained a few bytes per loop pass)

Per the reaction-time budget in docs/hardware/bench-validation.md, the bit-banged LCD
write was the dominant source of protection-loop latency: a full page redraw was
~13 ms of blocking bit-banging, during which `update_protection_state()` could not
run, so a fault occurring mid-redraw wasn't acted on until the LCD transaction
finished.
Fix: `lcd_write_byte()` in `firmware/src/lcd_i2c.c` now enqueues into a 56-entry ring
buffer (sized for the worst case: the TRIP screen with every fault reason set at
once, 49 bytes) instead of transmitting immediately. The main loop drains it via the
new `lcd_service(2)` (2 bytes/pass) after `update_protection_state()` has already run
that pass. The actual I2C bit-banging moved to `lcd_write_byte_now()`, used directly
by `lcd_init()`'s one-time startup sequence and by the "Clear Display" command on a
real page/state transition (both have their own real timing requirements and stay
synchronous; the queue is flushed first so ordering can't be disturbed). Rendering
code (`lcd_write_text`, `lcd_write_unsigned`, etc.) is unchanged - only *when* each
byte physically goes out changed, not what gets displayed. Worst-case gap between
consecutive `update_protection_state()` calls due to the LCD dropped from ~13 ms to
~0.8 ms (2 queued bytes), or ~2 ms including an occasional page-transition clear.

## 2026-09-12 — TRIP state/display cleared before the PTT re-arm, not only on it

`update_protection_state()` in [firmware/src/main.c](firmware/src/main.c) recomputed
`any_trip_fault` from live sensor readings every loop and unconditionally set
`g_state = STATE_OPERATE` the instant that reading looked clear - with no check of
`g_fault_latched`. Only `handle_ptt_transition()`'s PTT key-down path actually clears
`g_fault_latched`/`g_trip_reason`. Net effect: the TRIP screen (and `g_state`) could
silently revert to a normal STATUS screen as soon as the offending condition itself
cleared (e.g. forward power decays after unkeying), well before any new PTT keydown,
even though the fault was still latched underneath. TX sequencing itself was never
unsafe - `update_tx_sequence()` independently gates on `g_fault_latched`, not
`g_state` - but the operator-facing display didn't reflect the real latched state.
Fix: when the live condition clears but `g_fault_latched` is still true,
`update_protection_state()` now keeps `g_state = STATE_TRIP` (and the trip output
active) until the next PTT re-arm edge actually clears the latch via
`clear_fault_latches()`, matching the documented "latched until conditions are safe
and the system is re-armed" rule.

## 2026-09-12 — Remaining LCD flicker: config pages still cleared on every rapid-adjust redraw

The earlier flicker fix only skipped the LCD clear for STATUS/POWER_TEMPERATURE/TRIP.
Every other menu/config page still cleared on every redraw, and holding the ADJUST
button auto-repeats a value change (and a redraw) roughly every 100 ms - so a held
adjustment flickered exactly like the original bug did. Several of those pages also
printed numeric fields with no fixed width (`SWR full-scale`, `overdrive`, `temp
trip`, `drain trip`, `current trip`, both delay pages, `PEP decay`, and the `HIGH`/
`LOW` boolean fields), so simply skipping their clear would have left stale digits
behind when a value shrank (e.g. "100" -> "9" leaving a trailing stale "0").
Fix: the clear now only fires on an actual screen (page/state) change, for every
page, not just the three live ones; added `lcd_write_unsigned_padded()` and applied
fixed-width formatting to every previously-unpadded field so an in-place redraw is
always safe. `"LOW"` is now written as `"LOW "` (trailing space) to match `"HIGH"`'s
width.

## 2026-09-12 — STATUS page: live SWR readout, bar now tracks the selected power mode

Two follow-ups to the STATUS page requested after the PEP/RMS-label fix below:

1. The power bar on row 1 always used the PEP value (`g_post_fwd_pep_w`) even when
   RMS mode was selected, so the bar and the number above it could disagree. Fixed:
   the bar now uses the same `power_w` (PEP or RMS, per `power_display_pep`) as the
   numeric reading.
2. Added a live SWR reading, right-justified on row 0 (`lcd_write_swr_right()`).
   The display-only SWR calculation derives it from the post-filter forward/reflected ADC
   samples using the standard power-based relation
   `SWR = (1 + sqrt(Pr/Pf)) / (1 - sqrt(Pr/Pf))`, via a fixed-point integer square
   root (`isqrt32()`) since this part has no FPU. Display-only - trip logic still
   uses the existing threshold comparison in `swr_trip()`, unchanged.

Row 0 layout is now `P=nnnnW` or `R=nnnnW` (mode is now a single-letter prefix
instead of a trailing `" PEP"`/`" RMS"`) followed by right-justified `SWR=X.XX`,
filling all 16 columns.

## 2026-09-12 — Dead "SWR=" label on the STATUS page (found in review)

The STATUS page in `show_menu_page()` printed `"P=<power>W SWR="` on row 0, but no
SWR value was ever written after the label - it was leftover/incomplete text with no
basis in the documented design (docs/project-architecture.md only specifies power +
a PEP bar for this page). Computing a live SWR ratio from raw ADC counts needs a
square-root approximation with no FPU on this part, which is new numeric code in a
safety-relevant display path and out of scope for a text-label cleanup.
Fix: replaced the dead label with `" PEP"`/`" RMS"`, reusing the already-available
`power_display_pep` flag so the row now tells the operator which reading mode they're
looking at instead of showing an unfulfilled promise of a value. (Superseded by the
entry above, which adds the actual SWR value.)

## 2026-09-12 — LCD full-clear on every refresh caused flicker (found in review)

`show_menu_page()` in [firmware/src/main.c](firmware/src/main.c) unconditionally sent
the HD44780 "Clear Display" command (`0x01`) plus a 2 ms delay on every call. The
STATUS and POWER/TEMPERATURE pages are redrawn every 100 ms during normal operation,
and the TRIP screen was redrawn identically every 100 ms while latched, so the
display blanked and repainted at ~10 Hz - a visible flicker on real hardware, worst on
the continuously-updating PEP bar.
Fix: track the last-drawn (menu page, state, trip reason) and only send the clear
command when that identity actually changes. Live pages now update their
fixed-width fields in place each refresh; the temperature field on the
POWER/TEMPERATURE page was also space-padded to a fixed 3 digits so no stale digit
can be left behind now that the clear is skipped between refreshes. Config/setting
pages keep the previous clear-per-change behavior since they only redraw on an
actual button press, not a timer.

Also added, as related usability fixes:
- an 8 s menu-inactivity timeout that returns the display to STATUS from any config
  page (`MENU_IDLE_TIMEOUT_MS` in `poll_menu_inputs()`), and
- forcing the display back to STATUS the instant PTT is asserted
  (`handle_ptt_transition()`), so an operator can't key up onto a frozen config page.

## 2026-09-12 — Found while removing the warning system (KISS refactor)

While rebuilding `g_menu_setting_offsets`/`g_menu_setting_types` in
[firmware/src/main.c](firmware/src/main.c) to drop the temperature/overdrive/drain
warning tiers, three pre-existing type-tag mismatches were discovered in the same
tables. These were latent bugs, unrelated to the warning-system removal itself, and
were fixed in the same commit since the tables had to be rewritten anyway.

1. **`current_trip_a` read/written as the wrong size.** The struct field was declared
   `unsigned char` but tagged `MENU_SETTING_U16` in the settings table, so the menu code
   read/wrote 2 bytes at a 1-byte field's offset — corrupting the low byte of the next
   struct field (`tx_vcc_delay_ms`) every time the CURRENT TRIP setting was adjusted.
   Fix: widened `current_trip_a` to `unsigned int` to match how it was actually accessed.

2. **`tx_bias_delay_ms` misclassified as `MENU_SETTING_BOOL`.** The struct field is
   `unsigned int` (a millisecond delay, 0-1000 ms), but its table entry was tagged BOOL.
   This meant pressing "increase" on the TX-BIAS DELAY menu page toggled the low byte
   of the delay value on/off instead of incrementing it — the intended 5 ms step logic
   further down in the setting-adjust path was unreachable dead code for this page.
   Fix: retagged as `MENU_SETTING_U16`.

3. **`power_display_pep` misclassified as `MENU_SETTING_U8`.** The struct field is
   `bool`, but was tagged as a plain ranged 0-100 byte. Pressing "increase" repeatedly
   on the POWER DISPLAY menu page would count up past 1 instead of cleanly toggling
   PEP/RMS, requiring a long "decrease" hold to get back to RMS.
   Fix: retagged as `MENU_SETTING_BOOL`.

Also bumped `SETTINGS_VERSION` (4 -> 5) so EEPROM records saved by older firmware
(with the old struct layout) are rejected by the checksum/version check on next boot
and the new compiled defaults load cleanly, rather than misinterpreting old bytes
under the new field layout.
