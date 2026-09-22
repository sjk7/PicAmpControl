#!/usr/bin/env python3
"""Give each device its own output directory, so the tests can never read the wrong image.

Run from the repository root: python tools/setup/parameterise_output_dir.py

Why
---
`.generated/file.cmake` hardcodes the firmware image output to `out/My_Pic_Project/`, i.e.
`default.elf`, `default.sym` and friends. Every simulator harness loads exactly that path:

    ELF_PATH = REPO_ROOT / "out" / "My_Pic_Project" / "default.elf"
    SYM_PATH = REPO_ROOT / "out" / "My_Pic_Project" / "default.sym"

With two devices that is a trap with no symptom. Build Q10, then build the 16F, and the harnesses
happily run the 16F image against the Q10 expectations - or the reverse. The fault injection is
worse still: `test_first_dit.py` writes to variable *addresses* read from `default.sym`, so a stale
symbol file makes it poke the wrong memory. None of that reports an error; it just produces a wrong
verdict.

So the output directory becomes per-device:

    PIC16F18875  -> out/My_Pic_Project_16F18875/
    PIC18F47Q10  -> out/My_Pic_Project_18F47Q10/

and the harnesses resolve the same directory from `PICAMP_DEVICE`, so what the tests load is
necessarily what the selected device built.

This is the same small, commented, device-token-only edit as `parameterise_device.py` applies to
`rule.cmake`, for the same reason: the alternative is a duplicated generated tree that drifts, and
a drift between "what the tests load" and "what the build makes" is the failure being removed.
Idempotent: running it twice changes nothing.
"""
import re
import sys
from pathlib import Path

FILE_CMAKE = Path("cmake/My_Pic_Project/default/.generated/file.cmake")
# The unparameterised form, as generated.
PLAIN = 'set(My_Pic_Project_default_output_dir "${CMAKE_CURRENT_SOURCE_DIR}/../../../out/My_Pic_Project")'
SUFFIXED = ('set(My_Pic_Project_default_output_dir\n'
            '    "${CMAKE_CURRENT_SOURCE_DIR}/../../../out/My_Pic_Project_${PICAMP_MCPU}")')


def main() -> int:
    if not FILE_CMAKE.exists():
        sys.exit(f"error: {FILE_CMAKE} not found - run this from the repository root")
    source = FILE_CMAKE.read_text(encoding="utf-8")
    original = source

    if PLAIN in source:
        source = source.replace(PLAIN, SUFFIXED)
    elif SUFFIXED not in source:
        sys.exit("error: output dir line not recognised; inspect file.cmake before editing")

    FILE_CMAKE.write_text(source, encoding="utf-8")
    print(f"file.cmake: rewritten (changed={original != source})")
    print(f"  per-device output dir present: {SUFFIXED in source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
