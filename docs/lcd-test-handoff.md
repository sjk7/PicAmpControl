# Handoff: the parallel LCD driver test (still open)

**Reviewed 2026-09-24. This file is NOT a session launch point - `Ai-Notes.md` is.** The single
item here that is still live is the LCD blocker below; the "green and pushed" state and the commands
have been superseded, and are marked where they were wrong.

Still open: `firmware/src/lcd_parallel.c` is untested. `tools/simulate/test_lcd_parallel.py` exists and
does not work yet, and no LCD test is registered in `cmake/My_Pic_Project/default/user.cmake`. The
blocker - the Q10 simulator reporting RA4/RA6/RA7 as `Aout` and never as `Dout` - is unresolved.

Original header follows. Date: 2026-09-22; the branch it names, `upgrade/pic18f47q10`, has since been
deleted (it was an ancestor of `main`).

## Where things stand

**Green and pushed:**
- Full Q10 simulator suite passes: `SUITE_EXIT:0`, 11 scenarios. *(The `--timeout 400` quoted here on
  2026-09-22 is stale - the budget is `--timeout 1200`; see `TESTING.md`.)*
- CI (`firmware-build.yml`) builds the PIC18F47Q10 and installs its DFP
  (`PIC18F-Q_DFP/1.30.487`). Verified green on GitHub; Q10 links at 8.6% flash. (The 16F matrix leg
  was removed on 2026-09-23, together with the 16F port itself.)
- FREQ_CTR I5 hot-switch fixed (firmware): see the build/test skill for the root cause and the two
  fixes in `main.c`.

**Not started / open:**
- **LCD parallel driver has no test.** `firmware/src/lcd_parallel.c` drives RS=RA4, E=RA6, D4=RA7,
  D5=RC3, D6=RC4, D7=RD0 and its contract (HD44780 4-bit init + cursor/text) is checked by nothing.
  A work-in-progress pin-level test exists at `tools/simulate/test_lcd_parallel.py` but does NOT
  work yet — see the blocker below.
- Bench validation of the relay-settle constants (`BAND_SETTLE_MS`, `BAND_VERIFY_MS`,
  `BAND_CACHE_IDLE_TIMEOUT_MS = 60 s`) is still pending; source comments say they are guesses.

## The LCD test blocker (read this before retrying)

`test_lcd_parallel.py` decodes the RS/E/D4-D7 waveform by latching D4-D7 on each E falling/rising
edge and reconstructing the nibbles, then asserts the init and text byte sequences.

**Blocker: the Q10 simulator reports RA4/RA6/RA7 as `Aout 0.0V` (analog output), not `Dout HIGH/LOW`,
even when `ANSELA` has their analog bits clear and the firmware drives them as digital outputs.**
So the test never sees an E pulse on RA6, and the RA4/RA7 data bits read as a constant 0.0 V.
RC3/RC4/RD0 *do* report `Dout` correctly, so the driver's low nibble is observable but the high
nibble and E are not.

Things already tried and their outcomes:
- Sampling at 2 us to catch the ~1 us E pulse — insufficient on its own because of the analog-report
  problem above.
- Clearing `ANSELA` bits 6/7 before the sequence — no effect (bits were already clear; the simulator
  still reports Aout).
- Moving the test sequence to run at boot (before any status render) so the trace is deterministic —
  this part is correct and should be kept.
- A firmware hook under `#ifdef PICAMP_LCD_TEST` was added and then **reverted** to keep the
  production firmware clean. Re-add it when the simulator issue is solved.

**Next steps to try, in order:**
1. Check whether the Q10 ADCC `ANSELA`/`ANSEL` semantics differ (the Q10 ADCC may have a separate
   analog-select register or the simulator may key off `ADCON`/`PPS`). Confirm with a minimal
   `write pin RA6 high` + `print pin RA6` probe *without* the firmware, to see if the simulator can
   report RA6 at all.
2. If RA6/RA7 genuinely cannot be observed, either (a) move the two affected LCD signals to
   digital-reporting pins if the hardware allows — check the pin map first, or (b) prove the
   protocol from the low nibble (RC3/RC4/RD0) plus an internal shadow variable the firmware
   maintains, which is weaker but still catches nibble-order and RS bugs.
3. Only then re-add the `#ifdef PICAMP_LCD_TEST` hook (boot-time sequence, digital pins) and make
   the test assert the init + `0x80`/`H`/`I`/`0xC3` nibble stream.

## Stale-ELF trap (cost a full debugging cycle — now in the skill)

The harness loads ONE fixed image, `out/My_Pic_Project_18F47Q10/default.elf`, not the build tree it
was configured in. An edited source under a *different* build dir (e.g. `_build/.../q10_lcdtest`)
does not update that path unless that dir is built, and `cmake --build` can print
`ninja: no work to do` and silently leave a stale image. Always confirm the ELF timestamp is newer
than every source file you changed before running any simulator test. Full rule is in
`.github/skills/build-test/SKILL.md`.

## Quick commands

```powershell
# suite (watchdog-wrapped, like everything else - see the build-test skill)
python tools/simulate/run_suite_with_watchdog.py --timeout 1200

# targeted FREQ_CTR I5 repro (also wrapped: run_mdb_probe.py or --test first-dit)
python tools/simulate/repro_i5_15m_10m.py

# LCD test build (writes the SHARED ELF; rebuild the normal config afterwards)
cmake -S cmake/My_Pic_Project/default -B _build/My_Pic_Project/lcdtest -G Ninja `
  -DCMAKE_BUILD_TYPE=Debug `
  -DCMAKE_TOOLCHAIN_FILE="$PWD/cmake/My_Pic_Project/default/.generated/toolchain.cmake" `
  -DCMAKE_USER_MAKE_RULES_OVERRIDE="$PWD/cmake/My_Pic_Project/default/.generated/overrides.cmake" `
  -DCMAKE_C_FLAGS="-DPICAMP_LCD_TEST=1"
cmake --build _build/My_Pic_Project/lcdtest --verbose
```
