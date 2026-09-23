#ifndef NVM_H
#define NVM_H

#include <stdbool.h>

/* Internal (on-chip) non-volatile storage for the versioned, checksummed settings record.
 *
 * This has its own translation unit rather than living inside the LCD driver: XC8 flags the
 * legacy `eeprom_read`/`eeprom_write` helpers as unsupported on this part (the link fails with
 * `undefined symbol "_Write_b_eep"`), so the driver here talks to the NVM block directly.
 *
 * Owner's notes on the migration are in `Eeprom-changes.md` at the repo root - read that file
 * before changing anything here. Its 0x55/0xAA unlock (written to NVMCON2) matches this device,
 * but its bit names do not: this part has NVMCON1 = {RD, SECRD, WR, SECWR, SECER} and
 * NVMCON0 = {NVMERR, NVMEN}. The DFP header is the authority for names; see the skill.
 *
 * Addresses are 8-bit and lengths are bounded by the record size. This part has 1 KB of EEPROM,
 * so a record above 255 bytes would need the address widened here and at the call sites.
 */
bool internal_eeprom_read(unsigned char address, unsigned char *data, unsigned char length);
bool internal_eeprom_write(unsigned char address, const unsigned char *data, unsigned char length);

#endif
