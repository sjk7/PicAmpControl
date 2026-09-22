PIC18F47Q10 EEPROM Codec> **CORRECTIONS (2026-09-22)** - checked against the shipping `PIC18F-Q_DFP/1.30.487`
> (`pic18f47q10.h`), because the code below does not compile as written:
>
> 1. **`NVMCON1bits.NVMREG` does not exist on this part.** `NVMCON1` is
>    {`RD`, `SECRD`, `WR`, `SECWR`, `SECER`} - there is no memory-select field, so the
>    "select data EEPROM" step has nothing to write.
> 2. **`NVMCON0bits.NVMGO` does not exist either.** `NVMCON0` is {`NVMERR`, `NVMEN`} only. Start a
>    **read** with `NVMCON1bits.RD = 1` (self-clearing, so no wait loop is needed) and start a
>    **write** with `NVMCON1bits.WR = 1`, then wait for `WR` to clear.
> 3. Typo: `NVM0CON0bits.NVMEN` -> `NVMCON0bits.NVMEN`.
> 4. `NVMDAT` is fine (it aliases the low data byte), and `NVMCON2 = 0x55; NVMCON2 = 0xAA;` before
>    setting `WR` matches the header - the unlock destination is right, only the control bits differ.
>
> Corrected **write**: `NVMADRL/NVMADRH` -> `NVMDATL` -> `NVMCON0bits.NVMEN = 1` -> save and clear
> `INTCONbits.GIE` -> `NVMCON2 = 0x55` -> `NVMCON2 = 0xAA` -> `NVMCON1bits.WR = 1` -> restore `GIE`
> -> `while (NVMCON1bits.WR);` -> `NVMCON0bits.NVMEN = 0`.
>
> Corrected **read**: `NVMADRL/NVMADRH` -> `NVMCON0bits.NVMEN = 1` -> `NVMCON1bits.RD = 1` -> read
> `NVMDATL` -> `NVMCON0bits.NVMEN = 0`.
>
> The implementation lives in `firmware/src/nvm.c`, device-guarded so the PIC16F18875 keeps the
> toolchain's `eeprom_read`/`eeprom_write`. The code below is kept for reference only.

#include <xc.h>

void EEPROM_Write(unsigned int address, unsigned char data) {
    // 1. Set up the target EEPROM address (splits a 10-bit address)
    NVMADRL = (address & 0xFF);         
    NVMADRH = ((address >> 8) & 0x03);  

    // 2. Load the target data byte into the absolute NVMDAT register
    NVMDAT = data;                     

    // 3. Select Data EEPROM Memory access (0b00 = EEPROM)
    NVMCON1bits.NVMREG = 0;   
    
    // 4. Enable Non-Volatile Memory execution module
    NVMCON0bits.NVMEN = 1;    
    
    // 5. Clear global interrupts safely 
    unsigned char gie_state = INTCONbits.GIE; 
    INTCONbits.GIE = 0;       

    // 6. Mandatory Unlock Sequence via NVMCON2
    NVMCON2 = 0x55;
    NVMCON2 = 0xAA;
    
    // 7. Fire the write sequence using the NVMGO bit
    NVMCON0bits.NVMGO = 1;       

    // 8. Restore initial interrupt status
    INTCONbits.GIE = gie_state; 

    // 9. Await hardware write finish
    while (NVMCON0bits.NVMGO);   

    // 10. Immediately disable NVM module to safeguard against corruption
    NVMCON0bits.NVMEN = 0;   
}

unsigned char EEPROM_Read(unsigned int address) {
    // 1. Set up source EEPROM address
    NVMADRL = (address & 0xFF);         
    NVMADRH = ((address >> 8) & 0x03);  

    // 2. Point module directly to data EEPROM memory
    NVMCON1bits.NVMREG = 0;   
    
    // 3. Turn on the NVM system module
    NVMCON0bits.NVMEN = 1;    

    // 4. Set NVMGO to fetch the contents
    NVMCON0bits.NVMGO = 1;       

    // 5. Hold loop until hardware populates the target register
    while (NVMCON0bits.NVMGO);   

    // 6. Return the data directly from NVMDAT
    return NVMDAT;           
}