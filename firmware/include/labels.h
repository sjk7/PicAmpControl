#ifndef LABELS_H
#define LABELS_H

#include "state.h"

/* Human-readable name tables for the state enums, and their accessors. Each name is kept short
   enough to fit one 16-column LCD line beside a short prefix, and each accessor returns a safe
   fallback ("?", "UNKNOWN", "160m") so the panel can never show a blank. */

/* The name for a latched trip mask: the highest-priority set bit (same order the LCD's trip screen
   tests them). Returns "UNKNOWN" for 0 and for any bit this table does not know. */
const char *trip_reason_name(unsigned char reason);

/* The name for a sequence stage, indexed directly by the enum value. Returns "?" out of range. */
const char *sequence_stage_name(unsigned char stage);

/* The name for a measured band. BAND_UNKNOWN aliases BAND_160M, so 160m is also what
   "no measurement yet" reads as - exactly what the operator needs to see. */
const char *band_name(rf_band_t band);

#endif
