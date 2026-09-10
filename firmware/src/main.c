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

static volatile system_state_t g_state = STATE_STANDBY;
static volatile bool g_fault_latched = false;
static volatile bool g_ptt_active = false;
static volatile bool g_startup_inhibit = true;

void adc_init(void) {
    FVRCON = 0x00;
    ANSELA = 0x0B;
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
        if (INPUT_COMP_SWR_1 == 0 && INPUT_COMP_SWR_2 == 0 && INPUT_COMP_OVERDRIVE == 0 && INPUT_COMP_OVERCURRENT == 0 && INPUT_COMP_DRAIN_PEAK == 0) {
            clear_fault_latches();
            g_state = STATE_OPERATE;
        }
    } else {
        g_ptt_active = false;
        g_state = STATE_STANDBY;
    }
}

void update_protection_state(unsigned int fwd_raw,
                            unsigned int ref_raw,
                            unsigned int temp_raw,
                            bool swr1_fault,
                            bool swr2_fault,
                            bool overdrive_fault,
                            bool drain_peak_fault,
                            bool overcurrent_fault) {
    bool any_hardware_fault = swr1_fault || swr2_fault || overdrive_fault || drain_peak_fault || overcurrent_fault;

    if (g_startup_inhibit) {
        g_state = STATE_RESET_WAIT;
        OUTPUT_TX = 1;
        OUTPUT_TX_VCC = 1;
        OUTPUT_TX_BIAS = 1;
        return;
    }

    if (any_hardware_fault) {
        g_fault_latched = true;
        g_state = STATE_TRIP;
        OUTPUT_TRIP_STATUS = 0;
        OUTPUT_WARNING_STATUS = 0;
        OUTPUT_TX = 1;
        OUTPUT_TX_VCC = 1;
        OUTPUT_TX_BIAS = 1;
        return;
    }

    if (temp_raw > 300) {
        g_state = STATE_WARNING;
        OUTPUT_WARNING_STATUS = 0;
        OUTPUT_TX = 0;
        OUTPUT_TX_VCC = 0;
        OUTPUT_TX_BIAS = 0;
    } else if (fwd_raw > 400 || ref_raw > 250) {
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
    unsigned int fwd_raw = 0;
    unsigned int ref_raw = 0;
    unsigned int temp_raw = 0;

    TRISAbits.TRISA0 = 1;
    TRISAbits.TRISA1 = 1;
    TRISAbits.TRISA3 = 1;
    TRISCbits.TRISC0 = 1;
    TRISCbits.TRISC1 = 1;
    TRISCbits.TRISC2 = 1;
    TRISCbits.TRISC3 = 1;
    TRISCbits.TRISC4 = 1;
    TRISCbits.TRISC5 = 0;
    TRISCbits.TRISC6 = 0;
    TRISCbits.TRISC7 = 0;

    TRISB = 0xFF;
    PORTB = 0x00;

    OUTPUT_TX = 1;
    OUTPUT_TX_VCC = 1;
    OUTPUT_TX_BIAS = 1;
    OUTPUT_WARNING_STATUS = 1;
    OUTPUT_TRIP_STATUS = 1;

    adc_init();
    apply_startup_inhibit();

    while (1) {
        __delay_ms(5);

        fwd_raw = adc_read(FWD_ADC_CHANNEL);
        ref_raw = adc_read(REF_ADC_CHANNEL);
        temp_raw = adc_read(TEMP_ADC_CHANNEL);

        bool swr1_fault = (INPUT_COMP_SWR_1 == 1);
        bool swr2_fault = (INPUT_COMP_SWR_2 == 1);
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

        update_protection_state(fwd_raw, ref_raw, temp_raw,
                                swr1_fault,
                                swr2_fault,
                                overdrive_fault,
                                drain_peak_fault,
                                overcurrent_fault);
    }
}
