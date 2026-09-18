# PicAmpControl AI Handoff

## Repository state

- Repository: `PicAmpControl`
- Branch: `main`
- Latest pushed commit: `2884824` (`Synchronize docs diagrams and scenario traces`)
- A user change exists in `.vscode/tasks.json`; do not revert or include it unless explicitly requested.
- After verified changes, build, commit, and push.

## Firmware

- Target: PIC16F18855-I/SP, XC8, 32 MHz HFINTOSC.
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

## Testing and artifacts

- Fast complete suite, one MDB/Java invocation:
  ```powershell
  python tools/simulate/trace_ptt_sequence.py --suite
  ```
- The suite covers baseline sequencing, temperature trip/recovery, SWR1, SWR2, hardware fault, current ramp/trip/re-arm, overdrive, drain, and SWR1 1.5:1 no-trip at 2 kW PEP.
- The suite emits exactly nine scenario CSVs under `_build/My_Pic_Project/sim/csv/` and nine scenario PNGs under `_build/My_Pic_Project/sim/graphs/`.
- CTest default is one test: `PTT_SequencerAndTripSuite`.
- Individual CTest registrations are optional through `-DPICAMP_ENABLE_INDIVIDUAL_SIM_TESTS=ON`.
- Diagram generators:
  ```powershell
  python tools/simulate/render_display_menu_diagram.py
  python tools/simulate/render_lcd_lifecycle_diagram.py
  ```
- Current diagrams:
  - `lcd/display_menu_state_diagram.png`
  - `lcd/lcd_lifecycle_16x2.png`
  - `lcd/lcd_normal_screens_16x2.png`
  - `lcd/lcd_fault_screens_16x2.png`
- Graph event labels are positioned above the waveforms at their event timestamps, using stacked lanes to prevent overlap.

## Documentation

- Main project documentation: `README.md`
- Hardware map: `docs/hardware/PIC16F18855_pin_map.md`
- Display/menu diagram links are in `README.md`.
- Frequency-counter handoff: `docs/frequency-counter-next-steps.md`
- Spare GPIOs: RA4, RA6, RA7, RB6. RB6 is used only as a simulator marker by the Python trace tool.

## Deferred frequency-counter work

- Do not implement yet unless requested.
- Recommended architecture: externally condition the overdrive/RF signal into a clean 0-5 V square wave, route it to a spare GPIO through PPS, and count edges with Timer1 during a Timer2-gated interval.
- Do not count frequency directly from the overdrive ADC; ADC sampling does not preserve zero crossings.
- Hardware conditioning must include attenuation, limiting/comparator hysteresis, clamps, and a safe 0-5 V output.
- See `docs/frequency-counter-next-steps.md`.

## Next-session checklist

1. Read this file and `Ai-Notes.txt`.
2. Check `git --no-pager status --short`.
3. Preserve unrelated `.vscode/tasks.json` changes.
4. Run the single suite before modifying simulator behavior.
5. Keep generated outputs in the existing `sim/csv` and `sim/graphs` directories.
6. Commit and push verified changes promptly.
