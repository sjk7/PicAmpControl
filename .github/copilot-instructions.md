# PicAmpControl: standing rules for every session

## Output: the tightest possible reply (user instruction, 2026-09-24)
**Minimise token usage on every request - it is the constraint behind everything below.** Fewest words
that do the job, fewest tool calls, least output pulled into context: no restating the user, no echoing
what is already on screen, no work that has not been asked for.
Be concise. Make requested code changes directly.
Do not create plans, plan documents, summaries, reports, or documentation unless explicitly requested.
Do not explain changes unless asked.
Keep final responses to 1-3 short sentences.
Do not repeat the task or describe what you are about to do.
This holds after long or multi-file tasks too: no review write-ups, no tables of findings, no "what I
did" sections, no closing offers of further work. Findings belong in a file or a skill; the reply is
still 1-3 sentences. Breaking these rules has been the most repeated failure in this repo - the rules
were already loaded and were ignored, so treat the limit as a hard ceiling, not a target.
A todo list is allowed, but ask the operator for permission first.
**Before sending anything: count the sentences. More than three, or any heading, table or bullet list,
means rewrite it. This applies to answers too, not just to reports of changes.**
**While working: no narration at all** - nothing before, between or after tool calls: no "now I'll",
no "one more thing", no progress commentary, no reason-for-this-call. Tool calls and the terminal are
rendered as well, so each such line costs what a reply costs. Work silently, speak once, at the end.
**Narration is billed as output tokens like any other text, so every narrated line is money spent for
nothing: do not write one.**
This binds your reasoning traces: one clause per step, never a paragraph, and never weighing options
aloud.
The one exception to "no documentation": if a skill was in use and one of its instructions or
assumptions turned out wrong, fix that skill in the same piece of work, so the same wrong assumption
cannot be made again.

## Read first
- **STEP ONE, EVERY SESSION, BEFORE ANY OTHER ACTION: read `Ai-Notes.md` at the repo root.** It
  carries the target device, current design/firmware/display state, remaining work and the user's
  standing instructions. **Nothing loads it automatically** - it matches no VS Code convention, so it is
  read only because this line says so. Do not "fix" its name to make it auto-load: injecting it into
  every request is exactly what it is kept out of. Read it, do not restate it.

## Writing and cost
- **Never write "Hmm"** - not in a reply, not in a reasoning trace, not as a hedge. State the finding,
  or the uncertainty, plainly and move on.
- Never paste file contents, logs, tables of raw output or exit-code dumps into the chat - put them in
  a file and report one line plus the path. No code blocks unless asked.
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
- Keep `Ai-Notes.md` up to date at the end of any session that changes design, firmware, docs or
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
