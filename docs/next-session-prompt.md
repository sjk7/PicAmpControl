# Prompt for the next session

Copy the block below into a new chat session.

```text
PicAmpControl — continue the PIC18F47Q10 upgrade.

FIRST, before anything else:
1. Read .github/skills/picampcontrol-build-test/SKILL.md — it holds the hard rules and the
   Windows/Q10 traps we already paid for.
2. Read Ai-Notes.txt (sticky user rules), deepseek-pic.md and mistakes.md.
3. Never write the word "Hmm" anywhere, including in your reasoning.
4. Output discipline is a hard rule: terse answers, never restate context, never paste file
   contents/logs/raw output tables into the chat, batch tool calls, filter command output
   (-Tail/-First/Select-String). The skill is where durable knowledge goes, not the chat.

Branch: upgrade/pic18f47q10 (HEAD 9215035). Never work on main.
  - 2997d47  nvm.c split out of lcd_parallel.c, lcd_parallel.h rename, Q10 config/interrupt
             guards, docs.
  - a508666  harness: separate-process progress heartbeat, TEST_BEGIN/TEST_END per test,
             cleanup_sim_processes.py pre-flight, tools/setup/windows-defender-exclusions.ps1.
  - 9854809  Defender installer reports ADDED/PRESENT/SKIPPED + SUCCESS/FAILED, auto-closes on
             success, auto-runs from the pre-flight.
  - 1a2b4f6  unelevated Defender check (RTP status + install record; the exclusion list itself
             is admin-only on Windows).
  - 9215035  output discipline as a sticky lever; FileTail conditional, not mandatory.
Both Q10 and harness changes were verified green on the 16F18875 (full suite 100% pass). The Q10
image links clean (12,666 bytes) but has NEVER been run on the simulator.

Work in this order:
A. Run the Q10 firmware under MDB for real: PTT visibility, tick, interrupt dispatch
   (IPEN + IPR4 TMR2IP). Recalibrate INSTRUCTIONS_PER_MS in tools/simulate/test_first_dit.py —
   Q10 measured ~6,100-6,900 instructions/tick vs the 8,000 assumed for the 16F.
B. Settle the comparators: W9602-COMP flags a DAC gap in the overcurrent safety path. Resolve
   before spending more engineering time.
C. Then ADC/ADCC, PPS codes (T1CKIPPS = 0x19 is 16F-specific), and re-derive the pin map from
   the Q10 datasheet.
D. PIC16F18877 rejection is only PROVISIONAL in bugfixes.md — same single-configuration method
   that produced two wrong Q10 verdicts. Re-test with a positive control, deriving its register
   values from the DFP instead of assuming 18875 equivalence.

Before every build or simulator run: python tools/simulate/cleanup_sim_processes.py
It kills leftovers using the launcher's own pattern list and checks Defender (raising the
elevated installer itself only if there is no record of it being applied).

Watching jobs:
  - Never tail in the console. Truncate the log with Clear-Content (never delete a file a watcher
    has open), start the job, have the file open in a VS Code tab.
  - FileTail (~110% of one core to follow a log) is optional and only while a job is running.
    Read on demand instead if it shows that load.
  - Resolve the VS Code CLI (code-insiders, else code); never assume Insiders.
  - Progress log: %TEMP%\picampcontrol_suite_progress.log — appended across both tests,
    TEST_BEGIN/TEST_END per test, heartbeat every 5 s naming the running test.
Verdicts come from the run's own log file plus its appended exit code, never from terminal text.

Pending non-urgent: build the reusable "follow a growing file" skill (sticky TODO in Ai-Notes.txt)
— do it only when there is slack, never mid-task.

Everything must be green on this branch before it goes near main.
```
