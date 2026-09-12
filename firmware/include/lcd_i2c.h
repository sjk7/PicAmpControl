#ifndef LCD_I2C_H
#define LCD_I2C_H

#include <stdbool.h>

void lcd_init(void);
void lcd_write_byte(unsigned char value, bool data_mode);
void lcd_write_byte_now(unsigned char value, bool data_mode);
void lcd_service(unsigned char max_bytes);
void lcd_write_text(const char *text);
void lcd_write_unsigned(unsigned int value);
void lcd_set_cursor(unsigned char row, unsigned char column);
bool internal_eeprom_read(unsigned char address, unsigned char *data, unsigned char length);
bool internal_eeprom_write(unsigned char address, const unsigned char *data, unsigned char length);

#endif
