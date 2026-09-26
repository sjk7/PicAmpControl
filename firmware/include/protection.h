#ifndef PROTECTION_H
#define PROTECTION_H

#include <stdbool.h>

/* Protection / measurement maths and the trip state machine. Raw ADC values are 10-bit
   (0..1023); the conversion helpers turn them into engineering units, and
   update_protection_state() is the single place that latches and clears a trip. */

bool swr_trip(unsigned int forward_raw, unsigned int reflected_raw, unsigned char limit_tenths);
unsigned int isqrt32(unsigned long value);
unsigned int compute_swr_hundredths(unsigned int forward_raw, unsigned int reflected_raw);
unsigned int drain_voltage(unsigned int raw);
unsigned int temperature_c(unsigned int raw);
unsigned int overdrive_power_mw(unsigned int raw);
unsigned int current_amperes(unsigned int raw);

void update_post_filter_power(unsigned int forward_raw, unsigned int reflected_raw);
void update_peak_decay(unsigned int *peak_value, unsigned int *elapsed_ms, unsigned int tick_ms);
void update_current_peak(unsigned int current_a);

void update_protection_state(unsigned int temp_c,
                             unsigned int overdrive_raw,
                             unsigned int drain_raw,
                             bool swr1_fault,
                             bool swr2_fault,
                             bool hw_fault,
                             bool current_fault);

#endif
