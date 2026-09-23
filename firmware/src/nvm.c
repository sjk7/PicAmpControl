/*
 * Internal (on-chip) non-volatile storage - the versioned, checksummed settings record.
 *
 * PIC18F47Q10 ONLY. The legacy `eeprom_read`/`eeprom_write` helpers do not exist on this part:
 * XC8 warns "The Read_b_eep routine is no longer supported" and the link fails with `undefined
 * symbol "_Write_b_eep"`. This device therefore drives its own NVM block.
 *
 * The register names and the read/write procedure come from the DFP header
 * (PIC18F-Q_DFP/1.30.487), NOT from the `Eeprom-changes.md` notes: those notes name
 * `NVMCON1bits.NVMREG` and `NVMCON0bits.GO`, neither of which exists on this part. Only the
 * 0x55/0xAA unlock destination (NVMCON2) matches. Code written to the notes' names does not
 * compile, which is the cheapest possible way to find that out - so compile early.
 */

#include <xc.h>
#include <stdbool.h>

#include "../include/nvm.h"

static unsigned char eeprom_read_byte(unsigned char address) {
    NVMADRL = address;
    NVMADRH = 0;
    NVMCON0bits.NVMEN = 1;   /* the NVM block must be enabled for reads too */
    NVMCON1bits.RD = 1;      /* self-clearing once the byte has been fetched */
    unsigned char value = NVMDATL;
    NVMCON0bits.NVMEN = 0;   /* disable again so an accidental write cannot land */
    return value;
}

static void eeprom_write_byte(unsigned char address, unsigned char value) {
    NVMADRL = address;
    NVMADRH = 0;
    NVMDATL = value;
    NVMCON0bits.NVMEN = 1;

    /* The unlock cascade must not be interrupted, or the hardware silently abandons the write
       and the settings record loses a byte with nothing reporting it. */
    bool gie = INTCONbits.GIE;
    INTCONbits.GIE = 0;
    NVMCON2 = 0x55;
    NVMCON2 = 0xAA;
    NVMCON1bits.WR = 1;
    INTCONbits.GIE = gie;

    while (NVMCON1bits.WR) {
        ;   /* the write cycle is self-timed; WR clears when it completes */
    }
    NVMCON0bits.NVMEN = 0;
}

bool internal_eeprom_read(unsigned char address, unsigned char *data, unsigned char length) {
    unsigned char index;

    for (index = 0; index < length; index++) {
        data[index] = eeprom_read_byte((unsigned char)(address + index));
    }
    return true;
}

bool internal_eeprom_write(unsigned char address, const unsigned char *data, unsigned char length) {
    unsigned char index;

    for (index = 0; index < length; index++) {
        eeprom_write_byte((unsigned char)(address + index), data[index]);
    }
    return true;
}
