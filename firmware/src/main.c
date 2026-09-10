#include <xc.h>
#include <stdbool.h>
#include "../include/pin_map.h"

#pragma config FOSC = HS
#pragma config WDTE = OFF
#pragma config PWRTE = OFF
#pragma config MCLRE = ON
#pragma config CP = OFF
#pragma config BOREN = ON
#pragma config BORV = 19
#pragma config PLLEN = OFF

typedef enum {
    STATE_STANDBY = 0,
    STATE_IDLE,
    STATE_OPERATE,
    STATE_WARNING,
    STATE_TRIP,
    STATE_FAULT_LATCHED,
    STATE_RESET_WAIT
} system_state_t;

typedef enum {
    MENU_PAGE_STATUS = 0,
    MENU_PAGE_SWR1_TRIP,
    MENU_PAGE_SWR2_TRIP,
    MENU_PAGE_TEMP_WARNING,
    MENU_PAGE_TEMP_TRIP,
    MENU_PAGE_COUNT
} menu_page_t;

typedef struct {
    unsigned char swr1_trip_tenths;
    unsigned char swr2_trip_tenths;
    unsigned int temp_warning_raw;
    unsigned int temp_trip_raw;
} protection_thresholds_t;

static volatile system_state_t g_state = STATE_STANDBY;
static volatile bool g_fault_latched = false;
static volatile bool g_ptt_active = false;
static volatile bool g_startup_inhibit = true;
static volatile menu_page_t g_menu_page = MENU_PAGE_STATUS;
static volatile bool g_menu_changed = true;
static protection_thresholds_t g_thresholds = {
    20, 20,
    300, 350
};

void i2c_delay(void) {
    __delay_us(5);
}

void i2c_scl_low(void) {
    OUTPUT_LCD_I2C_SCL = 0;
    TRISCbits.TRISC3 = 0;
}

void i2c_scl_release(void) {
    TRISCbits.TRISC3 = 1;
}

void i2c_sda_low(void) {
    OUTPUT_LCD_I2C_SDA = 0;
    TRISCbits.TRISC4 = 0;
}

void i2c_sda_release(void) {
    TRISCbits.TRISC4 = 1;
}

void i2c_start(void) {
    i2c_sda_release();
    i2c_scl_release();
    i2c_delay();
    i2c_sda_low();
    i2c_delay();
    i2c_scl_low();
}

void i2c_stop(void) {
    i2c_sda_low();
    i2c_delay();
    i2c_scl_release();
    i2c_delay();
    i2c_sda_release();
    i2c_delay();
}

bool i2c_write_byte(unsigned char value) {
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

void lcd_write_nibble(unsigned char nibble, bool data_mode) {
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

void show_menu_page(void) {
    const char *label = "STATUS";
    unsigned int value = 0;

    switch (g_menu_page) {
        case MENU_PAGE_SWR1_TRIP:
            label = "S1 SWR TRIP";
            value = g_thresholds.swr1_trip_tenths;
            break;
        case MENU_PAGE_SWR2_TRIP:
            label = "S2 SWR TRIP";
            value = g_thresholds.swr2_trip_tenths;
            break;
        case MENU_PAGE_TEMP_WARNING:
            label = "TEMP WARNING";
            value = g_thresholds.temp_warning_raw;
            break;
        case MENU_PAGE_TEMP_TRIP:
            label = "TEMP TRIP";
            value = g_thresholds.temp_trip_raw;
            break;
        default:
            break;
    }

    lcd_write_byte(0x01, false);
    __delay_ms(2);
    lcd_set_cursor(0, 0);
    lcd_write_text(label);
    lcd_set_cursor(1, 0);
    if (g_menu_page == MENU_PAGE_STATUS) {
        lcd_write_text(g_ptt_active ? "TRANSMIT" : "RECEIVE");
    } else if (g_menu_page == MENU_PAGE_SWR1_TRIP || g_menu_page == MENU_PAGE_SWR2_TRIP) {
        lcd_write_unsigned((unsigned int)(value / 10));
        lcd_write_byte('.', true);
        lcd_write_unsigned((unsigned int)(value % 10));
        lcd_write_text(":1");
    } else {
        lcd_write_unsigned(value);
    }
}

void adc_init(void) {
    FVRCON = 0x00;
    ANSELA = 0x1F;
    ADCON1 = 0x22;
    ADCON0 = 0x01;
}

unsigned int adc_read(unsigned char channel) {
    ADCON0 &= 0x03;
    ADCON0 |= (unsigned char)(channel << 2);
    __delay_us(20);
    ADCON0bits.GO_DONE = 1;
    while (ADCON0bits.GO_DONE) {
        continue;
    }
    return (unsigned int)ADRES;
}

void apply_startup_inhibit(void) {
    OUTPUT_TX = 1;
    OUTPUT_TX_VCC = 1;
    OUTPUT_TX_BIAS = 1;
    OUTPUT_WARNING_STATUS = 1;
    OUTPUT_TRIP_STATUS = 1;
    g_startup_inhibit = true;
}

void clear_fault_latches(void) {
    g_fault_latched = false;
    OUTPUT_WARNING_STATUS = 1;
    OUTPUT_TRIP_STATUS = 1;
}

void handle_ptt_transition(bool ptt_asserted) {
    if (ptt_asserted) {
        g_ptt_active = true;
        if (!g_fault_latched) {
            g_state = STATE_RESET_WAIT;
        }
        // Purposefully clear only software latches when a new transmit cycle begins.
        // Real hardware comparator faults must still be checked before enabling the amplifier.
        if (INPUT_COMP_OVERDRIVE == 0 && INPUT_COMP_OVERCURRENT == 0 && INPUT_COMP_DRAIN_PEAK == 0) {
            clear_fault_latches();
            g_state = STATE_OPERATE;
        }
    } else {
        g_ptt_active = false;
        g_state = STATE_STANDBY;
    }
}

bool swr_trip(unsigned int forward_raw, unsigned int reflected_raw, unsigned char limit_tenths) {
    unsigned long upper_factor;
    unsigned long lower_factor;

    if (forward_raw < 10 || limit_tenths <= 10) {
        return false;
    }

    upper_factor = (unsigned long)(limit_tenths + 10) * (limit_tenths + 10);
    lower_factor = (unsigned long)(limit_tenths - 10) * (limit_tenths - 10);
    return (unsigned long)reflected_raw * upper_factor >= (unsigned long)forward_raw * lower_factor;
}

void adjust_selected_threshold(bool increase) {
    unsigned int *selected_threshold = 0;
    unsigned char *selected_swr_threshold = 0;

    switch (g_menu_page) {
        case MENU_PAGE_SWR1_TRIP:
            selected_swr_threshold = &g_thresholds.swr1_trip_tenths;
            break;
        case MENU_PAGE_SWR2_TRIP:
            selected_swr_threshold = &g_thresholds.swr2_trip_tenths;
            break;
        case MENU_PAGE_TEMP_WARNING:
            selected_threshold = &g_thresholds.temp_warning_raw;
            break;
        case MENU_PAGE_TEMP_TRIP:
            selected_threshold = &g_thresholds.temp_trip_raw;
            break;
        default:
            break;
    }

    if (selected_swr_threshold != 0) {
        if (increase && *selected_swr_threshold < 50) {
            *selected_swr_threshold += 1;
        } else if (!increase && *selected_swr_threshold > 11) {
            *selected_swr_threshold -= 1;
        }
        return;
    }

    if (selected_threshold == 0) {
        return;
    }

    if (increase && *selected_threshold < 1013) {
        *selected_threshold += 10;
    } else if (!increase && *selected_threshold > 10) {
        *selected_threshold -= 10;
    }
}

void poll_menu_inputs(void) {
    static bool next_was_pressed = false;
    static bool increase_was_pressed = false;
    static bool decrease_was_pressed = false;
    bool next_pressed = (INPUT_MENU_NEXT == 0);
    bool increase_pressed = (INPUT_MENU_INCREASE == 0);
    bool decrease_pressed = (INPUT_MENU_DECREASE == 0);

    if (!g_ptt_active) {
        if (next_pressed && !next_was_pressed) {
            g_menu_page = (menu_page_t)((g_menu_page + 1) % MENU_PAGE_COUNT);
            g_menu_changed = true;
        }
        if (increase_pressed && !increase_was_pressed) {
            adjust_selected_threshold(true);
            g_menu_changed = true;
        }
        if (decrease_pressed && !decrease_was_pressed) {
            adjust_selected_threshold(false);
            g_menu_changed = true;
        }
    }

    next_was_pressed = next_pressed;
    increase_was_pressed = increase_pressed;
    decrease_was_pressed = decrease_pressed;
}

void update_protection_state(unsigned int temp_raw,
                            bool swr1_fault,
                            bool swr2_fault,
                            bool overdrive_fault,
                            bool drain_peak_fault,
                            bool overcurrent_fault) {
    bool any_trip_fault = swr1_fault || swr2_fault || overdrive_fault || drain_peak_fault || overcurrent_fault || (temp_raw >= g_thresholds.temp_trip_raw);

    if (g_startup_inhibit) {
        g_state = STATE_RESET_WAIT;
        OUTPUT_TX = 1;
        OUTPUT_TX_VCC = 1;
        OUTPUT_TX_BIAS = 1;
        return;
    }

    if (any_trip_fault) {
        g_fault_latched = true;
        g_state = STATE_TRIP;
        OUTPUT_TRIP_STATUS = 0;
        OUTPUT_WARNING_STATUS = 0;
        OUTPUT_TX = 1;
        OUTPUT_TX_VCC = 1;
        OUTPUT_TX_BIAS = 1;
        return;
    }

    if (temp_raw >= g_thresholds.temp_warning_raw) {
        g_state = STATE_WARNING;
        OUTPUT_WARNING_STATUS = 0;
        OUTPUT_TX = 0;
        OUTPUT_TX_VCC = 0;
        OUTPUT_TX_BIAS = 0;
    } else {
        g_state = STATE_OPERATE;
        OUTPUT_WARNING_STATUS = 1;
        OUTPUT_TRIP_STATUS = 1;
        OUTPUT_TX = 0;
        OUTPUT_TX_VCC = 0;
        OUTPUT_TX_BIAS = 0;
    }
}

int main(void) {
    unsigned int swr1_fwd_raw = 0;
    unsigned int swr1_ref_raw = 0;
    unsigned int swr2_fwd_raw = 0;
    unsigned int swr2_ref_raw = 0;
    unsigned int temp_raw = 0;

    TRISAbits.TRISA0 = 1;
    TRISAbits.TRISA1 = 1;
    TRISAbits.TRISA2 = 1;
    TRISAbits.TRISA3 = 1;
    TRISAbits.TRISA4 = 1;
    TRISCbits.TRISC0 = 1;
    TRISCbits.TRISC1 = 1;
    TRISCbits.TRISC2 = 1;
    TRISCbits.TRISC3 = 1;
    TRISCbits.TRISC4 = 1;
    TRISCbits.TRISC5 = 0;
    TRISCbits.TRISC6 = 0;
    TRISCbits.TRISC7 = 0;

    TRISB = 0x1F;
    PORTB = 0x00;
    WPUB = 0x03;
    OPTION_REGbits.nRBPU = 0;

    OUTPUT_TX = 1;
    OUTPUT_TX_VCC = 1;
    OUTPUT_TX_BIAS = 1;
    OUTPUT_WARNING_STATUS = 1;
    OUTPUT_TRIP_STATUS = 1;

    adc_init();
    lcd_init();
    show_menu_page();
    apply_startup_inhibit();

    while (1) {
        __delay_ms(5);

        swr1_fwd_raw = adc_read(ADC_SWR1_FWD_CHANNEL);
        swr1_ref_raw = adc_read(ADC_SWR1_REF_CHANNEL);
        swr2_fwd_raw = adc_read(ADC_SWR2_FWD_CHANNEL);
        swr2_ref_raw = adc_read(ADC_SWR2_REF_CHANNEL);
        temp_raw = adc_read(ADC_TEMP_CHANNEL);

        bool swr1_fault = swr_trip(swr1_fwd_raw, swr1_ref_raw, g_thresholds.swr1_trip_tenths);
        bool swr2_fault = swr_trip(swr2_fwd_raw, swr2_ref_raw, g_thresholds.swr2_trip_tenths);
        bool overdrive_fault = (INPUT_COMP_OVERDRIVE == 1);
        bool drain_peak_fault = (INPUT_COMP_DRAIN_PEAK == 1);
        bool overcurrent_fault = (INPUT_COMP_OVERCURRENT == 1);

        if (g_startup_inhibit) {
            __delay_ms(1000);
            g_startup_inhibit = false;
        }

        if (INPUT_PTT == 0) {
            handle_ptt_transition(true);
        } else {
            handle_ptt_transition(false);
        }

        poll_menu_inputs();

        if (g_menu_changed) {
            show_menu_page();
            g_menu_changed = false;
        }

        update_protection_state(temp_raw,
                                swr1_fault,
                                swr2_fault,
                                overdrive_fault,
                                drain_peak_fault,
                                overcurrent_fault);
    }
}
