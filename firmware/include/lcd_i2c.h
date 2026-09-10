#ifndef LCD_I2C_H
#define LCD_I2C_H

#include <stdbool.h>

void lcd_init(void);
void lcd_write_byte(unsigned char value, bool data_mode);
void lcd_write_text(const char *text);
void lcd_write_unsigned(unsigned int value);
void lcd_set_cursor(unsigned char row, unsigned char column);

#endif
