# Setup helpers

Machine setup, not build steps. Scripts here are safe to re-run.

- **`parameterise_device.py`** - rewrites the device tokens in the generated MPLAB X files. It still
  pattern-matches the 16F tokens on purpose: those are the *generator's* tokens, not our target.
- **`parameterise_output_dir.py`** - rewrites the output directory tokens in the same generated files.
- **`windows-defender-exclusions.ps1`** - excludes the build and MDB working directories from Defender
  scans, which otherwise slow simulator runs substantially.
