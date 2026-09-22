#include <xc.h>
#include <stdbool.h>
#include "../include/pin_map.h"
#include "../include/lcd_parallel.h"

/* Parallel LCD in 4-bit mode using freed pins:
   RS=RA4, E=RA6, D4=RA7, D5=RC3, D6=RC4, D7=RD0 */

static void lcd_delay_us(unsigned int us) {
    while (us--) {
        __delay_us(1);
    }
}

static void lcd_set_data_pins(unsigned char nibble) {
    OUTPUT_LCD_D4 = (nibble >> 0) & 1U;
    OUTPUT_LCD_D5 = (nibble >> 1) & 1U;
    OUTPUT_LCD_D6 = (nibble >> 2) & 1U;
    OUTPUT_LCD_D7 = (nibble >> 3) & 1U;
}

static void lcd_pulse_enable(void) {
    OUTPUT_LCD_E = 1;
    lcd_delay_us(1);
    OUTPUT_LCD_E = 0;
    lcd_delay_us(50);
}

static void lcd_write_nibble(unsigned char nibble, bool data_mode) {
    OUTPUT_LCD_RS = data_mode ? 1 : 0;
    lcd_delay_us(1);
    lcd_set_data_pins(nibble);
    lcd_delay_us(1);
    lcd_pulse_enable();
}

void lcd_write_byte_now(unsigned char value, bool data_mode) {
    /* High nibble first */
    lcd_write_nibble((unsigned char)(value >> 4), data_mode);
    /* Low nibble */
    lcd_write_nibble((unsigned char)(value & 0x0F), data_mode);
    lcd_delay_us(100);
}

/* Queue so the main loop can send a few bytes at a time between protection
   checks instead of blocking. */
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
    /* Initialize all LCD pins as outputs */
    TRISAbits.TRISA4 = 0;  /* RS */
    TRISAbits.TRISA6 = 0;  /* E */
    TRISAbits.TRISA7 = 0;  /* D4 */
    TRISCbits.TRISC3 = 0;  /* D5 */
    TRISCbits.TRISC4 = 0;  /* D6 */
    TRISDbits.TRISD0 = 0;  /* D7 */

    /* Set all pins low initially */
    OUTPUT_LCD_RS = 0;
    OUTPUT_LCD_E = 0;
    OUTPUT_LCD_D4 = 0;
    OUTPUT_LCD_D5 = 0;
    OUTPUT_LCD_D6 = 0;
    OUTPUT_LCD_D7 = 0;

    __delay_ms(50);

    /* 4-bit mode initialization sequence (send as high nibble only) */
    OUTPUT_LCD_RS = 0;  /* Command mode */

    /* Function set: 8-bit interface (3 times) to ensure 8-bit mode */
    lcd_set_data_pins(0x3);  /* 0011 */
    lcd_pulse_enable();
    __delay_ms(5);

    lcd_set_data_pins(0x3);
    lcd_pulse_enable();
    __delay_ms(1);

    lcd_set_data_pins(0x3);
    lcd_pulse_enable();
    __delay_ms(1);

    /* Function set: 4-bit interface */
    lcd_set_data_pins(0x2);  /* 0010 */
    lcd_pulse_enable();
    __delay_ms(1);

    /* Now in 4-bit mode; use full bytes */
    lcd_write_byte_now(0x28, false);  /* Function set: 4-bit, 2 lines, 5x8 font */
    lcd_write_byte_now(0x0C, false);  /* Display ON, cursor OFF, blink OFF */
    lcd_write_byte_now(0x06, false);  /* Entry mode: auto-increment address */
    lcd_write_byte_now(0x01, false);  /* Clear display */
    __delay_ms(2);
}

/* Internal EEPROM access now lives in firmware/src/nvm.c: the two devices need different
   implementations, so it no longer belongs in the LCD driver. */
