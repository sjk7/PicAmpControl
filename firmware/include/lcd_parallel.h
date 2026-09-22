#ifndef LCD_PARALLEL_H
#define LCD_PARALLEL_H

/* Interface for the 1602 LCD, driven in 4-bit *parallel* mode by lcd_parallel.c. The name says
 * parallel because that is what it is: there is no I2C backpack, and no I2C code anywhere in the
 * firmware. This header was called `lcd_i2c.h` until 2026-09-22 - a prototype-era name that kept
 * misleading readers - so it was renamed to match the driver. Internal EEPROM access is not here
 * either; that lives in nvm.h. */

#include <stdbool.h>

void lcd_init(void);
void lcd_write_byte(unsigned char value, bool data_mode);
void lcd_write_byte_now(unsigned char value, bool data_mode);
void lcd_service(unsigned char max_bytes);
void lcd_write_text(const char *text);
void lcd_write_unsigned(unsigned int value);
void lcd_set_cursor(unsigned char row, unsigned char column);

#endif
