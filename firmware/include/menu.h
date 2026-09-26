#ifndef MENU_H
#define MENU_H

#include "state.h"

/* LCD menu / encoder UI: page rendering, the boot message, and input polling. */

bool is_live_menu_page(menu_page_t page);
void show_menu_page(void);
void show_boot_message(void);
void poll_menu_inputs(unsigned int elapsed_ms);

#endif
