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
- **Yields to you, instantly.** Clicking in the text, moving the cursor, selecting, wheeling,
  dragging the scrollbar, or switching to another tab all pause the follow. Resume is *deliberate*
  (the toggle command) - it never re-arms itself behind your back.
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
| `logFollower.autoFollowGlobs` | `[]` | File-name patterns (simple `*` wildcards) followed automatically when opened, e.g. `*.log`. Matching is on the file name only, so no machine-specific path is ever needed. |
| `logFollower.coalesceMs` | `60` | Scroll coalescing window in milliseconds. Writes inside one window produce one scroll, which caps cost regardless of write rate. Raise it to reduce cost further. |

## Notes on the cost

A follow is one cursor placement plus one `revealRange()` per coalesced burst. With the default
60 ms window, a producer writing thousands of lines a second still costs at most ~17 scrolls a
second, and typically far fewer. There is no interval timer anywhere in the extension, so an idle
follow costs nothing.

## Licence

MIT.
