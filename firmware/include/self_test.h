#ifndef SELF_TEST_H
#define SELF_TEST_H

#include <stdbool.h>

/* Firmware-only diagnostic self-test (docs/firmware-self-test-diagnostic.md). Each check is one
   bit of `g_diag_result`; 0 = every check passed. The harness reads g_diag_request / g_diag_done /
   g_diag_result directly (by .sym address) and only ever reads the verdict - the firmware runs every
   check itself and decides PASS/FAIL. */
typedef enum {
    DIAG_OK = 0x00,
    DIAG_OUTPUTS = 0x01,    /* an output failed to reach/leave its commanded level */
    DIAG_SEQUENCER = 0x02,  /* the 0->1->2->3->0 sequencer walk failed */
    DIAG_LCD = 0x04,        /* LCD liveness not confirmed */
    DIAG_EEPROM = 0x08      /* settings EEPROM round-trip failed */
} diag_check_t;

#define DIAG_CHECK_COUNT 4
#define DIAG_CHECK_ALL 0xFF   /* run every check */

/* Trigger written by the SELF TEST menu page or by the simulator (through the .sym address). */
extern volatile bool g_diag_request;

/* Menu selection: rotate to pick which check(s) the next press runs, then press to run. */
void diag_select_cycle(void);            /* advance ALL -> OUTPUT -> SEQ -> LCD -> EEPROM -> ALL */
unsigned char diag_selected_index(void); /* 0..4 */
const char *diag_selected_name(void);    /* "ALL" / "OUTPUT" / "SEQ" / "LCD" / "EEPROM" */

/* Begin a run of the currently selected check(s). Cold-only (not keyed, no latched fault). */
void diag_start(void);
bool diag_busy(void);                    /* a requested run is executing */
bool diag_done(void);                    /* the most recent run has finished */
unsigned char diag_result(void);         /* PASS/FAIL mask (0 = all passed) */

/* Advance a running diagnostic by `elapsed_ms` ticks (called once per main-loop pass). */
void diag_tick(unsigned int elapsed_ms);

/* The LCD label for check bit `index` (0..3). */
const char *diag_check_name(unsigned char index);

#endif
