#include "../include/labels.h"

/* One name per trip cause, indexed by bit position, so this array and the trip_reason_t enum in
   state.h must stay in the same order. Kept to <= TRIP_REASON_NAME_MAX characters so a name always
   fits on one 16-column LCD line beside a short prefix. */
static const char *const TRIP_REASON_NAMES[] = {
    "SWR1",        /* TRIP_REASON_SWR1      0x01 */
    "SWR2",        /* TRIP_REASON_SWR2      0x02 */
    "HARDWARE",    /* TRIP_REASON_HWFAULT   0x04 */
    "CURRENT",     /* TRIP_REASON_CURRENT   0x08 */
    "TEMPERATURE", /* TRIP_REASON_TEMP      0x10 */
    "OVERDRIVE",   /* TRIP_REASON_OVERDRIVE 0x20 */
    "DRAIN"        /* TRIP_REASON_DRAIN     0x40 */
};

const char *trip_reason_name(unsigned char reason) {
    /* Bit positions, most severe first, in the same order the trip screen tests causes in:
       TEMP, SWR1, SWR2, CURRENT, OVERDRIVE, HWFAULT, DRAIN. `reason & (1u << bit)` uses the enum
       values as the bit positions they are, so a typo here cannot silently name the wrong fault. */
    static const unsigned char priority_bits[] = { 4u, 0u, 1u, 3u, 5u, 2u, 6u };
    unsigned char index;
    for (index = 0; index < (unsigned char)(sizeof priority_bits / sizeof priority_bits[0]); index++) {
        if (reason & (unsigned char)(1u << priority_bits[index])) {
            return TRIP_REASON_NAMES[priority_bits[index]];
        }
    }
    return "UNKNOWN";
}

/* Text for a sequence stage. Indexed directly by the enum value, so the two must stay in the same
   order. */
static const char *const SEQUENCE_STAGE_NAMES[] = {
    "IDLE",         /* SEQ_IDLE           */
    "TX-ON",        /* SEQ_TX_ON          */
    "VCC-ON",       /* SEQ_VCC_ON         */
    "BIAS-ON",      /* SEQ_BIAS_ON        */
    "UNKEY-RELAYS", /* SEQ_RELEASE_RELAYS */
    "UNKEY-VCC"     /* SEQ_RELEASE_VCC    */
};

const char *sequence_stage_name(unsigned char stage) {
    if (stage >= (unsigned char)(sizeof SEQUENCE_STAGE_NAMES / sizeof SEQUENCE_STAGE_NAMES[0])) {
        return "?";
    }
    return SEQUENCE_STAGE_NAMES[stage];
}

const char *band_name(rf_band_t band) {
    switch (band) {
        case BAND_80M: return "80m";
        case BAND_40M: return "40m";
        case BAND_20M: return "20m";
        case BAND_15M: return "15m";
        case BAND_10M: return "10m";
        case BAND_OUT_OF_SPEC: return "OOS";
        case BAND_160M:
        default: return "160m";
    }
}
