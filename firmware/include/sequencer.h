#ifndef SEQUENCER_H
#define SEQUENCER_H

#include <stdbool.h>

/* The TX sequencer: the PTT transition handler and the per-millisecond sequence advance. */

/* Handle a PTT edge (asserted = key down, deasserted = key up). Runs the first-dit band-memory
   decision and the bypass-snoop entry/exit. */
void handle_ptt_transition(bool ptt_asserted);

/* Advance the TX engage/release state machine by one millisecond tick. */
void update_tx_sequence(void);

#endif
