# RETIRED - do not use this file

**This file is a tombstone (2026-09-23). It was out of date and its instructions were wrong:** it
told a new session to work on branch `upgrade/pic18f47q10` (that branch is an *ancestor* of `main`
and has been deleted) and to hunt a Q10 temperature-trip bug that was fixed, verified and merged
long before this file was read again.

The AI carry-over is `Ai-Notes.txt` at the repo root - read that first, then
`.github/skills/picampcontrol-build-test/SKILL.md`. Do not recreate a second handoff file: an
earlier duplicate (`AI-HANDOFF.md`) was deleted for exactly this reason.

The historical text below is kept only so that the stale instructions are recognisable if they are
quoted back at a future session. Nothing below is current.

---

# Prompt for the next session (RETIRED - historical text follows)

Copy the block below into a new chat session.

```text
PicAmpControl — continue the PIC18F47Q10 upgrade.

FIRST, before anything else:
1. Read .github/skills/picampcontrol-build-test/SKILL.md — hard rules + Windows/Q10/ADCC traps.
2. Read Ai-Notes.txt (sticky user rules), deepseek-pic.md and mistakes.md.
3. Never write "Hmm" anywhere, including reasoning.
4. Be maximally token-efficient at all times; stream long-op output to a VS Code tab (heartbeat),
   never run long tasks silently. The user has complained repeatedly (and again in this session)
   that long tasks (suite, probe, build) run with no visible output in VS Code. Opening the log in
   a VS Code tab and streaming a heartbeat to it is part of doing the job, not a courtesy. Use
   tools/simulate/open_progress_log.py and the AppendLog heartbeat from
   tools/simulate/platform_process.py; never just redirect to a temp file and report the tail.

Branch: upgrade/pic18f47q10. Never work on main.

## The one problem left
On the Q10 the amplifier TRIPS as soon as PTT asserts: g_state=STATE_TRIP(3), g_fault_latched=true.
g_trip_reason = 0x10 = TEMPERATURE only. g_live_temperature_c = 150 (max sentinel) with the temp
pin driven to 2.5V (should be ~25-30C). current/overdrive/drain all read 0 correctly.

## Already ruled out (do NOT re-chase)
- Floating pins: probe now drives all ADC pins to safe values; trip persists.
- ADFM justification alone: adc_init() sets ADCON0bits.ADFM=1 under #if defined(__18F47Q10__)
  (working tree, UNCOMMITTED). ELF rebuilt (14:50 > main.c 14:40) and temp STILL reads 150C.
- ADREF: no ADREF write exists and none should be added (reset = VDD/VSS).

## Leading hypothesis (untested)
The Q10 ADCC result is NOT necessarily 10-bit. If it runs 12-bit (or wider), 2.5V = ~2048 raw,
and temperature_c() does raw>>=2 -> 512 > 250 -> returns 150. Matches exactly; 0V channels stay 0.

## Next concrete step
Extend tools/simulate/probe_q10_ptt_path.py to also `print` ADCON0/1/2/3 (result width/mode,
esp. ADCON2 ADMD + ADCRS resolution bits), ADRES (raw), ADPCH (channel). Confirm whether 2.5V
yields ~512 (10-bit) or ~2048 (12-bit). Then set the ADCC to 10-bit right-justified (or shift the
result) and re-run.

Rebuild (cmake --build alone can fail the regenerate — run the full configure first):
  cmake -S cmake/My_Pic_Project/default -B _build/My_Pic_Project/q10_release -G Ninja \
    -DPICAMP_DEVICE=PIC18F47Q10 -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_TOOLCHAIN_FILE=$PWD/cmake/My_Pic_Project/default/.generated/toolchain.cmake \
    -DCMAKE_USER_MAKE_RULES_OVERRIDE=$PWD/cmake/My_Pic_Project/default/.generated/overrides.cmake \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
  cmake --build _build/My_Pic_Project/q10_release --verbose -j4
Probe: $env:PICAMP_DEVICE="PIC18F47Q10"; python tools/simulate/probe_q10_ptt_path.py
(report _build/My_Pic_Project/sim/q10_ptt_probe_report.txt).

## Probe parse bug
`print pin RAx` emits a TABLE ("Pin Mode Value Owner or Mapping" header + row), so the probe's
pin_re (requires line to end in V) drops all ADC pin reads. Fix the regex or drop pin reads and
rely on the g_live_* globals.

## Working tree (UNCOMMITTED — decide what to keep)
- firmware/src/main.c — ADFM=1 fix.
- tools/simulate/probe_q10_ptt_path.py — pin setup + trip decode + live/threshold reads.
- .github/skills/picampcontrol-build-test/SKILL.md — ADCC register map + six mistakes +
  token-efficiency rule.
- DELETED (working tree shows D): docs/pin-write-question-ELI5.txt,
  docs/remaining-blocker-ELI5.txt, q10_trip_resolution.txt. Confirm intentional before committing.

Before every build/sim run: python tools/simulate/cleanup_sim_processes.py
Verdicts come from the run's own log file + appended exit code, never terminal text.
Everything must be green on this branch before it goes near main.
```
