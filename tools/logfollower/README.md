# Log Follower

Keeps a **growing log file** scrolled to its tail in an editor tab, and stops immediately when you
take control of that tab.

Built for watching long-running build, test or simulation output that is written to a file.

**This directory is the source of truth, and it is version-controlled on purpose.** The extension
used to live only at `_build/logfollower/`, which `.gitignore` excludes, so every fix to it was
uncommittable and got lost - which is why the same following bugs kept coming back. Edit here, then
repackage:

```powershell
cd tools/logfollower
npx --yes @vscode/vsce package --no-dependencies --allow-missing-repository -o pac-log-follower.vsix
code-insiders --install-extension pac-log-follower.vsix --force   # or: code
# then RESTART the editor - a running extension host keeps the old version loaded
```

## What it does

- **Follows the tail.** As the file grows, the view scrolls to the end, so the tab always shows the
  newest output instead of the run's first three lines. A `FileSystemWatcher` drives the refresh,
  with a poll as the safety net, so an append scrolls straight away rather than up to one interval
  late.
- **Yields to you, instantly - for that session.** Clicking in the text, moving the cursor,
  highlighting/selecting text, wheeling, or dragging the scrollbar all pause the follow. The pause
  lasts only for the current run: when the producer truncates the file for a new run, following
  re-arms automatically (and so does reopening the tab). Within a single run the resume is
  *deliberate* - the toggle command - so the view is never yanked out from under you while you read.
- **Stays cheap.** Following costs one file stat per interval plus one reveal per actual growth
  (plus watcher events). Paused, it costs nothing.

## Commands

| Command | Effect |
|---|---|
| `Log Follower: Toggle auto-scroll for this file` | Start following, or stop; also resumes after a pause |
| `Log Follower: Start auto-scroll for this file` | Follow the active file |
| `Log Follower: Stop auto-scroll for this file` | Stop following the active file |

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `logFollower.autoFollowGlobs` | `["*.log", "*progress.log", "*.out"]` | File-name patterns (simple `*` wildcards) followed automatically when opened, e.g. `*.log`. Matching is on the file name only, so no machine-specific path is ever needed. |
| `logFollower.coalesceMs` | `400` | Poll interval in milliseconds (400 = 2.5 checks/second). Each check is one file stat; only an actual size change costs a revert plus a scroll, so this interval is the floor of the follow's cost. Raise it to reduce cost further. Changing it needs a window reload - the interval is created once at activation. |

## Notes on the cost

A follow costs one `stat()` per poll interval (2.5 per second at the 400 ms default) plus, only when
the file actually grew, one revert and one cursor placement plus `revealRange()`. The optional
per-file watcher adds an append-triggered refresh on top, so a burst is not limited to the poll rate -
but it is still one scroll per distinct growth event, and it is disposed the moment you stop
following. While paused, or while the followed tab is not the visible one, there is nothing to pay:
the poll stats a file nobody is looking at and stops there.

## Licence

MIT.
