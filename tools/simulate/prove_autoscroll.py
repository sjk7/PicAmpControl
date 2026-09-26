#!/usr/bin/env python3
"""Prove the simshow log-follow: open a log in VS Code, then append a line every half-second
so the operator can watch it follow the tail (and scroll up to stop, down to resume)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "simulate"))
import open_progress_log  # noqa: E402

log = Path(__file__).resolve().parents[2] / "_build" / "My_Pic_Project" / "sim" / "autoscroll_test.log"
log.parent.mkdir(parents=True, exist_ok=True)
log.write_text("autoscroll proof - line 0\n", encoding="utf-8")

# Open it through the focus-inert helper (tags the request with this window's main PID).
opened = open_progress_log.open_in_editor([str(log)], quiet=False)
print(f"open requested: {opened}")

for i in range(1, 40):
    with log.open("a", encoding="utf-8") as f:
        f.write(f"autoscroll proof - line {i}\n")
    time.sleep(0.5)

receipt = open_progress_log.RECEIPT_FILE
print(f"receipt: {receipt.read_text(encoding='utf-8') if receipt.exists() else '(none)'}")
print("done - watch the tab; scroll up mid-run to confirm it stops, back down to resume")
