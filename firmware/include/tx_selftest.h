#ifndef TX_SELFTEST_H
#define TX_SELFTEST_H

#include "state.h"

/* The keyed TX self-test: "is the firmware where the PTT and the sequencer say it should be?".
   See docs/tx-sequencer.md §9 and tx_selftest.c. The verdict mask is tx_selftest_reason_t; the
   panel text is tx_selftest_reason_text(). */

/* Start a new key-down verdict. The ONLY place the reason mask is cleared, so the previous reason
   stays on the panel until the operator keys again. */
void tx_selftest_reset(void);

/* The panel text for a self-test mask: EVERY set bit's name, joined with '+', in bit order.
   Never blank - "OK" for an empty mask, "UNKNOWN" for a code the table does not know. Truncation
   ends with '+'. Returns the columns used. */
unsigned char tx_selftest_reason_text(unsigned int reason, char *buffer, unsigned char size);

/* Evaluate the keyed self-test once per 10 ms counter gate (called beside freq_counter_tick_10ms). */
void tx_selftest_run(void);

#endif
