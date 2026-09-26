#ifndef LCD_FORMAT_H
#define LCD_FORMAT_H

/* Fixed-width formatting helpers layered on lcd_parallel.h, so a repeated redraw never leaves a
   stale digit behind from a previous, wider value. */

void lcd_write_spaces(unsigned char count);
void lcd_write_unsigned_padded(unsigned int value, unsigned char digits);
void lcd_write_power_bar(unsigned int power_w, unsigned int full_scale_w, unsigned char width);
void lcd_write_swr_right(unsigned char field_width, unsigned int swr_hundredths);
void lcd_write_swr_value(unsigned int swr_hundredths);

#endif
