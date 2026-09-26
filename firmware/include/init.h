#ifndef INIT_H
#define INIT_H

/* Board bring-up: the ~1 ms system tick, the ADC, and the startup-inhibit window. */

void timer0_init(void);
void adc_init(void);
void apply_startup_inhibit(void);

#endif
