#!/usr/bin/env python3
"""Pin-level proof that the parallel LCD driver speaks the HD44780 4-bit protocol.

Why this test exists
--------------------
Every other simulator test watches PTT / relay / ADC pins. Nothing checked the LCD driver, and the
driver's whole contract is on six GPIO pins (RS=RA4, E=RA6, D4=RA7, D5=RC3, D6=RC4, D7=RD0). A
regression here is silent to the rest of the suite - a wrong nibble order, a wrong RS level, a
missing E pulse or a wrong init constant would all pass every existing test and only show up as a
blank or garbled panel on the bench.

So this test drives the driver directly, through a small firmware entry point (`lcd_test_sequence`)
guarded by `PICAMP_LCD_TEST`, and reconstructs the bytes the driver placed on the bus by watching
the E pin: every low->high edge latches the current D4-D7 nibble with the current RS level. The
reconstructed nibble stream is then asserted against the exact bytes the HD44780 init and a known
text/cursor write must produce.

Usage:
    python3 tools/simulate/test_lcd_parallel.py
"""
import os
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent.parent
sys.path.insert(0, str(TOOLS_DIR))
import platform_process as procutil  # noqa: E402
import trace_ptt_sequence as harness  # noqa: E402

ELF_PATH = harness.ELF_PATH
DEVICE = harness.DEVICE
INSTRUCTIONS_PER_MS = harness.INSTRUCTIONS_PER_MS

# LCD pins in the order D4-D7 (bit 0..3 of a nibble), then RS and E.
LCD_D_PINS = ["RA7", "RC3", "RC4", "RD0"]   # D4, D5, D6, D7
LCD_RS_PIN = "RA4"
LCD_E_PIN = "RA6"

# The exact bytes `lcd_init()` must emit (see firmware/src/lcd_parallel.c), split into the pin
# trace they produce:
#   the 4-bit wake-up sends 0x3, 0x3, 0x3, 0x2 as HIGH-NIBBLE ONLY (RS=0, one E pulse each);
#   then 0x28, 0x0C, 0x06, 0x01 as full bytes (two nibbles each, RS=0).
INIT_NIBBLES = [
    (0x3, 0), (0x3, 0), (0x3, 0), (0x2, 0),            # wake-up: high nibble only
    (0x2, 0), (0x8, 0),                                # 0x28 function set
    (0x0, 0), (0xC, 0),                                # 0x0C display on
    (0x0, 0), (0x6, 0),                                # 0x06 entry mode
    (0x0, 0), (0x1, 0),                                # 0x01 clear
]
# Then the test writes: set cursor (0,0) -> 0x80; 'H' 0x48; 'I' 0x49; set cursor (1,3) -> 0xC3.
TEXT_NIBBLES = [
    (0x8, 0), (0x0, 0),                                # lcd_set_cursor(0,0) -> 0x80 command
    (0x4, 1), (0x8, 1),                                # 'H' 0x48 data
    (0x4, 1), (0x9, 1),                                # 'I' 0x49 data
    (0xC, 0), (0x3, 0),                                # lcd_set_cursor(1,3) -> 0xC3 command
]
EXPECTED_NIBBLES = INIT_NIBBLES + TEXT_NIBBLES


def stepi(ms) -> str:
    return f"Stepi {int(round(ms * INSTRUCTIONS_PER_MS))}"


def build_script() -> str:
    """Drive the LCD test sequence and sample the six LCD pins at fine steps.

    Sampling: the driver pulses E for ~1us and then waits 50us, so a sample interval shorter than
    the inter-nibble gap is required to see each E pulse. 4-bit writes are ~150us apart, so a
    20us step catches every pulse without exploding the transcript.
    """
    lines = [
        f"device {DEVICE}",
        "hwtool sim",
        f"program {ELF_PATH}",
    ]
    # In PICAMP_LCD_TEST builds the firmware runs lcd_init() + the known text sequence at boot, so
    # sample from reset at 2 us (short enough to catch the ~1 us E pulse) across init's 50 ms
    # power-on delay plus the sequence.
    samples = 30000
    for _ in range(samples):
        lines.append("print pin " + LCD_RS_PIN)
        lines.append("print pin " + LCD_E_PIN)
        for pin in LCD_D_PINS:
            lines.append("print pin " + pin)
        lines.append(f"Stepi {max(1, int(0.002 * INSTRUCTIONS_PER_MS))}")  # 2 us
        lines.append("print g_lcd_test_done")
    lines.append("quit")
    return "\n".join(lines) + "\n"


def run() -> str:
    return harness.run_mdb(mdb_path=harness.find_mdb(), script=build_script())


def parse_nibbles(text: str):
    """Reconstruct (nibble, rs) pairs from the E-pin low->high edges.

    Uses the harness's own pin-line regex so analogue-capable pins (RA4/RA6/RA7 report a voltage
    and a capability string) are handled the same way the rest of the suite handles them: HIGH, or
    a voltage >= 2.5 V, is a logic 1.
    """
    import re
    pin_re = harness.PRINT_RE
    want = {LCD_RS_PIN: "rs", LCD_E_PIN: "e", LCD_D_PINS[0]: "d0",
            LCD_D_PINS[1]: "d1", LCD_D_PINS[2]: "d2", LCD_D_PINS[3]: "d3"}
    samples = []
    pending = {}
    for raw_line in text.splitlines():
        m = pin_re.match(raw_line.strip())
        if not m or m.group(1) not in want:
            continue
        level = m.group(2)
        volts = m.group(3)
        bit = 1 if level == "HIGH" or (volts is not None and float(volts) >= 2.5) else 0
        pending[want[m.group(1)]] = bit
        if len(pending) == 6:
            samples.append(dict(pending))
            pending = {}
    nibbles = []
    prev_e = 0
    for s in samples:
        if s["e"] == 1 and prev_e == 0:
            nibble = (s["d0"] & 1) | ((s["d1"] & 1) << 1) | ((s["d2"] & 1) << 2) | ((s["d3"] & 1) << 3)
            nibbles.append((nibble, s["rs"]))
        prev_e = s["e"]
    return nibbles


def contains_subsequence(haystack, needle):
    """Index of the first occurrence of `needle` as a contiguous slice of `haystack`, or None."""
    n = len(needle)
    for i in range(len(haystack) - n + 1):
        if haystack[i:i + n] == needle:
            return i
    return None


def main():
    if not ELF_PATH.exists():
        sys.exit(f"error: {ELF_PATH} not found - build firmware first")
    os.environ.setdefault("PICAMP_DEVICE", DEVICE)
    text = run()

    nibbles = parse_nibbles(text)
    if not nibbles:
        print("LCD_TEST FAIL: no E-pin pulses observed on the LCD bus")
        sys.exit(1)

    # The captured stream also carries the boot banner ("Booting") which the firmware emits before
    # the test hook can run, so assert the two known byte sequences appear as contiguous slices
    # rather than requiring an exact whole-stream match.
    init_at = contains_subsequence(nibbles, INIT_NIBBLES)
    text_at = contains_subsequence(nibbles, TEXT_NIBBLES)

    # Report the reconstructed stream as decoded bytes, which is what a human can check.
    print(f"LCD_TEST: captured {len(nibbles)} E-pin nibbles")

    if init_at is None:
        print("LCD_TEST FAIL: lcd_init() wake-up/command nibbles not found in the captured stream")
        print(f"  expected slice: {INIT_NIBBLES}")
        print(f"  captured:       {nibbles[:len(INIT_NIBBLES) + 8]}")
        sys.exit(1)
    if text_at is None:
        print("LCD_TEST FAIL: cursor/text write nibbles not found in the captured stream")
        print(f"  expected slice: {TEXT_NIBBLES}")
        print(f"  captured tail:  {nibbles[-len(TEXT_NIBBLES) - 6:]}")
        sys.exit(1)

    print(f"LCD_TEST PASS: lcd_init() contract verified at nibble {init_at}; "
          f"cursor+text write verified at nibble {text_at}")


if __name__ == "__main__":
    main()
