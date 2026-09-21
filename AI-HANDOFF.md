# PicAmpControl AI Handoff

## Repository state

- Repository: `PicAmpControl`
- Branch: `main`
- Latest pushed commit: `7041164` (`docs: remove the abandoned EasyEDA/KiCad schematic automation entirely`). This line is a snapshot - run `git --no-pager log --oneline -1` for the real head.
- After verified changes, build, commit, and push.
- `Ai-Notes.txt` is the authoritative launch point for current design, firmware and verification state. This file is a shorter orientation summary; keep the two from contradicting each other.

## Firmware

- Target: PIC16F18875-I/P (40-pin PDIP), XC8, 32 MHz HFINTOSC. The firmware is the source of truth for the target device: `-mcpu=16F18875` in `cmake/My_Pic_Project/default/.generated/rule.cmake`, mirrored in `.clangd`.
- Timer2 drives the approximately 1 ms scheduler tick.
- ADC is 10-bit, right-justified, VDD-referenced, approximately 4.89 mV/count.
- ADC channels:
  - RA0/AN0: SWR1 forward
  - RA1/AN1: SWR1 reflected
  - RA2/AN2: SWR2 forward
  - RA3/AN3: SWR2 reflected
  - RA5/AN5: temperature
  - RB1/AN9: WCS1700 current
  - RB2/AN10: overdrive
  - RB3/AN11: drain
- WCS1700 model: 2.5 V = 0 A; 5 V = +70 A; 0 V = -70 A. Default positive current trip is 40 A.
- Power display supports EEPROM-backed FWD/NET selection. FWD is default; NET subtracts SWR2 reflected power.
- Output sequencing is active-low by default: RELAYS/TX, TX_VCC, TX_BIAS.
- Fault shutdown: TX_VCC inactive immediately; RELAYS and TX_BIAS inactive after 5 ms; non-temperature faults latch until a valid PTT re-arm or long-press clear.
- Temperature trips can recover below threshold plus 5 C hysteresis.
- Sequence requests complete their engage order even if PTT releases early, then unsequence in order.
- LCD boot message: `Booting, please` / `wait.` during startup inhibit, then saved EEPROM home page.
- LCD `PTT_COMPLETE` appears only after all three TX outputs reach active levels, for 500 ms, then restores the saved home page.
- TRIP LCD display always has priority over `PTT_COMPLETE` and home-page restoration.
- Fault LCD screens show measured value versus EEPROM limit for temperature, SWR, current, overdrive, and drain. Extreme SWR1 can show `FLTR?? CHECK LPF`.
- Band selection is first-dit bypass-snoop with a remembered band that is verified against the first usable measurement (fold-back); see `docs/first-dit-band-detection.md`. The amplifier never keys without an established band, and the LPF relays never move while it is keyed.

## Testing and artifacts

- Fast complete suite, one MDB/Java invocation. Use the cleanup-aware launcher and log the output
  to a file: MDB emits megabytes of trace and the verdict line is easily lost.
  ```sh
  python3 tools/simulate/run_suite_with_watchdog.py --timeout 300 > /tmp/pac_suite.log 2>&1
  ```
- The suite covers baseline sequencing, temperature trip/recovery, SWR1, SWR2, hardware fault, current ramp/trip/re-arm, overdrive, drain, SWR1 1.5:1 no-trip at 2 kW PEP, the six-band RX preflight and TX lock, the `FREQ_CTR_FAIL` first-dit case, and the band-selection safety invariants.
- The suite emits one scenario CSV per scenario under `_build/My_Pic_Project/sim/csv/` and matching PNGs under `_build/My_Pic_Project/sim/graphs/` (12 of each as of 2026-09-21).
- CTest registers two tests by default: `PTT_SequencerAndTripSuite` (about 2.5 minutes) and `FirstDit_BandDetectionAndHotSwitchGuards` (about 20 seconds, running `tools/simulate/test_first_dit.py`). They must not run concurrently - each owns MDB.
- Individual CTest registrations are optional through `-DPICAMP_ENABLE_INDIVIDUAL_SIM_TESTS=ON`.
- `tools/simulate/*.sh` (macOS) and `*.ps1` (Windows) both exist; the Python harnesses and ctest are cross-platform.
- Diagram generators:
  ```powershell
  python tools/simulate/render_display_menu_diagram.py
  python tools/simulate/render_lcd_lifecycle_diagram.py
  ```
- Current diagrams:
  - `lcd/display_menu_state_diagram.png`
  - `lcd/lcd_lifecycle_16x2.png`
  - `lcd/lcd_normal_screens_16x2.png`
  - `lcd/settings/lcd_settings_navigation_16x2.png`
  - `lcd/lcd_fault_screens_16x2.png`
- Graph event labels are positioned above the waveforms at their event timestamps, using stacked lanes to prevent overlap.

## Documentation

- Main project documentation: `README.md`
- Hardware map (single source of truth for pin assignments): `docs/hardware/PIC16F18875_pin_map.md`
- Display/menu diagram links are in `README.md`.
- Operator UI is a single EC11-style rotary encoder (A/B/push), all active-low/common-to-ground with pull-ups.
- LPF band selection is one dedicated active-high output per band; the old 74HC4514 decoder and B0-B2 bus are gone. Band lockout freezes the LPF relays for the duration of a TX cycle.

## Next-session checklist

1. Read this file and `Ai-Notes.txt`.
2. Check `git --no-pager status --short`.
3. Do not let build/test output flood the terminal - log it and read the verdict from the file.
4. Run the suite and the first-dit proof through ctest before modifying simulator behavior, and read the verdict from the log file rather than the terminal.
5. Keep generated outputs in the existing `sim/csv` and `sim/graphs` directories.
6. Commit and push verified changes promptly.
