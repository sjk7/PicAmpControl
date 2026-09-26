#include "../include/lcd_parallel.h"
#include "../include/lcd_format.h"

void lcd_write_spaces(unsigned char count) {
    while (count > 0) {
        lcd_write_byte(' ', true);
        count--;
    }
}

/* Right-justifies value within a fixed digit width so repeated redraws never
   leave a stale digit behind from a previous, wider value. */
void lcd_write_unsigned_padded(unsigned int value, unsigned char digits) {
    unsigned int threshold = 1;
    unsigned char pad;

    for (pad = digits; pad > 1; pad--) {
        threshold *= 10;
    }
    for (pad = digits; pad > 1; pad--) {
        if (value >= threshold) {
            break;
        }
        lcd_write_spaces(1);
        threshold /= 10;
    }
    lcd_write_unsigned(value);
}

void lcd_write_power_bar(unsigned int power_w, unsigned int full_scale_w, unsigned char width) {
    unsigned char bar_segment;
    unsigned char bar_segments;

    if (full_scale_w == 0) {
        full_scale_w = 1;
    }

    /* 16-bit on purpose: power_w is bounded by the configured forward full scale (2500 W max)
       and width by the LCD columns, so the product cannot overflow 16 bits. Using longs here
       pulled the 32-bit divide/multiply helpers into the image for no reason. */
    bar_segments = (unsigned char)((power_w * width) / full_scale_w);

    if (bar_segments > width) {
        bar_segments = width;
    }

    for (bar_segment = 0; bar_segment < width; bar_segment++) {
        lcd_write_byte(bar_segment < bar_segments ? '|' : '.', true);
    }
}

void lcd_write_swr_right(unsigned char field_width, unsigned int swr_hundredths) {
    unsigned int whole = swr_hundredths / 100U;
    unsigned int fraction = swr_hundredths % 100U;
    unsigned char text_len = (unsigned char)(4 + (whole >= 10 ? 2 : 1) + 3);

    while (field_width > text_len) {
        lcd_write_byte(' ', true);
        field_width--;
    }
    lcd_write_text("SWR=");
    lcd_write_unsigned(whole);
    lcd_write_byte('.', true);
    lcd_write_unsigned_padded(fraction, 2);
}

void lcd_write_swr_value(unsigned int swr_hundredths) {
    /* "x.xx" only. The trip screen shows measured/limit side by side ("2.34/2.00:1"), and the
       "SWR=" prefix the meter pages use does not fit on one 16-column line twice. */
    lcd_write_unsigned(swr_hundredths / 100U);
    lcd_write_byte('.', true);
    lcd_write_unsigned_padded(swr_hundredths % 100U, 2);
}
