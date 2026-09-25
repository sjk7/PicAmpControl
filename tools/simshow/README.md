# PicAmpControl show-log helper (never takes focus)

A tiny VS Code extension that puts a running simulator test's log in front of the operator
**without ever moving their focus, activating its tab, or raising the window**.

## Why it exists

A long simulator run has to be watchable while it runs. Every *external* way of showing the log
moves the focus:

| Mechanism | What actually happens |
|---|---|
| `code -r <log>` | the log becomes the **active editor tab**, so the operator's next keystrokes land in the log (this damaged a run on 2026-09-25), and the window is un-minimised |
| `code -r` + restoring the window focus | too late - the active tab has already moved |
| Log Viewer extension | follows the file in its own webview (no focus change) but it is a separate panel the operator must point at the file |

The VS Code **API** has the one flag the CLI lacks: `preserveFocus`. This extension does the showing
from inside the editor, prompted by a plain request file, so no external process ever asks VS Code to
activate anything.

## How it works

1. The harness writes `%TEMP%\picampcontrol_show.request.json` (`$TMPDIR/...` on macOS) containing
   `{"path": "<log>"}`. `tools/simulate/open_progress_log.py` does this on Windows.
2. This extension notices the file, opens the log in a **non-active editor group** with
   `preserveFocus: true`, then puts the operator's original document and group back exactly as they
   were.
3. It writes `picampcontrol_show.done.json` so the outcome can be confirmed without guessing.

If the request file never appears, the extension does nothing at all.

## Install (one command)

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File tools/simshow/install.ps1
```

macOS / Linux:

```sh
sh tools/simshow/install.sh
```

The script copies the extension into your VS Code extensions directory and prints the one manual
step it cannot do for you: **reload the VS Code window once** (Ctrl/Cmd+Shift+P →
*Developer: Reload Window*), so the editor loads it. After that it is automatic on every run.

Test it by hand at any time:

```sh
python tools/simulate/open_progress_log.py <some-log-file>
```

## Notes

- It never writes to the log it shows.
- It is independent of `tools/logfollower` (deleted 2026-09-24 for stealing focus) and of
  `berublan.vscode-log-viewer`; either can coexist with it.
- macOS does not need it (`open -g` already opens without activation), but installing it is harmless.
