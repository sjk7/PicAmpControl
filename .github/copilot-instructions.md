# PicAmpControl: standing rules for every session

These apply to ALL work in this repo, which is why they live here (always loaded) rather than in a
skill (loaded on demand). Detail, method and traps live in the skills named at the bottom - do not
restate them here, because this file is injected into every request and every line costs.

## Read first
- **STEP ONE, EVERY SESSION, BEFORE ANY OTHER ACTION: read `Ai-Notes.txt` at the repo root.** It
  carries the target device, current design/firmware/display state, remaining work and the user's
  standing instructions. **Nothing loads it automatically** - it matches no VS Code convention, so it is
  read only because this line says so. Do not "fix" its name to make it auto-load: at 499 lines it would
  then be injected into every request. Read it, do not restate it.
- Also read `deepseek-pic.md` (bare-metal PIC guardrail checklist - a cross-check, never project state).
- The target is the **PIC18F47Q10, and nothing else**. There is no second device and no legacy part.

## Writing and cost
- **Never write "Hmm"** - not in a reply, not in a reasoning trace, not as a hedge. State the finding,
  or the uncertainty, plainly and move on.
- Be maximally terse. No filler, no step-by-step narration, no restating what was just done, no code
  blocks unless asked. Never paste file contents, logs, tables of raw output or exit-code dumps into
  the chat - put them in a file and report one line plus the path.
- Batch tool calls; filter command output (`-Tail`, `-First`) instead of dumping whole files. The
  terminal panel is rendered too, so a whole-file dump costs CPU as well as tokens.

## Running builds and tests
- **Never judge a run from terminal output, and never ask a running test for its terminal output** -
  that wedges the terminal. Verdicts come from FILES: the run's own log, its appended exit-code line,
  and the watchdog progress log.
- **Every simulator run goes through the watchdog wrapper. No exceptions**, not for a quick probe, a
  one-off measurement, a harness you are debugging, or a value you want sooner.
- **The user watches a run by having its log open in a VS Code tab.** Opening it and keeping it live
  is part of doing the job, not a courtesy.

## Working style
- Do not ask permission to overwrite or edit a file whose change was already agreed - just do it.
- Commit and push small verified increments promptly to `origin/main`. Always pass explicit paths to
  `git add` (never `git add .`), and use `git --no-pager status --short`.
- Delete large logs and transcripts as soon as their verdict has been read - never accumulate runs.
- Keep `Ai-Notes.txt` up to date at the end of any session that changes design, firmware, docs or
  workflow.
- **Record every durable finding** - a trap that cost time, a method that worked, a measurement that
  replaces a guess, a mistake of mine a reader should not repeat - **in the relevant skill in the same
  session.** A code comment or a commit message is not a finding recorded.

## Where detail lives
- Skill **`build-test`** - building, testing, harnesses, watchdog, verdict method, flash budget:
  `.github/skills/build-test/SKILL.md`
- Skill **`editor-clangd`** - VS Code Problems panel, clangd, C/C++ extension, compile database, XC8
  header/macro resolution: `.github/skills/editor-clangd/SKILL.md`
- Agent **`build-runner`** - thin delegate for builds and tests: `.github/agents/build-runner.agent.md`
- Design detail: `docs/`. Defects and their fixes: `bugfixes.md`. Historical narrative:
  `prototype_reference/` only.
