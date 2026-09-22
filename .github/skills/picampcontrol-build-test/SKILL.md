---
name: picampcontrol-build-test
description: "Use when building, testing or debugging PicAmpControl firmware: Debug or Release builds, CMake configuration, ctest, run_tests.sh, simulator/mdb runs, the VS Code Simulate debug session, breakpoints and symbol reads, PTT/frequency-counter tests, band-lock tests, first-dit band detection, remembered-band fold-back, band-change/hot-switch guards, or build/test failures."
---

# PicAmpControl Build, Test and Debug

Use this skill for firmware builds, simulator verification and simulator debugging. Do not claim success from a missing or truncated terminal response; require a fresh exit code and final output.

Always use the **file-based pattern**: redirect every test command's output to a log file, append the exit code, and read the verdict from that file. MDB emits megabytes of trace, and the terminal scrollback and output capture regularly lose the pass/fail line (a command can even come back with no captured output while the run is still going). Never conclude anything from an empty terminal response - check the log and the exit-code line.

Always clean up an earlier run before starting another. The MDB suite can outlive a terminal wrapper if the wrapper is interrupted, and a stale Java/MDB process can make the next run appear hung.

## Repository facts

- CMake source directory: `cmake/My_Pic_Project/default`
- Debug build directory: `_build/My_Pic_Project/debug`
- Release build directory: `_build/My_Pic_Project/release`
- Firmware ELF used by MDB: `out/My_Pic_Project/default.elf`
- Merged simulator suite: `tools/simulate/trace_ptt_sequence.py --suite`
- Cleanup-aware suite launcher: `tools/simulate/run_suite_with_watchdog.py`
- First-dit band-detection proof (own MDB session): `tools/simulate/test_first_dit.py`
- Shared band-selection invariants: `tools/simulate/first_dit_invariants.py`
- CTest registration: `cmake/My_Pic_Project/default/user.cmake`
- CTest tests: `PTT_SequencerAndTripSuite` (labels `sim;suite`) and
  `FirstDit_BandDetectionAndHotSwitchGuards` (labels `sim;first-dit`)
- The standalone `test_freq_counter.py` is not the authoritative suite; frequency and band checks are merged into the PTT suite.
- Harness fault injection reads symbol addresses from `out/My_Pic_Project/default.sym` (regenerated every build).
- Design reference for the first-dit model, the invariants, and the defects each test is proven to catch: `docs/first-dit-band-detection.md`.
- Evidence log for defects found while testing: `bugfixes.md` (read it before "fixing" a suspicious harness assertion).
- VS Code debug config: `.vscode/launch.json` → `Simulate PicAmpControl (Debug)` (`mplab-core-da`, tool `Simulator`, device `PIC16F18875`, program `out/My_Pic_Project/default.elf`).
- Symbol table for breakpoints and harness state reads: `out/My_Pic_Project/default.sym`.
- **The workspace build tasks in `.vscode/tasks.json` are Windows-only** — they hard-code `E:/hamcode/PicAmpControl/...`, so on this macOS checkout they fail immediately. Do not reach for `Build PicAmpControl (Debug/Release)` here; use the commands in this skill.

## Toolchain setup

On macOS, use the installed XC8 toolchain under `$HOME` (the MPLAB X installer also exposes it
at `/Applications/microchip/...`; either works):

```text
$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin
```

On Windows it is `C:/Program Files/Microchip/xc8/v4.00/bin`, and `%USERPROFILE%/.mchp_packs` holds
the DFP packs (`$HOME/.mchp_packs` on macOS). Use `$HOME`/`%USERPROFILE%` rather than a literal
home directory: the committed docs and config must not carry a developer's account name, and the
paths differ per machine.

`.clangd` **is** tracked and is deliberately machine-agnostic - do not add absolute include paths
back to it, and do not untrack it. It needs none: `CompilationDatabase` is relative to the config
file, the compile database CMake generates already carries that machine's compiler and `-mdfp` pack
path, and clangd then queries that compiler for its system includes ("System includes extractor:
successfully executed xc8-cc"), so the XC8 and DFP directories resolve automatically on either OS.
The firmware's own headers are included with relative paths (`../include/...`), so they need no `-I`
either. Verified on clangd 19.1.7: with no `-I`/`-mdfp` lines, `--check firmware/src/main.c` reports
0 errors. (An earlier revision of this file hard-coded one machine's home directory, which both
published a developer's account name and broke the other platform - see `bugfixes.md` 2026-09-21.)

Before building, check that `xc8-cc` exists. Existing build caches may contain the invalid compiler value `c`; explicitly override the compiler paths when reconfiguring. The repository root has no `CMakeLists.txt`, so do not configure with `cmake --preset` from the root unless the preset is first corrected to specify the nested source directory.

## Debug build

```sh
cmake -S cmake/My_Pic_Project/default \
  -B _build/My_Pic_Project/debug \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_TOOLCHAIN_FILE="$PWD/cmake/My_Pic_Project/default/.generated/toolchain.cmake" \
  -DCMAKE_USER_MAKE_RULES_OVERRIDE="$PWD/cmake/My_Pic_Project/default/.generated/overrides.cmake" \
  -DXC8_BIN_DIR="$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin" \
  -DCMAKE_C_COMPILER="$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-cc" \
  -DCMAKE_ASM_COMPILER="$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-cc" \
  -DCMAKE_AR="$HOME/tools/microchip/xc8/v4.00/xc8-v4.00/bin/xc8-ar" \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build _build/My_Pic_Project/debug -j4
```

## Release build

Use the same configure command with:

```text
-B _build/My_Pic_Project/release -DCMAKE_BUILD_TYPE=Release
```

Then run:

```sh
cmake --build _build/My_Pic_Project/release -j4
```

**Both configurations link to the same `out/My_Pic_Project/default.elf`.** A Release build
replaces the ELF that MDB loads, and its stripped/optimized symbols break the `print <var>`
reads the harnesses depend on. After any Release build, delete that ELF and rebuild Debug before
running the simulator tests - Ninja will otherwise report "no work to do" and leave the Release
binary in place:

```sh
rm -f out/My_Pic_Project/default.elf
cmake --build _build/My_Pic_Project/debug -j4
```

## Flash space

**Reducing flash is a standing work item, not a nuisance to tolerate (user instruction,
2026-09-21).** A near-full Debug image is not an acceptable steady state. Concretely:

- When a build or test run leaves you waiting, spend that time finding space - do not idle.
- **Inline assembly is acceptable here, on one condition:** every block must carry an equivalent-C
  comment so it can be reviewed and re-derived. An uncommented asm block is not acceptable.
- Every saving is a code change like any other: it must keep the tests green, and ideally be proven
  by a fault injection. Space is never "free" just because the tests happen to pass.
- The purpose of the headroom is to be able to assert **strongly, and with test evidence, that the
  PTT sequencing cannot damage the amplifier** - the silicon in this project is expensive and the
  safety argument has to be airtight. No gaps, no excuses.

Known reduction levers, in rough order of value:

1. Table-drive the long `if`/`else` chain in `adjust_selected_setting()` (est. 80-100 words). The
   per-setting min/max/step bounds are irregular, so it needs a new menu-edit scenario in the suite.
2. Compile the translation units the harness does NOT read (`lcd_parallel.c`) at `-Os` in the Debug
   build; the harness only needs symbols from `main.c` and `freq_counter.c`.
3. Bit-pack the menu metadata (`g_menu_setting_offsets[]` 20 B + `g_menu_setting_types[]` 20 B).
4. Shorten the remaining display strings.
5. Only if the user explicitly agrees: build the whole Debug image `-Os` - it costs ~1200 words but
   silently breaks MDB symbol and breakpoint resolution.

Flash is the binding constraint on this project, and it is easy to trip from a test change:

- Release (shipping) uses ~6899/8192 words = ~84% used; Debug is the binding one at 8117/8192 = 99.1%
  (2026-09-21 snapshot - always read the current value from `memoryfile.xml`, and note that the same
  figures are tracked in `Ai-Notes.txt` under "Device memory usage").
- Debug is deliberately compiled `-O1` (not `-Os`) so MDB can resolve symbols and breakpoints. That is why the build the simulator loads is far closer to the limit than the shipped build. Budget against the Release number.
- A link error reporting that program space is exhausted reproduces in the Debug build first, long before Release breaks. It reads as `(1347) can't find 0xN words ... for psect "<name>" in class "<class>"` and lists several psects, because the last few words are fragmented. Treat it as a signal that the test image needs `-O1` kept and the change needs to be smaller — not as a reason to switch Debug to `-Os`, which would silently break MDB symbol resolution. Read the exact figure from `memoryfile.xml` rather than guessing at the wording of the linker message.
- The cheapest room is in string literals (`STRCODE`), which the linker fails to place first. On
  2026-09-21 the LCD menu labels and boot text were shortened to reclaim ~72 words; that is the
  precedent to follow before reaching for anything structural, but it is a user-visible change - ask.
- Prefer table-driven logic over long if/else chains when adding firmware code, and ask before adding code.

## Simulator verification

Run the full merged suite with the cleanup-aware launcher. This is the default test workflow: it records its PID, kills a stale prior launcher, owns the MDB process group, logs raw MDB stderr, records 10-second progress heartbeats, and cleans up on timeout or Ctrl-C:

```sh
python3 tools/simulate/run_suite_with_watchdog.py --timeout 180
```

Use the full five-minute default verification before calling the suite green:

```sh
python3 tools/simulate/run_suite_with_watchdog.py --timeout 300
```

For a fast diagnostic run only, use one happy band plus the deliberate missing-frequency failure case:

```sh
python3 tools/simulate/run_suite_with_watchdog.py --quick-bands --timeout 180
```

This is diagnostic only. The default command remains the full six-band suite.

Start this command in a fresh VS Code terminal/execution context. The launcher creates a new process group for the suite, so the caller can be interrupted without attaching the next run to an old MDB process. Do not reuse a terminal that still has a prior suite command queued.

Progress is written to `/tmp/picampcontrol_suite_progress.log`; live MDB output is written to `/tmp/picampcontrol_mdb_progress.log`.

The launcher owns `/tmp/picampcontrol_suite.pid` and also scans for orphaned `mdb`, `run_suite_with_watchdog.py`, and `trace_ptt_sequence.py --suite` processes at startup. Before manually killing a run, read that PID and terminate the process group, then remove the PID file. Verify no `trace_ptt_sequence.py --suite` or `mdb.sh` process remains before starting another run. Do not kill unrelated compiler language servers or system Java processes.

The live MDB log is intentionally separate from the suite result log. MDB produces a large amount of trace output because every simulator sample prints pins and state variables. During a long run, inspect both logs:

```sh
tail -n 20 /tmp/picampcontrol_suite_progress.log
tail -n 20 /tmp/picampcontrol_mdb_progress.log
```

The diagnostic runner should record periodic heartbeats containing:

- elapsed time and child exit status
- suite-log byte count
- MDB-log byte count
- the latest MDB output tail

If MDB-log bytes continue increasing, the simulator is working slowly rather than hung. In a recent full run, MDB output grew from about 47 bytes at startup to more than 3 MB while still progressing. The volume is expected to increase as all six bands and repeated TX scenarios are added, but it can make the run take substantially longer than the original two-minute test.

`trace_ptt_sequence.py` normally buffers MDB output until the process exits. Set `PICAMP_MDB_DEBUG_LOG` to enable its live stream drain for diagnosis; do not enable it for ordinary runs unless progress investigation is needed.

The suite must cover:

- all six nominal bands in RX preflight
- TX lock behavior for every band
- normal PTT/trip scenarios
- `FREQ_CTR_FAIL`, where no Timer1 signal must hold PTT latched in bypass-snoop with every TX
  output inactive and no band locked (first-dit model, not a refusal)
- the band-selection safety invariants over every scenario (`validate_keyed_band_invariants`,
  `validate_band_changes_are_cold` and `validate_t_r_closes_only_after_band_settle` in
  `tools/simulate/first_dit_invariants.py`): I1 no relay move
  between consecutive keyed samples, I2 never keyed while the band is unlocked, I3 never keyed
  while snooping, I4 the band-select output pins agree with `current_band`, I5 every relay move
  seen with the amplifier cold, I6 every T/R relay close follows a band relay selection that has
  already settled (never hot-switch the band relay)

`test_first_dit.py` additionally covers the first-dit clauses end to end in its own MDB session:
clause (a) bypass with no band, (b) first-burst decode with bypass held for `BAND_SETTLE_MS`,
(c) instant warm re-key with no RF injected, (d) cache expiry, (e) band re-detection, (f) a
hot-switch fault injection, and (g) the remembered-band fold-back - engage on a remembered 160m,
change to 80m, and assert the firmware forces bypass before releasing the band so the relay can
follow the new frequency. Both harnesses share `first_dit_invariants.py`, and the defects that
test is proven to catch are listed in `docs/first-dit-band-detection.md`.

For a bounded run:

```sh
timeout 150 python3 -u tools/simulate/trace_ptt_sequence.py --suite
```

Do not launch another suite while this launcher is running. If an old run exists, starting the launcher cleans it up through `/tmp/picampcontrol_suite.pid`. A terminal response with exit `130`, `142`, no output, or an empty log is not a pass; inspect the saved logs and process state.

### Injecting stimuli and faults into the harness

Two techniques matter when writing or repairing a scenario, both already implemented in
`test_first_dit.py`:

- **RF is injected by writing the counter, not by driving the pin.** Set `TMR1H`/`TMR1L` to
  `counts = frequency_khz * 1000 / 400`. Because the firmware resets Timer1 on every 10 ms tick,
  an injection made once before a long step reads as an empty gate window afterwards, and the
  classifier reports its no-signal default of 160m. Re-inject before each short chunk inside a
  long step (`inject_step_hold()`), sample at 5 ms rather than on 10 ms boundaries, and keep the
  band frequency present for the whole keyed window when modelling a transmitting radio.
- **Firmware state is injected by address, not by name.** MDB in this version cannot write a C
  variable by symbol - `write g_x 1` fails with `For input string: "<addr> "`, and so does
  `print /a g_x`. Read the address from `out/My_Pic_Project/default.sym` (lines look like
  `_g_band_cache_idle_ms B4 0 BANK1 1`) and use `write /r 0x<addr> <lo> <hi>` for a 16-bit value
  (little-endian, one byte per word) or a single byte for a bool/enum. Addresses move on every
  rebuild, so parse the `.sym` at run time.

## CTest

The registered `PTT_SequencerAndTripSuite` test runs the merged suite through
`run_suite_with_watchdog.py`, so it owns the MDB process group, cleans up stale runs, and
enforces its own timeout without depending on the non-standard macOS `timeout` binary.
The suite is Python 3 only: configuration fails fast if the discovered interpreter is not
Python 3, and `PYTHON_EXECUTABLE` may be stale in an existing cache, so clear it with
`-U PYTHON_EXECUTABLE` when reconfiguring.

Run CTest with **all output redirected to a log file**. The MDB trace is megabytes of pin
and state dump; printing it to the terminal overflows the scrollback and loses the result.

```sh
ctest --test-dir _build/My_Pic_Project/debug --output-on-failure > /tmp/pac_ctest.log 2>&1
echo "CTEST_EXIT=$?" >> /tmp/pac_ctest.log
```

Both tests run by default (~3 min together). Run one at a time when iterating - the first-dit
proof is ~20 s against the suite's ~2.5 min:

```sh
ctest --test-dir _build/My_Pic_Project/debug -R FirstDit
ctest --test-dir _build/My_Pic_Project/debug -R PTT_Sequencer
ctest --test-dir _build/My_Pic_Project/debug -L sim
```

Neither test may run concurrently with the other: each owns MDB, and the suite launcher kills
stray MDB processes at startup.

Run that detached (or let it finish) and read the verdict from `/tmp/pac_ctest.log`. Do not
re-run another suite while one is active, and do not reuse a terminal that still has a prior
ctest/suite command queued.

Confirm that CTest discovers the merged `PTT_SequencerAndTripSuite` test
(`ctest --test-dir _build/My_Pic_Project/debug -N`). Report zero discovered tests as a
configuration failure, not success.

## Debugging

Two ways in, both against the simulator:

**VS Code GUI session.** Launch `Simulate PicAmpControl (Debug)` from `.vscode/launch.json` (breakpoints, variables, watch, registers, no terminal). It needs `out/My_Pic_Project/default.elf` to exist, so build first - and see the shared-ELF trap above, because a Release build leaves an optimized binary there and the session then misbehaves. Pin and register names cannot be pre-seeded through a file; add `PORTA`/`PORTB`/`PORTC`, `LATA`/`LATB`/`LATC`, `TRISA`/`TRISB`/`TRISC` or bitfields like `PORTCbits.RC5` to the Watch panel by hand.

**Headless `mdb`.** `tools/simulate/run_sim.sh [scenario.mdb]` builds, programs the simulator, and filters the benign `W0106-SIM` TMR1/3/5 warnings. Useful scripting commands: `break <function>` / `break <file>:<line>` with `Run`/`Continue`/`Halt`, `Stepi <count>` to single-step, `Stopwatch` for simulated elapsed time, `print pin <name>` to read an output and `write pin <name> high|low|<N>v` to drive an input. Scenario files must contain plain commands only - a `;` or `#` comment line aborts the rest of the script.

Prerequisites that decide whether debugging works at all:

- **Symbols come from the Debug build.** `user.cmake` compiles Debug with `-O1` and Release with `-Os` per configuration precisely so breakpoints and symbol reads resolve; a bare `-Os` overriding an `-O0` is a past bug that silently broke them, so if breakpoints on functions or statics stop resolving, read that file first.
- **You cannot write a C variable by name.** `write g_x 1` fails with `For input string: "<addr> "`, and `print /a g_x` fails the same way. Inject state by address from `out/My_Pic_Project/default.sym`, using `write /r 0x<addr> <lo> <hi>` (little-endian, one byte per word). Addresses move on every rebuild, so parse the `.sym` at run time.
- **The simulator is a debugger model, not silicon.** Timer1's external clock is not modelled and the suite injects `TMR1H`/`TMR1L` instead (see the triage section); exact timing still needs the bench. The simulator notes in `Ai-Notes.txt` are the reference for what the model does and does not implement.
- If the CPU appears stuck at the interrupt vector with continuous `W0223-ADC` spam on every `Halt`, suspect the ADC-ISR starvation bug class recorded in `bugfixes.md` rather than a debugger fault.

## Known snags (each one cost real time - do not rediscover them)

- **Do NOT swap the target device without first checking that MPLAB models it equivalently.** On
  2026-09-22 the PIC16F18877 (same family, 40-pin PDIP, 4x flash and RAM, ~£2, in stock) was trialled
  as a drop-in upgrade for the PIC16F18875. It **builds perfectly** - the whole change is
  `-mcpu=16F18877` in `.generated/rule.cmake` plus the `__16F1887x__` defines and `.clangd` - and
  gives 8117/32768 words = 24.8% flash, 365/4096 bytes = 8.9% RAM. `mdb` also **accepts** the device
  and runs the script. But the firmware then behaves differently: **0 keyed runs**, only 3 band-select
  changes (all `locked=false`), and `g_state` never reaches STATE_BYPASS_SNOOP, so `test_first_dit.py`
  aborts at the first clause with `clause (a): snooping did not report STATE_BYPASS_SNOOP`.
  Band-change timing is unchanged (1161/1705ms vs 1162/1699ms), which rules out a clock-rate
  difference, and `ANSELC = 0x00` / `TRISC0 = 1` / `WPUC0 = 1` are already set in `main.c`, which
  rules out a pin-config omission. The pattern says the firmware never sees PTT asserted on the
  18877 model. Reverted.
  **The lesson: a clean build says nothing about the simulator.** Every suite in this project runs on
  `mdb`, so a device whose model is not verification-equivalent trades verified behaviour for
  headroom - never worth it here. Check the simulator first, and treat an unexplained behaviour change
  on the new device as a blocker, not a puzzle to work around.
- **Delete large logs as soon as their verdict is read.** MDB transcripts and captured suite output
  run to megabytes. Remove them (`rm -f /tmp/<log>`) the moment the verdict has been extracted, and
  do not leave them on disk even in `/tmp`. Keep a log only while its run's verdict is still needed;
  never accumulate a series of run logs. Copying a log to a second path to defeat a stale read (see
  below) doubles the space, so delete both once read.
- **A fault-injection proof must fail on the clause that names the defect.** Re-introducing a defect
  can trip an *earlier* clause instead, because the suite is one continuous MDB session and one phase
  feeds the next. That is still evidence the defect is caught, but it is NOT evidence for the clause
  you wrote - record the failure message actually observed, and if it does not name your clause,
  either make the injection narrower or say plainly that the clause's own proof is outstanding. Do
  not upgrade an incidental cascade into a claim about the new clause.
- **Clause (d)'s idle-counter check was layout-sensitive; it is fixed - do not reintroduce the old
  form.** It used to build its delta list from consecutive entries of the *filtered* idle-sample list,
  so exactly one delta always spanned the keyed gap between two released runs, and the assertion
  required `len(resets) == 1`. Shift the phase boundary by a single sample and that one pair splits
  into a small positive plus a large negative: two "resets", and the clause fails for reasons that
  have nothing to do with the firmware. Fixed 2026-09-21 by grouping released samples into runs that
  are adjacent in the transcript (`idle_runs()`) and validating each run against **its own measured
  span**, not an assumed sample spacing - these phases mix 1 ms and 10 ms steps, so a fixed-spacing
  assumption is wrong even within one run. Symptom to watch for: a fault-injection run failing at
  clause (d) instead of at the clause under test.
- **A foreground `test_first_dit.py` run can be killed by the terminal capture.** Twice on 2026-09-21
  it came back with `Command produced no output`, exit `130`, and an **empty** log - the run never
  happened. Do not treat that as a pass or a fail. Check that the log is non-empty before judging
  anything, and launch these runs in the background (async) with output redirected, which is
  reliable; if the shell is wedged, `workbench.action.terminal.killAll` first.
- **A log read back through a file tool can be STALE.** Reading a log while it is still being
  written, or re-reading a path that was read earlier in the same session, can hand back an old copy
  - which looks exactly like "the run produced nothing". Copy it to a path that has never been read
  before (`cp /tmp/run.log /tmp/run_v2.log`) and read that, incrementing the suffix each time. Never
  judge a run from a log path you have already read.
- **Never reuse a log path across runs.** Truncate it (`> file`) or use a new name per run, or a
  stale verdict from an earlier run is indistinguishable from the current one. The appended
  exit-code line only helps if the file was genuinely rewritten.
- **The terminal's output capture can die and take the run with it.** A long suite printed enough to
  make VS Code report "Output exceeded terminal scrollback; beginning of output was lost", after
  which every command in that shell returned no output at all while the once-healthy run had stopped
  mid-trace. Recover with `workbench.action.terminal.killAll` and a fresh command; prevent it by
  launching long runs in the background with everything redirected to a file, so the run does not
  depend on the terminal staying healthy.
- **A stale PID file stops the next launch before it starts.** `run_suite_with_watchdog.py` kills the
  previous run's process group at startup and dies with `PermissionError: [Errno 1] Operation not
  permitted` from `os.killpg` when `/tmp/picampcontrol_suite.pid` belongs to a run that is already
  gone. `rm -f /tmp/picampcontrol_suite.pid` and relaunch.
- **A missing program-memory line means "nothing was relinked", not "no space used".** Both
  configurations link to the same `out/My_Pic_Project/default.elf`, so after a Release build the
  Debug `cmake --build` can print no summary at all because Ninja has no work to do. Force the relink
  with `rm -f out/My_Pic_Project/default.elf` before the Debug build.
- **`test_first_dit.py` can only inject the variables in `SYSTEM_SYMBOLS`** (`g_band_cache_band`,
  `g_band_cache_idle_ms`). Writing any other name raises `KeyError: '<name>'` before the simulator
  even starts. Either add the name to `SYSTEM_SYMBOLS`, or drive the state through the firmware's own
  mechanism - it puts the cache back into bypass-snoop by injecting an idle count past
  `IDLE_TIMEOUT_MS` rather than clearing `g_band_cache_valid`, which is not injectable.

## Failure triage

- `Frequency counter failed to classify ...`: inspect the scenario name, `FREQ_DEBUG` lines, Timer1 writes, measured `frequency_khz`, `current_band`, `band_locked`, PTT state, and sequence stage.
- `<band> TX lock failed while injecting <N> kHz`: check the injection timing before you touch the
  firmware. This signature is usually a stimulus artefact of the 10 ms tick resetting Timer1 while
  the harness sampled on 10 ms boundaries, so the sample always landed before the tick that
  consumed the count. It is the classic "passed standalone, failed in the suite" case (a
  standalone run can start at a favourable phase). Fix it with 5 ms sampling and
  `inject_step_hold()`; the historical instance is logged in `bugfixes.md`.
- A band assertion that "fails" only under `--quick-bands`: check whether the scenario is still
  injecting a frequency that actually differs from the band under test. Injecting the same
  frequency makes a lock-freeze assertion vacuous.
- `did not clear and re-enter TX after a PTT re-arm`: the re-arm must keep a valid Timer1 count
  present across the keyed window (see the injection notes above); a fault scenario must not
  re-assert PTT with frequency `0`.
- `I1:`/`I5:` or `clause (x):` failures naming a HOT SWITCH mean the invariant caught a real
  firmware defect, not a test problem. Do not relax the invariant to get green - fix the ordering
  so the amplifier is bypassed before the relay selection moves. `I2: amplifier keyed with the
  band unlocked` and `I4:` (relay pins disagreeing with `current_band`) are the same class.
- `FREQ_CTR_FAIL` must remain a negative test and must prove no active TX stage and inactive TX outputs.
- Band/frequency-counter coverage is deliberately indirect. The MPLAB X simulator does not
  model Timer1's external clock (it warns `W0106-SIM: ... partial support for TMR1 ...
  timer clock selection is not implemented`), so the suite injects `TMR1H`/`TMR1L` rather than
  clocking the pin. Do not try to "fix" a frequency-counter failure by driving RD1: an SCL
  stimulus (`stim <file>.scl`) does drive the pin correctly — verified, `print pin RD1`
  reports HIGH/Din — but `TMR1L`/`TMR1H` still stay 0. T1CKI, PPS routing, the 1:4 prescaler
  and the Timer1 overflow path can only be validated on the bench. For SCL syntax note that
  pin/SFR assignment uses `<=` (`:=` is for user variables); `RD1 = '1';` breaks the simulator.
- MDB output ending without a final validator line is inconclusive; inspect the saved log and process table.
- Keep source fixes separate from test-harness timing fixes. Re-run the narrow failing scenario first, then the full suite.
- If the terminal wrapper reports a command as finished while the PID file remains, the run is still active or the wrapper lost control of it. Kill the recorded process group before doing anything else.

## Reporting

Report:

0. **Commit and push as you go - local and remote.** As soon as a change is verified green, commit
   it and push to `origin/main`. Do not batch a session's work into one large commit at the end, and
   never leave verified work sitting only in the working tree. Small verified commits are the rule;
   the only acceptable reason to hold one is a verdict that is still running, and then it is
   committed the moment that verdict reads green. This is a standing user instruction - it has been
   forgotten before.

1. Debug and Release build exit status and important compiler/linker warnings, plus the program-memory figure when a build is near the limit.
2. CTest test discovery and result.
3. Merged suite exit status, elapsed time, and final pass/fail line.
4. The first failing scenario and its diagnostic state, if any.
5. Whether a fix that touched `firmware/` was pushed and whether the triggered `PIC firmware build` run for that commit succeeded (repo convention: commit and push verified-green work promptly, then confirm the triggered CI build rather than waiting for it before pushing).

Never say all tests are green unless Debug/Release and the requested test command have fresh successful exit codes, read from a log file rather than the terminal.
