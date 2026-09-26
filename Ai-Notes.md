# Project Status Notes

This file is the AI launch point for a new session: keep it ALWAYS up to date.
Update the Date and any changed sections whenever design, firmware, docs, or
CI/release workflows change - don't let it go stale.

## THE DEVICE: PIC18F47Q10, AND NOTHING ELSE (user instruction, 2026-09-23)
**PIC18F47Q10 ONLY. There is no second device, no "legacy part", and no device to choose
between.** The PIC16F18875 port was removed on 2026-09-23: its `#if defined(__18F47Q10__)` code
paths, its `-DPICAMP_DEVICE=PIC16F18875` build option, its CI matrix entry, its `.vscode` defines
and include paths, its `run_sim.sh`/`run_sim.ps1` default device, and its entries in these notes
were all deleted. Concretely, that means:
- **Nothing here forbids a future device change** (user, 2026-09-24: *"WE may want to upgrade in
  future"*). When one happens it is a deliberate, complete port on its own branch - not a dual-device
  facility, and not per-device machinery carried "just in case" in the meantime.
- Historical material about the 16F port, and the abandoned PIC16F18877 evaluation, now lives only
  in `prototype_reference/` and `bugfixes.md`. Do not restate it in `docs/`, `README.md` or here.
- The one deliberate exception: `tools/setup/parameterise_device.py` still *pattern-matches* the 16F
  tokens, because MPLAB X emits them when it regenerates `.generated/rule.cmake` from the MPLAB
  project the tree was created from. Those are the generator's tokens, not our target - removing the
  match would let a regenerated rule.cmake silently build the wrong part.

## Standing AI instructions (things the user asked to always remember)
- EVERY SIMULATOR TEST RUNS THROUGH THE WATCHDOG - ALWAYS (user instruction, 2026-09-23: "ALL these
  tests should run through the watchdog -- always"). Wrapped entry points, why a bare run is useless
  and how a new test gets wrapped: `.github/skills/build-test/SKILL.md`.
- NEVER ASK FOR OR ALLOW TERMINAL OUTPUT IN THE FIRST PLACE, not just "never judge a run by it"
  (user instruction, 2026-09-26). The reason we use FILES and watch them instead is that terminal
  output often BREAKS the terminal. Verdicts come from FILES (user instruction, restated 2026-09-21
  and again 2026-09-23: "we should not ask for terminal output when running tests -- this breaks the
  terminal. We are using a file-based approach instead."). The verdict method, the redirect/exit-code pattern and the two
  traps (a command that returns nothing says nothing about the run; a stale cached log read looks like
  "the run produced nothing") are in `.github/skills/build-test/SKILL.md`.
- Keep this file (Ai-Notes.md) ALWAYS up to date; it's the launch point for a new session.
- BARE-METAL FIRMWARE RULES live in `.github/instructions/firmware.instructions.md`, which VS Code
  auto-applies when `firmware/` files are edited or written (register/LAT-PORT handling, ISR discipline,
  `volatile`, config words, the clock chain). `deepseek-pic.md` - another agent's checklist, the source
  of those rules and a required step-one read from 2026-09-22 - was merged into that file and DELETED on
  2026-09-24, along with its stale `<session_state>`; its harness-design rules moved to
  `.github/skills/build-test/SKILL.md` and its "comment heavily / code in markdown blocks" output block
  was already superseded.
- FILE FOLLOWING AND LOG WATCHING: method in `.github/skills/build-test/SKILL.md` (`open_progress_log.py`,
  `run_detached.py`, the Log Viewer extension, the FileTail cost finding, the console-tail trap). The
  in-repo `tools/logfollower` follower was DELETED 2026-09-24 (it stole window focus); the marketplace
  `berublan.vscode-log-viewer` replaces it. **OPEN THE LOG TAB ON EVERY RUN - it is a REQUIREMENT
  (2026-09-26), and it may be the current/active tab. The only thing forbidden is SNATCHING FOCUS:
  never `code -r` (raises VS Code over the user's current work). The watchdog opens the log via
  `open_progress_log.open_in_editor()` -> the `tools/simshow/` helper, which opens with
  `preserveFocus` (tab appears, focus stays put). A relative `--log` path broke this (the helper
  made a `file:///_build/...` URI from the wrong cwd) - fixed 2026-09-26 by resolving to absolute.**
- DO NOT HEDGE (2026-09-24): no "I can fix it -> actually -> wait -> or even..."; no "maybe/perhaps/
  I think". State what you know and the next action, and act. Also: go with first instinct and prove it
  with a quick test rather than re-deriving the same deduction in circles. Detail in the build-test skill.
- Keep README.md and docs/ purely current-facing: no "old prototype was replaced by..." style historical narrative. Historical context belongs only in prototype_reference/.
- docs/hardware/PIC18F47Q10_pin_map_and_setup.md is the SINGLE source of truth for MCU pin assignments. Never restate pin numbers or pin tables in README, architecture, schematic-package, or checklist docs - link to it instead. Keep it in sync with firmware/include/pin_map.h. The same rule applies to nets (project_schematic_package/connection_table.csv) and the BOM (component_list.csv).
- Any new "remember this" instruction from the user must be added to this section, not just kept in assistant memory.
- The firmware is the single source of truth for which PIC we are using: PIC18F47Q10-I/P (40-pin PDIP), declared once in `cmake/My_Pic_Project/default/device.cmake` and emitted into `.generated/rule.cmake` as `-mcpu=18F47Q10` (mirrored in `.clangd`). If a document disagrees with the firmware about the target device, the firmware wins and the document is the bug.
- Do NOT reintroduce schematic automation. Both attempts (EasyEDA, then KiCad/MCP) were abandoned and
their traces deleted: no generators, no MCP schematic servers, no `.kicad_sch`/`.eext` tooling, no
node/npm scaffolding, and no tool-specific symbol references in the pin map. Netlist-verification
tooling was offered as a lighter alternative and has been declined as well, so this means none of it -
not drawing generation and not verification. `docs/hardware/project_schematic_package/` is deliberately
static, hand-captured design input. The user's words and the full list of what was removed: `bugfixes.md`.
- Generated simulator CSVs belong in `_build/My_Pic_Project/sim/csv/` and graphs in `_build/My_Pic_Project/sim/graphs/`.
- WHERE A FACT LIVES (so this file does not drift, and so nothing is written twice):
  *the general standing rules* - the ones that apply to every task here (never write "Hmm", terse
  output, never judge a run from the terminal, every run through the watchdog, commit-and-push often,
  delete logs once read, record every durable finding, PIC18F47Q10 only) - live in
  **`.github/copilot-instructions.md`**, which VS Code injects into EVERY request automatically. That
  file is deliberately short: each of its lines costs on every query, so it carries rules and pointers
  only, never detail. **Nothing loads THIS file automatically** - there is no hook or instruction that
  opens `Ai-Notes.md`, so a session only reads it because these notes say to (or because the user
  says so). That is exactly why the rules that must never be missed are no longer only here.
- THREE NAMES, SHORT (2026-09-24, user request: *"just name each skill (with a short name) so I know
  what they do"*): skill **`build-test`**, skill **`editor-clangd`**, agent **`build-runner`**. The
  folder (skills) or filename (agents) IS the name - a skill file must be exactly `SKILL.md`, so its
  name can only live in the folder. A skill `name:` that does not match its folder fails SILENTLY, with
  no error anywhere; an agent with no `name:` takes its filename.
- DOC HYGIENE (2026-09-24). Canonical build directories: `_build/My_Pic_Project/release` is what the
  editor reads, `_build/My_Pic_Project/sim` is where the tests run. The `q10_*` trees and the two Q10
  VS Code tasks are GONE - the Q10 is the default device, so it needs no build tree of its own.
  **Rule: never restate a rule in two files unless one is a pointer** - the copies drift, and whichever
  a session reads first wins, which is how `TESTING.md` came to outrank `user.cmake`.
  **Where a fact lives:** *state and user instructions* (what the firmware does now, what is in flight,
  what is left, the rules above) live
  in THIS file; *build/test/debug procedure* (toolchain paths, configure/build commands, the flash
  budget, mdb and harness techniques, test names and labels, failure triage) lives only in
  `.github/skills/build-test/SKILL.md`, with `.github/agents/build-runner.agent.md`
  as the thin runner that must stay in sync with it and TESTING.md as the human-facing guide;
  *editor/toolchain problems* (VS Code's Problems panel, clangd, the C/C++ extension,
  `compile_commands.json`, `-mdfp=`/`-mcpu=` complaints, XC8 device headers or missing family macros)
  live only in `.github/skills/editor-clangd/SKILL.md`, with the forensic detail in
  its `references/xc8-headers.md`. That is a SEPARATE skill on purpose: neither its rules nor its
  traps can affect a build or a test - XC8 is invoked directly and needs none of it - and keeping it
  out of the build/test skill makes that skill cheaper to read on every build and test task. The
  build/test skill keeps only a one-line pointer to it, and vice versa;
  *design detail* lives in `docs/` (e.g. docs/first-dit-band-detection.md); *defects and their fixes*
  in `bugfixes.md`; *historical/origin narrative* only in `prototype_reference/`. Never restate a
  command here - link to the skill.

## Date
2026-09-25

## Session handoff (carry-over for a NEW session)
- This is the ONLY AI carry-over file. `AI-HANDOFF.md` was deleted on 2026-09-21 (it duplicated
  project-architecture.md, the pin map and TESTING.md, and had drifted), and
  `docs/next-session-prompt.md` was retired to a tombstone on 2026-09-23 and has since been deleted
  (it still told a new session to work on the now-deleted `upgrade/pic18f47q10` branch and to chase a
  Q10 temperature trip that had long since been fixed). Do not recreate a second handoff file - update
  this one.
- Working tree should be clean; read the current commit with `git --no-pager log --oneline -1`
  rather than trusting a SHA written here.
- **The project now runs on Windows 10 as well as macOS** (MPLAB X 6.35 / XC8 4.00 / Python 3.14.7).
  MDB is ~2.4x slower on Windows: the merged suite is ~356 s there against ~150 s on macOS. All
  platform-specific harness code lives in `tools/simulate/platform_process.py`. Build/test procedure,
  the Windows gotchas and the timeout policy are in the skill - do not restate them here.
- **The log tab opens on every run - a REQUIREMENT (2026-09-26), and it may be the current tab.**
  The one thing forbidden is snatching focus: `code -r` makes the log the ACTIVE tab AND raises VS Code
  over whatever the operator is doing (it damaged a run on 2026-09-25). `tools/simshow/` is the small
  in-repo VS Code helper that opens the log with the API's `preserveFocus` (tab appears, focus stays),
  driven by a request file that `open_progress_log.py` writes; install once (`tools/simshow/install.ps1`)
  and reload the window. `LOG_TO_WATCH <path>` in the run log names the file. The helper needs an
  ABSOLUTE path - a relative `--log` produced a broken URI and the tab silently never opened
  (fixed 2026-09-26 in `open_progress_log.py`). See the skill's "How a run is watched".
- **Every suite scenario can be run on its own through the suite's own code path:**
  `run_suite_with_watchdog.py --test suite --only FREQ_CTR` (~40 s) or `--only base,SWR1`. The full
  suite is the verdict, never the debugging instrument.
- **A failed scenario's trace carries prose and the panel:** `scope_trace.py` writes
  `_build/My_Pic_Project/sim/graphs/<scenario>_scope.png` with the ms timebase across the top, lanes
  picked from the data, what the test was for / what the firmware did / the assertion as text, the
  injected counter stimulus drawn over the frequency lane, and a reconstructed 16x2 LCD panel of the
  state at failure. Render it offline from `suite_raw_mdb.log` rather than re-running the suite.
- **`80m TX injection lock not exercised` - FIXED 2026-09-25, and it was the harness, not the
  firmware**: `hold_band()` wrote all five Timer1 counts at the START of each 5 ms sample step, so
  they landed ahead of that chunk's first 10 ms gate and every later gate read the firmware's own
  TMR1 reset. Injecting once per simulated millisecond INSIDE the step fixes it and `--only FREQ_CTR
  --bands 80m` now passes; the general trap and the method are in the build-test skill.
- **A TX self-test is implemented (2026-09-25, DONE - live position in
  `docs/tx-self-test-plan.md`, design in `docs/tx-sequencer.md` §9)**: while keyed, on the 10 ms
  counter gate (never the 1 ms path - that starved the trip chain and broke SWR1), the firmware checks
  PTT, the running stage, that stage's outputs (via `SENSE_*`) and the measurement behind the band
  lock, ORs every check that has held for 200 ms into `g_selftest_reason` (bit flags). The remedy is
  split by cause (user instruction, 2026-09-25): a FATAL check (BAD_BAND, TX_SENSE, STALLED,
  REL_STUCK) latches the undefined/unkeyable state until the operator keys again, while a recoverable
  check (NO_RF, LOCK_LOST, BAND_CHG, NO_LOCK, NO_BAND) folds back (open the RF path, re-select from
  the next valid measurement, key once more). The panel reads `FAULT:` plus the `+`-joined reason,
  never a PWR/SWR page. The HARNESS asserts that verdict instead of any keyed `frequency_khz` reading.
- Last verified run: Windows **2026-09-25, the full 14-scenario suite GREEN (`TEST_END code=0`, 310 s)**
  with the keyed self-test, the unkey check, the 1 ms lean release sampling and the end-of-log
  `RUN PASSED` block all in. `--only <scenario>` or `--only FREQ_CTR --bands <band>` (40-80 s) is the
  iteration tool; the full suite is the verdict. Earlier session history - `platform_process.py`,
  timeouts, the 16F strip, the
  device spike, **the SWR1 re-arm failure (FIXED 2026-09-25: the harness held PTT released for 50 ms
  against a measured 54 ms firmware poll latency, so the release edge was never seen; the window is
  now 200 ms)** - is in `bugfixes.md` 2026-09-22..24 and the skill. Not restated here.

## Simulator timing limitation (IMPORTANT)
- The simulator is a debugger model, not silicon: it validates state ordering, LCD lifecycle, trip
  latching and recovery, but exact hardware timing needs the bench.
- **Timer1's external clock (T1CKI) is not modelled and MDB's SCL `stim` is not usable in this build**,
  so the frequency counter cannot be proven end-to-end in simulation - the harness injects
  `TMR1H`/`TMR1L` instead, which covers the maths, band classification, band-select outputs and TX lock
  but not the pin, the PPS routing, the prescaler or the overflow path. Do not try to clock the pin.
  Traps and the re-tests: `.github/skills/build-test/SKILL.md` and `TESTING.md`.
- **Injecting the count: write `TMR1H` FIRST, then `TMR1L`.** `RD16` is set, so a `TMR1H` write is
  buffered until `TMR1L` is written; the old L-then-H order dropped the high byte and truncated the
  count (14000 kHz / `0x88B8` read back as `0x00B8` = 73 kHz), which is the real cause of the "20m
  never classified" blocker, not injection aliasing. Proved with
  `tools/simulate/repro_first_dit_20m.py`.

## Current design
This repository is the active PIC18F47Q10-I/P linear-amplifier protection controller. Obsolete prototype source files have been removed so they cannot enter the production build.

## Firmware
- **The keyed TX self-test is implemented**: what it checks, the 200 ms hold, the reason mask and the
  action are in docs/tx-sequencer.md §9; the plan and its live position are in
  docs/tx-self-test-plan.md. The panel shows `FAULT:` plus the `+`-joined reason; fatal checks
  (BAD_BAND, TX_SENSE, STALLED, REL_STUCK) latch, recoverable checks fold back and re-key.
- **First-dit band switching is implemented.** The model, its guards and its bench unknowns are in
  docs/first-dit-band-detection.md; the firmware API is freq_counter_restore_locked_band(),
  freq_counter_band_confirmed() and freq_counter_measured_band(). Bench-confirm BAND_SETTLE_MS (20 ms),
  BAND_VERIFY_MS (20 ms) and BAND_CACHE_IDLE_TIMEOUT_MS (60 s); measured fold-back latency in the
  simulator is 23 ms.
- **Two relay groups in the RF path, and the order they switch in:** `OUTPUT_TX` (RC5, the T/R relay,
  called `RELAYS` by the harness) and `K1-K6` (RD2-RD7, the LPF band relays). The band relays settle
  before the T/R relay closes, which is why first-dit bypass exists; the LPF filters are on the TX
  train only, so the rig never sees a band relay move while the T/R relay is open. Detail:
  docs/first-dit-band-detection.md.
- **The relay selection no longer follows silence.** `freq_counter_tick_10ms()` drives the band
  outputs only for a usable measurement; it used to follow the classifier's 160m no-signal default,
  which parked the relays on 160m after every over and made almost every warm re-key move them.
- **The SWR trips are armed only while the TX path is engaged** (`g_sequence_stage` 1-3, the stages
  that hold `OUTPUT_TX` asserted). They used to be evaluated unconditionally, so a bridge reading
  during bypass (relay open, band selection possibly moving) could latch a spurious STATE_TRIP
  during the very first dit. Hardware overcurrent, current, temperature, overdrive and drain trips
  remain ungated. The gate is applied once inside `update_protection_state()` for flash reasons.
- **Flash, measured 2026-09-24 on Release: 11214/131072 bytes (8.6%) - nothing is tight.** The
  "effectively full" claim that used to sit here was a PIC16F18875 property (8192 words). One durable
  coupling survives: the LCD menu labels are hard-coded in `tools/simulate/render_lcd_lifecycle_diagram.py`'s
  `SETTINGS_PANELS`, so shortening or renaming a label means updating that script too.
- **The remembered band is verified, not trusted (fold-back):** a first-dit engage from the band memory
  is re-checked against the first usable measurement of that transmission, and a mismatch for
  BAND_VERIFY_MS forces bypass first, re-selects cold, then re-engages. Where it matters and why:
  docs/first-dit-band-detection.md.
- Direct ADC inputs monitor two forward/reflected SWR pairs, temperature, WCS1700 current, input power, and drain voltage. Which channel is which lives ONLY in docs/hardware/PIC18F47Q10_pin_map_and_setup.md - never restate that list here.
- ADC configuration (firmware/src/main.c adc_init): 10-bit, right-justified legacy format, VDD-referenced with the internal FVR off. Raw values are consumed directly as plain 0-1023 counts, so at a 5 V rail one count is about 4.88 mV.
- Current-sensor scaling (firmware/src/main.c): zero at raw 512 (2.5 V mid-rail), +511 counts = +70 A, 0 counts = -70 A. The default positive current trip is 40 A (g_thresholds initialiser).
- On PTT release the sequencer unwinds in order - TX off immediately, TX_VCC after the VCC delay, then TX_BIAS - and the band is released only once every TX output is confirmed inactive (release_band_if_cold()). An engage still in progress when PTT releases is therefore unwound, not completed; the old "engages complete, then unsequence" description is obsolete (see bugfixes.md 2026-09-21).
- SWR trips, power scales, drain/input thresholds, 10 kOhm NTC B-value profile, sequencer timing, and output polarities are user-configurable from the 1602 LCD menu.
- Outputs are written through the `LAT` registers and inputs are read from `PORT`
  (`.github/instructions/firmware.instructions.md`). `pin_map.h` holds the write macros; the three TX
  outputs also carry `SENSE_TX*`
  pin-level read macros, used by the two checks that must confirm the hardware actually reached a
  state (`release_band_if_cold()`, and the PTT COMPLETE condition) instead of trusting the latch.
  Do not reintroduce `PORTxbits` writes for outputs: on PORTC the relay lines share a port with the
  LCD data lines, so a port read-modify-write can clobber a relay latch from an unrelated write.
- Hardware comparators combine at INPUT_HARD_FAULT for independent overdrive, drain-peak, and overcurrent protection.
- The sequencer runs TX, TX_VCC, and TX_BIAS with two configurable inter-stage delays, defaulting to 20 ms.
- The LCD is a 1602 driven in 4-bit parallel mode by firmware/src/lcd_parallel.c, with its interface header at firmware/include/lcd_parallel.h (renamed from lcd_i2c.h on 2026-09-22 - a prototype-era name that kept misleading readers; there is no I2C backpack and no I2C code). Internal EEPROM access lives in firmware/src/nvm.c + firmware/include/nvm.h, which drives the Q10 NVM block directly (NVMCON0/NVMCON1, with the 0x55/0xAA unlock into NVMCON2) - there is no 16F guard and no legacy eeprom helper left. Pin assignments: see the single-source-of-truth rule above.
- Menu settings and the last display page are stored in the PIC's internal EEPROM in a versioned, checksummed record; no external EEPROM module is used.

## Display
- The default home page is the PEP/temperature display.
- The STATUS page shows post-filter forward power as PEP or RMS, two-decimal SWR, and a full-width `|`/`.` bar.
- The PEP/temperature and current-meter pages use EEPROM-saved peak hold/decay settings: factory defaults are 1.2 s hold and 100 ms smooth decay interval.

## Simulation
**Method, traps, commands and timeout policy for the simulator live in
`.github/skills/build-test/SKILL.md`** - see its `## Simulation method` and
`## Timeout and platform policy` sections. Those cover the mdb command set, `run_sim.sh`/`.ps1`, the
`.sym`-address fault injection, the idle-ADC stimulus recipe, `ANSELC`, `W0106-SIM`, the GUI debug
session, the shared-ELF/rebuild trap, the `platform_process.py` ownership rule and the timeout budgets.

## References
- Hardware source of truth: docs/hardware/PIC18F47Q10_pin_map_and_setup.md
- Architecture and safety behaviour: docs/project-architecture.md
- Band-change detection (first-dit model, implemented): docs/first-dit-band-detection.md
- Firmware entry point: firmware/src/main.c
- Bug fixes log (update whenever a real bug is found): bugfixes.md

## CI / release
- .github/workflows/firmware-build.yml builds on every push/PR to main on `ubuntu-latest` (installs XC8 v4.00 + the `PIC18F-Q_DFP` pack, Ninja) and packages `.hex`/`.elf`/`.map`/`.xml` plus the pin map (docs/hardware/PIC18F47Q10_pin_map_and_setup.md) into a `firmware-<sha>` artifact. It compiles only - the simulator tests are not run in CI.
- .github/workflows/auto-release.yml runs after a successful main build, auto-increments a `v0.0.N` tag, and publishes that artifact as a GitHub Release. This is fully automatic - no manual step needed for a normal push to main.
- .github/workflows/release-firmware.yml is the manual fallback (workflow_dispatch) to re-publish an older build's artifact under an existing tag.

## Device memory usage
**Current figures are in the skill's `## Flash space`.** Flattened here: on the Q10 nothing is tight.
Measure them, never quote them from memory:
- Measured 2026-09-24, Release: program **11214/131072 bytes used (8.6%)**, data **368/3359 bytes
  (11.0%)**. The PIC16F18875 map that used to be quoted here (8117/8192 words) was a property of the
  old part, and "FLASH IS EFFECTIVELY FULL" was true only of that part.
- `memoryfile.xml` (and `mem.map`) is regenerated by XC8 on every build and is always included in the
  latest release, so it always reflects the current firmware, not a stale snapshot.
- To check the current figures: read `<memory name="program">`/`<memory name="data">`
  `used`/`free`/`length` from the build directory's `memoryfile.xml`, or from the latest release
  (`gh release download <tag> -p memoryfile.xml`).

## Remaining work

### REMINDER: the MCU speed / oscillator question (flagged 2026-09-24, user asked to be reminded)

Two "instruction rate" figures in this repo disagree by ~10x and neither has been re-measured against
the ELF the tests actually load. `tools/simulate/probe_q10_ptt_path.py` sets `BOOT_STEPS = 16_500_000`
for the firmware's 1000 ms gate, derived from "Q10 at 64 MHz = 16 MIPS, so 1000 ms needs ~16,000,000
steps"; the direct probe of that same 1000 ms boundary put it at ~1.5-1.75M steps, i.e. ~1625 per
firmware-ms. Related: the two harnesses disagree by 16% (`test_first_dit.py` uses 1887, the others
1625), and 1887 is documented as measured in `ff931f7`. The clock chain itself is settled and must not
be re-litigated without evidence: core `RSTOSC = HFINTOSC_64MHZ`, Timer2 on `T2CLK = Fosc/8` with
`PR2 = 124` giving the 1.000 ms tick, and `_XTAL_FREQ = 64000000UL` in `pin_map.h` matching the core.
The open question is what MDB's `Stepi` actually counts - one instruction or something else - and
therefore which constant is right. One measurement settles it; do not "fix" it by picking the tidier
number. Detail: the skill's instruction-rate block and `bugfixes.md` 2026-09-23/24.

**MEASURED 2026-09-24: ~1695 steps per firmware millisecond** (531 Timer2-interrupt ticks per
900,000 `Stepi` steps, from the firmware's own tick counter; probe and table in
`docs/hardware/q10-bringup/tick_rate_probe.mdb` / its README). So 1625 is ~4% low, 1887 is ~11% high,
and `BOOT_STEPS = 16_500_000` in `probe_q10_ptt_path.py` is ~10x too large (the 1000 ms boundary is
at ~1.70M steps). **But forcing every harness to 1695 broke the merged suite's SWR1 scenario** - the
sample windows are phase-tuned per harness, and a single global rate is only an approximation - so
the harnesses keep their validated constants (1625 / 1887) and 1695 stands as the tighter
*measurement*, not the run value. Re-read the open first-dit clause (c) failure against 1887, the
rate that harness actually uses.

**And there is no single "sim MHz": the model ignores the oscillator configuration outright.**
After 300,000 steps `OSCCON1`/`OSCFRQ`/`OSCCON3` all read 0 - it does not apply `RSTOSC =
HFINTOSC_64MHZ` - and forcing `OSCFRQ = 0x07` by hand changes nothing measurable. MDB's own `Stopwatch`
(1000 cycles = 1 ms -> a 4 MHz-equivalent base) shows the core delivering ~847 instructions per
simulated ms, while the firmware's 1 ms tick arrives every 2.0 simulated ms (as if the timers were
clocked from 32 MHz). Core and peripherals disagree by ~8x and both sit an order of magnitude below
the real 64 MHz / 16 MIPS, so simulator steps must be converted with the measured 1695/firmware-ms,
never with datasheet clock arithmetic. Evidence: `docs/hardware/q10-bringup/clock_check_probe.mdb`.

**And it cannot be fixed: the clock-only image agrees.** `clock_only_probe.c` (config words, the
`timer0_init()` Timer2 setup, one ISR, a bare `while (1) {}` - no LCD/ADC/NVM/printing) with the
oscillator programmed in code (`OSCCON1 = 0x60`, `OSCFRQ = 0x07`) gives **exactly 1000 `Stepi` steps
per tick** and **1997 model cycles = 2.0 model-ms per tick**, the same ~1990 as the full firmware. The
model ignores the clock configuration and clocks Timer2 2x slow, so no setting makes it run at 64 MHz;
measure peripheral-free when a rate is wanted.

**The actual lever is MPLAB X's Simulator > Oscillator Options > Instruction Frequency (Fcyc),** set to
64 MHz - the simulator ignores config bits/oscillator registers and times from that project property.
Scripted `mdb.sh` runs have no project, so the harnesses can't use it and stay on the measured 1695
steps per firmware-ms; a 64 MHz simulation needs an MPLAB X project (or the VS Code MPLAB Simulate
session) with Fcyc = 64 MHz.

None of this affects test validity: the firmware's time base is the Timer2 tick and every harness
assertion is tick-relative, so the model's absolute speed only changes the step count per firmware-ms
(1695), which the harnesses already use.

**FIXED 2026-09-24: `_XTAL_FREQ` was 32 MHz against the real 64 MHz core.** `__delay_us()`/
`__delay_ms()` are computed by XC8 from `_XTAL_FREQ`, and this firmware uses them for real work: the
LCD init sequence (50/5/2/1 ms), the page-clear settle, and the ADC acquisition delay - so a 32 MHz
constant against a 64 MHz core made every one of those about half as long as its name claims.
`firmware/include/pin_map.h` now defines `_XTAL_FREQ 64000000UL`, matching `RSTOSC = HFINTOSC_64MHZ`.
This changes only the firmware's compiled delay loops, not the harness `Stepi` constants (1625/1887,
measured 1695), which stay unsettled until the operator picks one. Timer2's Fosc/8 chain is untouched.

**And a second firmware clock item, found while clearing up the device docs (2026-09-24): the ADC
clock divider is never set.** On the Q10's ADCC the divider is `ADCLKbits.ADCS` (6 bits off Fosc), and
`adc_init()` never writes `ADCLK`, so the ADC runs at that register's reset default. The Q10's `ADCON1`
has no clock field at all (`ADDSEN`/`ADGPOL`/`ADIPEN`/`ADPPOL`), so `ADCON1 = 0x20` there is a
guard-ring polarity bit, not `ADCS`. Any TAD claim must be read from the datasheet's `ADCLK` reset value
and confirmed against the module minimum; `docs/hardware/bench-validation.md` no longer quotes one.

### Open items carried out of the relay-ordering work (2026-09-22)

Both are OPEN. Each states what "done" means, so a later session can close it rather than
re-derive it.

1. **Prove clause (h) on its own.** Clause (h) checks that the LPF relay selection HOLDS through RX
   instead of following the 160m no-signal default. Re-introducing that defect does fail the test, but
   it fails *earlier*, at `clause (c): the remembered 20m band was not restored`, because one phase of
   the single MDB session feeds the next - so clause (h)'s own proof is outstanding. To close it, make
   the injection narrower: give clause (h) its own session, or restructure the phases so (a)-(c) do not
   depend on the selection surviving the previous release. Either way record the observed failure
   message in the defect table in docs/first-dit-band-detection.md.
2. **Bench-confirm the relay timings and the Timer1 path.** The 20 ms relay assumption is what both
   `BAND_SETTLE_MS` and `tx_vcc_delay_ms` rest on, and invariant I6 asserts only a 10 ms floor
   (deliberately below 20 ms and above the 1-6 ms a defect produces) at 1-5 ms sampling, so the margin
   is thin: measure the fitted K1-K6 and T/R relay operate times and confirm or adjust both constants.
   Separately the simulator does NOT model Timer1's external clock (`W0106-SIM`), so T1CKI, the PPS
   routing, the 1:4 prescaler and the overflow path are untested - the first burst is injected by
   writing `TMR1H`/`TMR1L`. That gap closes on the bench only.

### General

The open work is hardware validation: final sensor calibration, comparator thresholds and polarity, ADC transient protection, TX timing, fan implementation, LCD/menu/internal EEPROM persistence testing, final PCB review, and CI validation. First-dit specifics to confirm on the bench: BAND_CACHE_IDLE_TIMEOUT_MS (60 s) against real band-change habits, BAND_SETTLE_MS (20 ms) against the fitted LPF relay's operate time, and BAND_VERIFY_MS (20 ms) - i.e. how long a wrong remembered band may stay engaged before fold-back, which is the one figure that trades amplifier protection against nuisance drop-outs on a noisy first dit.

- **DONE (2026-09-26): a firmware-only diagnostic self-test** - the `SELF TEST` live menu page runs,
  only while cold, an assert-and-verify loop over every output (`SENSE_*` read-back), the 0->1->2->3->0
  sequencer walk, an LCD pattern and an EEPROM round-trip, and reports PASS or the `+`-joined failed
  check names on the LCD. `--test suite --only SELF_TEST_DIAG` passes (verdict `0x08` = EEPROM, the one
  check the simulator cannot model; outputs/sequencer/LCD green, amplifier cold). Design and the one
  open criterion (a fault-injection scenario to prove a stuck output fails the check) are in
  `docs/firmware-self-test-diagnostic.md`.

If the simulator image is ever compiled `-Os` instead of `-O1` it would reclaim space, but it degrades
mdb symbol/breakpoint resolution for the VS Code "Simulate PicAmpControl (Debug)" session - that needs
explicit user consent. If space ever does bind, the cheapest room is the LCD string literals
(`STRCODE`), and commented inline assembly where a hot path justifies it (every block needs an
equivalent-C comment).
