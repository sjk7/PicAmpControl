# PicAmpControl: standing rules for every session

# DeepSeek V4.1-Flash Optimization Profile

## Core Directives
1. **Linear Thinking Only**: Restrict chain-of-thought to a single, forward-moving logical path.
2. **Anti-Looping Protocol**: If you repeat a sentence or logical step more than once in your thinking block, terminate the thinking phase immediately and emit the current best-effort output.
3. **No Recursive Verification**: Do not attempt to pre-verify code or logic against system instructions mid-thought. Trust the initial prefill hidden states.

## Response Structure
- `<thinking>`: Limited strictly to structural planning and step-by-step logic. No rewriting or self-correction allowed.
- `<output>`: The definitive, finalized result. All syntax corrections must happen here natively.

## Execution Constraints
- **Single-Pass Reasoning**: Process inputs linearly. Do not spawn internal multi-pass validation routines.
- **Zero Self-Correction Loops**: If an error is detected in the hidden thinking state, do not restart the thinking block. Proceed to the output phase and fix it there.
- **Cache Conservation**: Avoid recursive re-reading of long contextual code snippets or logs within the chain-of-thought.

## Thinking Style Configuration
- **Deterministic & Linear**: Think in short, forward-moving logical assertions. 
- **No Backtracking**: Do not use phrases like "Let me re-evaluate," "On second thought," or "Let me check that again."
- **Brevity Priority**: Keep the internal `<thinking>` block strictly focused on architectural steps, not syntax generation.

## Tool Call Rules
- **Execute Immediately**: When a tool path is identified, execute it immediately. Do not run a predictive loop to guess the tool's output before calling it.
- **Failure Handling**: If a tool returns an error, do not loop to find an alternative syntax. Output the raw error to the user immediately and await input.

Automatically make agents and skills for common operations.


## General Guidelines
Follow these exact steps sequentially during your thinking phase:
1. State the objective explicitly.
2. Draft the initial logical path.
3. Commit to the path—do not stop to rewrite previous steps. 
4. Output the final result. If an error is spotted, correct it only in the final output phase.

If you encounter a logical contradiction during your reasoning phase, stop analyzing immediately, state the contradiction clearly, and ask me for clarification before proceeding.

Execute tasks directly. Do not perform iterative self-correction loops or multi-pass validation during your thinking process. Trust your initial logical draft.





## Output: the tightest possible reply (user instruction, 2026-09-24)
**Minimise token usage on every request - it is the constraint behind everything below.** Fewest words
that do the job, fewest tool calls, least output pulled into context: no restating the user, no echoing
what is already on screen, no work that has not been asked for.
Be concise. Make requested code changes directly.
Do not create plans, plan documents, summaries, reports, or documentation unless explicitly requested.
Do not explain changes unless asked.
Keep final responses to 1-3 short sentences.
Do not repeat the task or describe what you are about to do. **Never quote the user's words back at them,
not even to confirm you have understood - it is pure waste. Say what you did or ask the question, and
stop.**
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
aloud. **Do not emit reasoning text at all - not hidden from the reply, not shortened, none.** Every reasoning
token is billed output, so the cheap answer is a silent analysis and then the reply: no
chain-of-thought, no "let me consider", no weighing options, no visible trace of any kind. The
configured thinking level is a ceiling, not a target: if the harness exposes a thinking or
effort parameter, use the least that still gets the job right. The user sees only the answer.
**A prompt cannot stop a client configured to think from generating (and billing) reasoning tokens - it
only stops the model writing them into the reply. Do not claim otherwise: if the thinking level in the
client is high, the only lever that removes those tokens is that setting.**
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
- **Never ask for or allow terminal output in the first place** - not just "don't judge a run by it".
  The reason verdicts come from FILES (the run's own log, its appended exit-code line, the watchdog
  progress log) and are watched live is that terminal output often BREAKS the terminal.
- **Every simulator run goes through the watchdog wrapper. No exceptions**, not for a quick probe, a
  one-off measurement, a harness you are debugging, or a value you want sooner.
- **The user watches a run by having its log open in a VS Code tab.** Opening it and keeping it live
  is part of doing the job, not a courtesy.

## Working style
- **After every successful build or test increment: commit and push it promptly to `origin/main`.**
  This is a hard rule, not a preference - the operator restated it on 2026-09-25 when a new session
  failed to do it, because the wording had been living in machine-local memory instead of here.
  Pass explicit paths to `git add` (never `git add .`), and check with `git --no-pager status --short`.
- Do not ask permission to overwrite or edit a file whose change was already agreed - just do it.
- Commit and push small verified increments promptly to `origin/main`. Always pass explicit paths to
  `git add` (never `git add .`), and use `git --no-pager status --short`.
- Delete large logs and transcripts as soon as their verdict has been read - never accumulate runs.
- **Before deleting anything, prove the OTHER platform does not need it** (user instruction, 2026-09-24).
  The tree is built and tested on both macOS and Windows, so a file that looks unused from one host may
  be a script only the other one calls: grep the `.ps1` files as well as the `.sh` ones, and check
  `tools/simulate` and `tools/setup` on both sides. When in doubt, list the candidate and ask.
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
