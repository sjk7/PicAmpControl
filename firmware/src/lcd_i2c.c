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

void lcd_write_byte_now(unsigned char value, bool data_mode) {
    i2c_start();
    i2c_write_byte((unsigned char)(LCD_I2C_ADDRESS << 1));
    lcd_write_nibble((unsigned char)(value >> 4), data_mode);
    lcd_write_nibble((unsigned char)(value & 0x0F), data_mode);
    i2c_stop();
}

/* Queue so the main loop can send a few bytes at a time between protection
   checks instead of blocking for a whole page (~13 ms bit-banged at 5 us/step).
   56 entries comfortably covers the worst case: the TRIP screen with every
   fault reason set at once is 49 bytes (13 on row 0 + 36 on row 1). */
#define LCD_QUEUE_SIZE 56

typedef struct {
    unsigned char value;
    bool data_mode;
} lcd_queue_entry_t;

static lcd_queue_entry_t g_lcd_queue[LCD_QUEUE_SIZE];
static unsigned char g_lcd_queue_head = 0;
static unsigned char g_lcd_queue_tail = 0;
static unsigned char g_lcd_queue_count = 0;

void lcd_write_byte(unsigned char value, bool data_mode) {
    if (g_lcd_queue_count >= LCD_QUEUE_SIZE) {
        /* Shouldn't happen at real page sizes; drop the oldest byte rather
           than block the caller. */
        g_lcd_queue_tail = (unsigned char)((g_lcd_queue_tail + 1) % LCD_QUEUE_SIZE);
        g_lcd_queue_count--;
    }
    g_lcd_queue[g_lcd_queue_head].value = value;
    g_lcd_queue[g_lcd_queue_head].data_mode = data_mode;
    g_lcd_queue_head = (unsigned char)((g_lcd_queue_head + 1) % LCD_QUEUE_SIZE);
    g_lcd_queue_count++;
}

void lcd_service(unsigned char max_bytes) {
    while (max_bytes > 0 && g_lcd_queue_count > 0) {
        lcd_write_byte_now(g_lcd_queue[g_lcd_queue_tail].value, g_lcd_queue[g_lcd_queue_tail].data_mode);
        g_lcd_queue_tail = (unsigned char)((g_lcd_queue_tail + 1) % LCD_QUEUE_SIZE);
        g_lcd_queue_count--;
        max_bytes--;
    }
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
    /* One-time startup sequence: send immediately (queue/main loop don't exist yet). */
    lcd_write_byte_now(0x33, false);
    lcd_write_byte_now(0x32, false);
    lcd_write_byte_now(0x28, false);
    lcd_write_byte_now(0x0C, false);
    lcd_write_byte_now(0x06, false);
    lcd_write_byte_now(0x01, false);
    __delay_ms(2);
}

bool internal_eeprom_read(unsigned char address, unsigned char *data, unsigned char length) {
    unsigned char index;

    for (index = 0; index < length; index++) {
        data[index] = eeprom_read((unsigned char)(address + index));
    }
    return true;
}

bool internal_eeprom_write(unsigned char address, const unsigned char *data, unsigned char length) {
    unsigned char index;

    for (index = 0; index < length; index++) {
        eeprom_write((unsigned char)(address + index), data[index]);
    }
    return true;
}
