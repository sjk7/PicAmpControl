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
HEX_PATH="$REPO_ROOT/out/My_Pic_Project_18F47Q10/default.hex"
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

# W0106-SIM (TMR1/3/5 clock source), W9602-COMP (DAC as a comparator input) and W0223-ADC (a pin the
# harness holds at 0 V) are benign simulator chatter: each refers to the model or to the stimulus, not
# to this firmware (see the build-test skill); filter them out
# (`|| true` avoids pipefail tripping if grep ever finds no non-matching lines)
"$MDB_SH" "$PREAMBLE" 2>&1 | { grep -Ev 'W0106-SIM|W9602-COMP|W0223-ADC' || true; }
