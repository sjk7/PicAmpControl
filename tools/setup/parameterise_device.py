#!/usr/bin/env python3
"""Parameterise the device tokens in the generated rule.cmake.

Run from the repo root: python tools/setup/parameterise_device.py

Why edit a generated file
-------------------------
`cmake/My_Pic_Project/default/.generated/rule.cmake` hardcodes `-mcpu=16F18875`,
`__16F18875__` and the `PIC16F1xxxx_DFP` pack path in the compile, assemble and link rules. That
was fine with one device, but it meant the PIC18F47Q10 image could only be produced by hand-written
`xc8-cc` commands, so `ctest` and every harness (which load `out/My_Pic_Project/default.elf`) could
never exercise it. A second copy of the generated tree would drift from this one, and a drift
between "what the tests load" and "what the build produces" is the exact failure being removed.

So the device facts move to `cmake/My_Pic_Project/default/device.cmake`, and this script rewrites
the device tokens in rule.cmake to use them. It is idempotent: running it twice changes nothing.

Do NOT paste this into a shell as a one-liner - `${PICAMP_MCPU}` is expanded by the shell before
Python ever sees it, which silently produced `-mcpu=` and an unreadable include path once already
(2026-09-22).
"""
import re
import sys
from pathlib import Path

RULE = Path("cmake/My_Pic_Project/default/.generated/rule.cmake")
DEVICE_CMAKE = "../device.cmake"

HEADER = """# DEVICE SELECTION (hand-edited by tools/setup/parameterise_device.py, 2026-09-22).
# The device tokens below are CMake variables from device.cmake, so this one tree builds either
# the PIC16F18875 or the PIC18F47Q10 image. See device.cmake for why a generated file is edited
# here, and for the flash/RAM asymmetry between the two parts.
include("${CMAKE_CURRENT_LIST_DIR}/devicemarker")

"""


def main() -> int:
    if not RULE.exists():
        sys.exit(f"error: {RULE} not found - run this from the repository root")
    source = RULE.read_text(encoding="utf-8")

    # Drop a previously-inserted header so the script is idempotent.
    source = re.sub(r'^# DEVICE SELECTION.*?include\("\$\{CMAKE_CURRENT_LIST_DIR\}[^"]*"\)\n\n',
                    "", source, flags=re.S)

    original = source
    source = source.replace('"-mcpu=16F18875"', '"-mcpu=${PICAMP_MCPU}"')
    source = source.replace('"-mcpu=18F47Q10"', '"-mcpu=${PICAMP_MCPU}"')
    source = source.replace("${PACK_REPO_PATH}/Microchip/PIC16F1xxxx_DFP/1.32.471/xc8",
                            "${PICAMP_DFP_PATH}")
    source = source.replace("${PACK_REPO_PATH}/Microchip/PIC18F-Q_DFP/1.30.487/xc8",
                            "${PICAMP_DFP_PATH}")
    source = source.replace("${PACK_REPO_PATH}/Microchip/${PICAMP_DFP}/xc8",
                            "${PICAMP_DFP_PATH}")
    source = source.replace('PRIVATE "__16F18875__"', 'PRIVATE "${PICAMP_DEFINE}"')
    source = source.replace('PRIVATE "__18F47Q10__"', 'PRIVATE "${PICAMP_DEFINE}"')

    header = HEADER.replace("devicemarker", DEVICE_CMAKE)
    source = header + source
    RULE.write_text(source, encoding="utf-8")

    leftover = len(re.findall(r"16F18875|18F47Q10|PIC16F1xxxx_DFP|PIC18F-Q_DFP|PACK_REPO_PATH/Microchip",
                             source))
    print(f"rule.cmake: rewritten (changed={original != source}), "
          f"hardcoded device tokens left={leftover}")
    print(f"  PICAMP_MCPU uses     = {source.count('${PICAMP_MCPU}')}")
    print(f"  PICAMP_DFP_PATH uses = {source.count('${PICAMP_DFP_PATH}')}")
    print(f"  PICAMP_DEFINE uses   = {source.count('${PICAMP_DEFINE}')}")
    return 0 if leftover == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
