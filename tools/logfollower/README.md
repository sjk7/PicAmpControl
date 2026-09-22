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
  newest output instead of the run's first three lines.
- **Yields to you, instantly.** Click in the tab, move the cursor, or scroll up, and following
  pauses. Scroll back to the bottom and it resumes. Nothing fights you for the scroll position.
- **Stays cheap.** There are no timers and no polling. Scrolls happen only on file-change events and
  are coalesced, so the cost does not grow with how fast the file is written. Idle, it costs
  nothing.

## Commands

| Command | Effect |
|---|---|
| `Log Follower: Toggle auto-scroll for this file` | Start or stop following the active file |
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
