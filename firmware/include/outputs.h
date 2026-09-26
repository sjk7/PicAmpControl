#ifndef OUTPUTS_H
#define OUTPUTS_H

#include <stdbool.h>

/* Output drives and the safety helpers around them. Written through the LAT registers (see
   pin_map.h); the active-high polarity of each output comes from g_thresholds. */

/* Map a logical active flag to the pin level, honouring the configured polarity. */
bool output_level(bool active, bool active_high);

void set_tx_output(bool active);
void set_tx_vcc_output(bool active);
void set_tx_bias_output(bool active);
void set_fan_output(bool active);
void set_trip_output(bool active);

/* Force every TX output off (bypass). Always safe: RF passes straight through, no LDMOS bias. */
void apply_bypass(void);

/* Unlock the band only once every TX output is confirmed inactive at the pin. */
void release_band_if_cold(void);

/* The relay selection may follow live RF again: drop the established-band claim. */
void invalidate_established_band(void);

#endif
