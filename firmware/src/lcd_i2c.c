#include <xc.h>
#include <stdbool.h>
#include "../include/pin_map.h"
#include "../include/lcd_i2c.h"

static void i2c_delay(void) {
    __delay_us(5);
}

static void i2c_scl_low(void) {
    OUTPUT_LCD_I2C_SCL = 0;
    TRISCbits.TRISC3 = 0;
}

static void i2c_scl_release(void) {
    TRISCbits.TRISC3 = 1;
}

static void i2c_sda_low(void) {
    OUTPUT_LCD_I2C_SDA = 0;
    TRISCbits.TRISC4 = 0;
}

static void i2c_sda_release(void) {
    TRISCbits.TRISC4 = 1;
}

static void i2c_start(void) {
    i2c_sda_release();
    i2c_scl_release();
    i2c_delay();
    i2c_sda_low();
    i2c_delay();
    i2c_scl_low();
}

static void i2c_stop(void) {
    i2c_sda_low();
    i2c_delay();
    i2c_scl_release();
    i2c_delay();
    i2c_sda_release();
    i2c_delay();
}

static bool i2c_write_byte(unsigned char value) {
    unsigned char bit_mask;
    bool acknowledged;

    for (bit_mask = 0x80; bit_mask != 0; bit_mask >>= 1) {
        if ((value & bit_mask) != 0) {
            i2c_sda_release();
        } else {
            i2c_sda_low();
        }
        i2c_delay();
        i2c_scl_release();
        i2c_delay();
        i2c_scl_low();
    }

    i2c_sda_release();
    i2c_delay();
    i2c_scl_release();
    i2c_delay();
    acknowledged = (OUTPUT_LCD_I2C_SDA == 0);
    i2c_scl_low();
    return acknowledged;
}

static void lcd_write_nibble(unsigned char nibble, bool data_mode) {
    unsigned char expander_data = (unsigned char)((nibble << 4) | 0x08);

    if (data_mode) {
        expander_data |= 0x01;
    }

    i2c_write_byte(expander_data | 0x04);
    i2c_write_byte(expander_data);
}

void lcd_write_byte(unsigned char value, bool data_mode) {
    i2c_start();
    i2c_write_byte((unsigned char)(LCD_I2C_ADDRESS << 1));
    lcd_write_nibble((unsigned char)(value >> 4), data_mode);
    lcd_write_nibble((unsigned char)(value & 0x0F), data_mode);
    i2c_stop();
}

void lcd_write_text(const char *text) {
    while (*text != '\0') {
        lcd_write_byte((unsigned char)*text, true);
        text++;
    }
}

void lcd_write_unsigned(unsigned int value) {
    unsigned int divisor = 1000;
    bool digit_started = false;

    while (divisor > 0) {
        unsigned char digit = (unsigned char)(value / divisor);
        if (digit != 0 || digit_started || divisor == 1) {
            lcd_write_byte((unsigned char)('0' + digit), true);
            digit_started = true;
        }
        value %= divisor;
        divisor /= 10;
    }
}

void lcd_set_cursor(unsigned char row, unsigned char column) {
    lcd_write_byte((unsigned char)(0x80 | (row == 0 ? 0x00 : 0x40) | column), false);
}

void lcd_init(void) {
    i2c_sda_release();
    i2c_scl_release();
    __delay_ms(50);
    lcd_write_byte(0x33, false);
    lcd_write_byte(0x32, false);
    lcd_write_byte(0x28, false);
    lcd_write_byte(0x0C, false);
    lcd_write_byte(0x06, false);
    lcd_write_byte(0x01, false);
    __delay_ms(2);
}
