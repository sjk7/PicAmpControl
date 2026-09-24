# Setup helpers

Machine setup, not build steps. Scripts here are safe to re-run.

- **`install_logfollower.sh` / `.ps1`** - build and install the in-repo **Log Follower** VS Code
  extension (`tools/logfollower`) if the version in its `package.json` is not already installed.
  `run_tests.sh` / `run_tests.ps1` call it automatically before a run, so a fresh clone gets the
  follower without a manual step; run it by hand after bumping the extension's version. It is
  idempotent, needs no `npm` and no `vsce`, and writes `pac-log-follower.vsix` (gitignored) beside the
  extension source. Why it exists: the log the user watches during a simulator run is followed by that
  extension, and the VSIX is not committed, so without this a new machine would watch a dead tab.
- **`parameterise_device.py`** - rewrites the device tokens in the generated MPLAB X files. It still
  pattern-matches the 16F tokens on purpose: those are the *generator's* tokens, not our target.
- **`parameterise_output_dir.py`** - rewrites the output directory tokens in the same generated files.
- **`windows-defender-exclusions.ps1`** - excludes the build and MDB working directories from Defender
  scans, which otherwise slow simulator runs substantially.
