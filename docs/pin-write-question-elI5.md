THE PIN-WRITE QUESTION, EXPLAINED SIMPLY
========================================
Date: 2026-09-22
Branch: upgrade/pic18f47q10
Status: NOT an outstanding problem - resolved. Read the CONCLUSION at the end if you are in a hurry.


WHAT THIS FILE IS
-----------------
A plain-English explanation of one worry that came up while testing the new PIC18F47Q10 chip:
"when the test pretends to press the PTT button, does the chip actually notice?"

It includes the setup, the exact commands, the numbers, the answer, and the two mistakes made
along the way. It is written to be read cold by someone who was not in the session.


THE SETUP - WHAT THE HARDWARE IS
--------------------------------
The controller board has:

  * A PIC18F47Q10 microcontroller (the "new chip" being trialled; it replaces a PIC16F18875).
  * A PTT line - the wire from the radio that says "I am transmitting now".
  * Band relays - switches that choose which low-pass filter is in circuit, one per amateur band.
  * TX / TX_VCC / TX_BIAS lines - the lines that actually key the amplifier.

The relevant pin assignments (from firmware/include/pin_map.h):

  RC0   INPUT_PTT              the PTT wire from the radio. ACTIVE LOW, which means:
                               * 1 (high) = button NOT pressed
                               * 0 (low)  = button PRESSED
                               Pull-up enabled (WPUC0 = 1) so that, with nothing connected,
                               the pin sits at 1 and reads "not pressed".
  RD1   INPUT_FREQ_COUNTER     the RF sample used to count frequency and work out the band.
  RD2-RD7                      the band relay outputs (160m, 80m, 40m, 20m, 15m, 10m).
  RC5/RC6/RC7                  TX / TX_VCC / TX_BIAS - the amplifier keying lines.


THE SETUP - WHAT THE TEST IS
----------------------------
The firmware is never run on real hardware during development. It is run inside a *simulator*
(MPLAB's "mdb" - Microchip's Debugger). The simulator lets a test script:

  1. load the compiled firmware into a pretend chip,
  2. run it a chosen number of instruction steps,
  3. read any variable or pin to see what the firmware is doing,
  4. type commands to fake inputs, e.g. "pretend someone pulled pin RC0 low".

Step 4 is the interesting one. It is how the test fakes a button press.

The commands look like this (this is a real example, from the boot test):

    device PIC18F47Q10          <- which chip to simulate
    hwtool sim                  <- use the simulator, not a real programmer
    program <path>\default.elf  <- load the firmware
    Stepi 200000                <- run 200,000 instruction steps
    print PORTC                 <- show me the state of port C (a number)
    print pin RC0               <- show me pin RC0 specifically
    write pin RC0 low           <- FAKE: pretend the button is pressed
    Stepi 20000                 <- run some more
    print PORTC                 <- did it change?
    write pin RC0 high          <- fake: release the button
    Stepi 20000
    print PORTC                 <- did it go back?


THE WORRY
---------
When the Q10 firmware was run through the full test suite, it reported:

    0 keyed runs out of 552 samples

Meaning: in the whole test, the amplifier never once keyed. Not once. The firmware was asked to
transmit and it never did.

That is a plausible-sounding chip problem, and there was a precedent: an earlier attempt to swap
in a different chip (the PIC16F18877) failed with the *exact same signature* - "the firmware never
sees PTT asserted" - and that attempt was abandoned.

So the worry was:

    Is the firmware genuinely broken on the new chip?
    OR
    Is our test simply failing to press the pretend button, and blaming the chip for it?

Those two look identical from the outside. Both produce "0 keyed runs". This is the single most
dangerous kind of test result: a test that cannot tell "the thing is broken" from "my test is
broken" is not evidence of anything.

There was a specific reason to suspect the test. Pins on these chips have MODES:

  * digital mode   - reads 0 or 1, like a light switch
  * analogue mode  - reads a small voltage, for sensors

If a pin is in analogue mode, "pull it low" may be quietly ignored. And worse - the simulator
ACCEPTS the command and prints nothing. It does not say "I ignored that". So a failed fake button
press is completely silent.

There was already one suspicious sighting: in the boot test, `write pin RA6 high` was echoed in
the output as if it had worked, yet reading RA6 back said it was still in analogue mode.


HOW WE SETTLED IT - THE "POSITIVE CONTROL"
------------------------------------------
A positive control means: instead of testing the thing you care about, test the *method* first,
using a case where you already know the right answer. If the method cannot even get the easy case
right, the method is broken - not the thing you were testing.

The control used here was as simple as possible:

    read what the chip sees on port C
    fake-press the button  (write pin RC0 low)
    read again
    release the button
    read again

Expected if the method works: the value should change on press, and change back on release.

The actual result, run on the PIC18F47Q10:

    PORTC = 229   pin = HIGH    (idle - button not pressed)
    PORTC = 228   pin = LOW     (pressed)
    PORTC = 229   pin = HIGH    (released)

229 -> 228 -> 229.

Port C is a number where each bit is one pin. RC0 is the *least significant* bit, which is worth
the value 1:

    229 in binary = 1110 0101
    228 in binary = 1110 0100
                    ^
                    the rightmost bit changed from 1 to 0

So pressing changed exactly one bit - the right one - and releasing put it back. The fake button
press REACHES the firmware. The method works.


THE ANSWER
----------
Because the fake button press demonstrably works on this chip, the "0 keyed runs" result is a
GENUINE firmware finding. It is not a test artefact. The firmware really does fail to key on the
PIC18F47Q10.

So the pin-write question is CLOSED. There is no outstanding pin-write problem.

The real problem turned out to be somewhere completely different, and finding it is the next
section.


WHAT THE FAILURE ACTUALLY WAS
-----------------------------
Having established that the test was trustworthy, a staged probe walked the PTT path one step at
a time - because "no keying" could have failed at any of several points:

    stage 1: has the chip finished its startup wait?
    stage 2: with the button released, does the firmware agree it is released?
    stage 3: press the button - does the firmware latch it?
    stage 4: if latched, does it enter "bypass snoop" and look for the band?

The answer was stage 1:

    g_startup_inhibit = true    (still in its startup wait)
    g_state           = 5       (STATE_RESET_WAIT - waiting, not operating)

...and it was STILL in that state after 800,000 instruction steps.

The firmware has a startup wait of 1000 milliseconds. After power-up it refuses to act on the PTT
button for one second, to let the hardware settle. That wait is counted by adding 1 to a counter
each time round the main loop, and stopping at 1000.

It never reached 1000. So the firmware sat in its startup wait forever, and PTT could never latch -
not because PTT was broken, but because the firmware was never ready to look at it.

Note carefully: "0 keyed runs" was a SYMPTOM. PTT handling was fine. The cause was upstream, in the
startup timer never advancing. Chasing the visible symptom (PTT) would have wasted a lot of time.


TWO MISTAKES MADE ALONG THE WAY - RECORDED SO THEY DO NOT REPEAT
-----------------------------------------------------------------
Mistake 1: the positive control initially reported the OPPOSITE of the truth.

  The first version of the control checked bit 1 of port C instead of bit 0.
  Bit 0 is worth 1 (RC0 - the pin we pressed).
  Bit 1 is worth 2 (RC1 - a different pin).
  229 and 228 have the same bit 1, so the check saw "no change" and announced that the stimulus
  was broken.

  A perfectly good result was reported as a failure, because of an off-by-one in a bit index. The
  lesson is uncomfortable but important: a positive control that has not been sanity-checked is
  WORSE than no control at all, because it manufactures confidence in the wrong direction. Always
  confirm which bit/mask you are testing against the pin you actually drove.

Mistake 2: a command the simulator accepts is not a command that took effect.

  `write pin RA6 high` appeared in the transcript as though applied, and did nothing. One cause is
  placement - before `program`, the chip is not programmed yet so the write goes nowhere. A second
  suspected cause is that RA6 is a special pin (it doubles as the clock-output pin CLKOUT/OSC2).
  That second one is NOT proven and remains an open question.

  The consequence for tests: any test whose entire purpose is to prove a bad outcome (a "sad path")
  must ASSERT that its stimulus actually applied, and fail loudly if it did not. The first version
  of the boot sad-path test did not do this, and reported a PASS while exercising nothing at all.
  That is the worst possible test result, because it is worse than a failure - it is a false pass.


CONCLUSION
----------
  * The pin-write method WORKS on the PIC18F47Q10. Proven: PORTC 229 -> 228 -> 229 on RC0.
  * The "0 keyed runs" result is a REAL firmware finding, not a test artefact.
  * The real fault is that the startup-inhibit timer of 1000 ms never expires, so the firmware
    stays in STATE_RESET_WAIT and is never willing to act on PTT.
  * The safety invariants all PASS on the new chip (no band change while keyed, keying only with a
    locked band, bypass-snooping keeps the outputs inactive, every band change seen with the
    amplifier cold). Nothing is unsafe; the amplifier simply never engages.
  * NOT an outstanding pin-write problem. The outstanding problem is the startup inhibit.
  * One open question remains: whether RA6 needs special handling (CLKOUT/OSC2), unproven.


WHERE THE EVIDENCE LIVES
------------------------
  tools/simulate/test_stimulus_positive_control.py       the control test itself
  _build/My_Pic_Project/sim/stimulus_control_report.txt  its result (the 229/228/229 table)
  _build/My_Pic_Project/sim/stimulus_control_mdb.log     the raw simulator transcript
  tools/simulate/probe_q10_ptt_path.py                   the staged probe
  _build/My_Pic_Project/sim/q10_ptt_probe_report.txt     its result (g_startup_inhibit stuck true)
  _build/My_Pic_Project/sim/q10_ptt_probe_mdb.log        the raw simulator transcript
  .github/skills/picampcontrol-build-test/SKILL.md       the durable lessons, under the
                                                         positive-control bullets
