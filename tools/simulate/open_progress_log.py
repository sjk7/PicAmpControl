#!/usr/bin/env python3
"""Open a log in the running VS Code so a human can watch a long run.

User instruction (2026-09-22, restated after it was missed twice): **a log the user is
expected to watch must be open in their editor for the whole operation.** Writing a useful
progress file is not enough - a file nobody can see is the same as no log at all. The user
had to say "I want to see logs during long ops in VS Code, Insiders or not. Always."

Insiders is preferred but not assumed: resolve `code-insiders` first, then `code`, and do
nothing quietly if neither exists - the failure mode this replaces was a silent no-op that
looked like a fix.

Usage:
    python tools/simulate/open_progress_log.py <log-path> [more log paths...]
"""
import shutil
import subprocess
import sys
from pathlib import Path

CANDIDATES = ("code-insiders", "code")
WINDOWS_FALLBACKS = (
    r"%LOCALAPPDATA%\Programs\Microsoft VS Code Insiders\bin\code-insiders.cmd",
    r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd",
)


def resolve_cli() -> tuple:
    """`(path, how)` for the first available editor CLI, or `(None, reason)`."""
    for name in CANDIDATES:
        found = shutil.which(name)
        if found:
            return found, name
    import os
    for raw in WINDOWS_FALLBACKS:
        candidate = Path(os.path.expandvars(raw))
        if candidate.exists():
            return str(candidate), candidate.name
    return None, "neither code-insiders nor code is on PATH"


def open_in_editor(paths, quiet: bool = False) -> bool:
    """Reuse the running editor window (`-r`) and open every path. Returns success."""
    cli, how = resolve_cli()
    if cli is None:
        if not quiet:
            print(f"open_progress_log: {how}; open the log manually to watch the run")
        return False
    targets = [str(Path(p)) for p in paths]
    try:
        subprocess.run([cli, "-r", *targets], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        if not quiet:
            print(f"open_progress_log: {how} failed: {exc}")
        return False
    if not quiet:
        print(f"open_progress_log: opened {len(targets)} log(s) via {how}")
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[0])
        print("usage: open_progress_log.py <log-path> [more...]")
        return 2
    return 0 if open_in_editor(sys.argv[1:]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
