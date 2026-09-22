#ifndef NVM_H
#define NVM_H

#include <stdbool.h>

/* Internal (on-chip) non-volatile storage for the versioned, checksummed settings record.
 *
 * This has its own translation unit rather than living inside the LCD driver because the two
 * devices in play need completely different implementations: the PIC16F18875 uses XC8's legacy
 * `eeprom_read`/`eeprom_write` helpers, while XC8 flags those as unsupported for the PIC18F-Q10
 * (the link fails with `undefined symbol "_Write_b_eep"`), so the Q10 drives its NVM block
 * directly.
 *
 * Owner's notes on that migration are in `Eeprom-changes.md` at the repo root - read that file
 * before changing anything here. Its 0x55/0xAA unlock (written to NVMCON2) matches this device,
 * but its bit names do not: this part has NVMCON1 = {RD, SECRD, WR, SECWR, SECER} and
 * NVMCON0 = {NVMERR, NVMEN}. The DFP header is the authority for names; see the skill.
 *
 * Addresses are 8-bit and lengths are bounded by the record size. The Q10 has 1 KB of EEPROM and
 * the PIC16F18875 has 256 bytes, so a record above 255 bytes would need the address widened here
 * and at the call sites.
 */
bool internal_eeprom_read(unsigned char address, unsigned char *data, unsigned char length);
bool internal_eeprom_write(unsigned char address, const unsigned char *data, unsigned char length);

#endif
