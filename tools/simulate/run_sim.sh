#!/usr/bin/env bash
# Launches the MPLAB X headless simulator (mdb) against our locally-built firmware.
#
# Usage:
#   tools/simulate/run_sim.sh                      # interactive mdb session
#   tools/simulate/run_sim.sh scenarios/foo.mdb     # run a scripted scenario, then exit
#
# Requires MPLAB X IDE (provides mdb.sh) and MPLAB XC8, both installable via:
#   brew install --cask mplabx-ide mplab-xc8
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HEX_PATH="$REPO_ROOT/out/My_Pic_Project/default.hex"
DEVICE="PIC18F47Q10"

MDB_SH="$(ls -d /Applications/microchip/mplabx/*/mplab_platform/bin/mdb.sh 2>/dev/null | sort -V | tail -1 || true)"
if [[ -z "$MDB_SH" ]]; then
    echo "error: mdb.sh not found. Install MPLAB X IDE: brew install --cask mplabx-ide" >&2
    exit 1
fi

"$REPO_ROOT/tools/simulate/build_firmware.sh"

PREAMBLE="$(mktemp /tmp/picampcontrol_sim.XXXXXX.mdb)"
trap 'rm -f "$PREAMBLE"' EXIT

{
    echo "device $DEVICE"
    echo "hwtool sim"
    echo "program $HEX_PATH"
    if [[ $# -ge 1 ]]; then
        cat "$1"
        echo "quit"
    fi
} > "$PREAMBLE"

# W0106-SIM TMR1/3/5 warnings are benign simulator-model noise (see Ai-Notes.txt); filter them out
# (`|| true` avoids pipefail tripping if grep -v ever finds no non-matching lines)
"$MDB_SH" "$PREAMBLE" 2>&1 | { grep -v 'W0106-SIM' || true; }
