#!/usr/bin/env python3
"""Show a log in the running VS Code so a human can watch a long run - without ever touching
that human's focus, active tab or window.

User instruction (2026-09-22, restated after it was missed twice): **a log the user is
expected to watch must be open in their editor for the whole operation.** Writing a useful
progress file is not enough - a file nobody can see is the same as no log at all.

User instruction (2026-09-25, after a `code -r` put the log in the active tab and the operator's
keystrokes went into it and wrecked a run): **show the tab, never give it focus.** The CLI cannot
be asked for that, so on Windows the showing is done from INSIDE the editor by the small extension
in `tools/simshow/` (installed with `tools/simshow/install.ps1`), which uses the API's
`preserveFocus`. This module's job on Windows is therefore to drop the request file that extension
watches; the extension opens the log in a NON-active editor group and restores the operator's
document and group afterwards. On macOS `open -g` already does the right thing natively.

Usage:
    python tools/simulate/open_progress_log.py <log-path> [more log paths...]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CANDIDATES = ("code-insiders", "code")
WINDOWS_FALLBACKS = (
    r"%LOCALAPPDATA%\Programs\Microsoft VS Code Insiders\bin\code-insiders.cmd",
    r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd",
)
# Matches `tempfile.gettempdir()` here and `os.tmpdir()` in tools/simshow/extension.js, so the
# extension and this module agree on the handshake file without either being told a path.
REQUEST_FILE = Path(tempfile.gettempdir()) / "picampcontrol_show.request.json"
RECEIPT_FILE = Path(tempfile.gettempdir()) / "picampcontrol_show.done.json"
SHOW_EXTENSION = "picampcontrol-simshow"


def resolve_cli() -> tuple:
    """`(path, how)` for the first available editor CLI, or `(None, reason)`."""
    for name in CANDIDATES:
        found = shutil.which(name)
        if found:
            return found, name
    for raw in WINDOWS_FALLBACKS:
        candidate = Path(os.path.expandvars(raw))
        if candidate.exists():
            return str(candidate), candidate.name
    return None, "neither code-insiders nor code is on PATH"


def show_extension_installed() -> bool:
    """True if `tools/simshow` has been installed for Insiders or stable on this machine."""
    for folder in (".vscode-insiders", ".vscode"):
        root = Path.home() / folder / "extensions"
        try:
            if any(child.name.startswith(SHOW_EXTENSION) for child in root.iterdir()):
                return True
        except OSError:
            continue
    return False


def request_show(paths, quiet: bool = False) -> bool:
    """Ask the editor-side helper (tools/simshow) to show `paths`, focus untouched.

    Signals the request through a file rather than the CLI: nothing outside the editor then asks
    VS Code to raise a window or activate a tab, which is the only way to guarantee the operator's
    typing stays where it was. The helper writes a receipt (`picampcontrol_show.done.json`) so a
    caller - or a human - can confirm it acted.
    """
    targets = [str(Path(p)) for p in paths]
    # Tag the request with the workspace root so the RIGHT window opens it. Every Insiders
    # window loads tools/simshow and every one watches the SAME request file, so an untagged
    # request is a race: whichever window's watcher fires first opens the log (2026-09-26 it
    # opened in a second, unrelated window - "MusicPlayer" - while the operator watched the
    # PicAmpControl window). The extension ignores a request whose root it does not own.
    root = Path(__file__).resolve().parents[2]
    try:
        REQUEST_FILE.write_text(
            json.dumps({"path": targets[-1], "paths": targets, "root": str(root)}),
            encoding="utf-8")
    except OSError as exc:
        if not quiet:
            print(f"open_progress_log: could not write {REQUEST_FILE}: {exc}")
        return False
    if not show_extension_installed():
        if not quiet:
            print("open_progress_log: log shown only if the PicAmpControl show helper is installed "
                  "- run tools/simshow/install.ps1, then reload the VS Code window once.\n  Watching: "
                  + targets[-1])
        return False
    return True


def open_in_editor(paths, quiet: bool = False) -> bool:
    """Show a path in the running editor. ON by default, and focus-inert by construction.

    History, because this has been got wrong repeatedly. Every attempt that OPENED something moved
    the operator's focus in the end - `code -r`, restoring the window focus, an in-editor helper,
    reusing an existing group - so opening was briefly made opt-in and the operator then asked the
    obvious question (*"I should be seeing the log in VSCODE. why am i not seeing it?"*). The
    resolution is the helper in `tools/simshow/`, which now cannot move the focus: it opens with
    `preserveFocus`, never re-shows the operator's document, never creates a group (no split), and
    does nothing at all when the file is already on screen. That is why showing is the default
    again; `PICAMP_SHOW_FILES=0` turns it off.

    macOS uses `open -g` (no activation); Windows drops the request file the helper watches.
    """
    if os.environ.get("PICAMP_SHOW_FILES") == "0":
        if not quiet:
            print("open_progress_log: not opening (PICAMP_SHOW_FILES=0):\n  "
                  + "\n  ".join(str(Path(p)) for p in paths))
        return False
    cli, how = resolve_cli()
    # Resolve to absolute: the simshow helper turns the path into a vscode.Uri, and a relative
    # path resolves against the extension's working directory, not the workspace root - so a
    # `--log _build/...` handed to the watchdog produced a broken `file:///_build/...` URI and the
    # tab never opened (2026-09-26). Absolute here, for macOS `open -g` and Windows alike.
    targets = [str(Path(p).resolve()) for p in paths]
    if sys.platform == "darwin":
        if cli is None:
            if not quiet:
                print(f"open_progress_log: {how}; open the log manually to watch the run")
            return False
        app = ("Visual Studio Code - Insiders"
               if how and "insiders" in how else "Visual Studio Code")
        ok = True
        for target in targets:
            try:
                subprocess.run(["open", "-g", "-a", app, target], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30)
            except (OSError, subprocess.SubprocessError) as exc:
                if not quiet:
                    print(f"open_progress_log: open -g -a '{app}' failed: {exc}")
                ok = False
        if ok and not quiet:
            print(f"open_progress_log: opened {len(targets)} log(s) in {app} (background)")
        return ok
    return request_show(targets, quiet=quiet)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[0])
        print("usage: open_progress_log.py <log-path> [more...]")
        return 2
    ok = open_in_editor(sys.argv[1:])
    if RECEIPT_FILE.exists():
        try:
            print(f"open_progress_log: helper receipt: {RECEIPT_FILE.read_text(encoding='utf-8')}")
        except OSError:
            pass
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
