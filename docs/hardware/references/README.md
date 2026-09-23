# Device reference documents

This project targets the **PIC18F47Q10 only** (see `Ai-Notes.txt`). These are the authoritative
vendor documents for that part, kept in-repo so a session does not have to re-find them or work
from a paraphrase.

| Document | File | Doc number |
|---|---|---|
| PIC18F27/47Q10 28/40/44-pin, Low-Power, High-Performance Microcontrollers Data Sheet | `DS40002043_PIC18F27-47Q10_datasheet.pdf` | DS40002043 |
| PIC18F27/47Q10 Silicon Errata and Data Sheet Clarifications | `DS80000832_PIC18F27-47Q10_erratum.pdf` | DS80000832 |

Canonical sources (re-download if a newer revision appears):

- Data sheet:
  https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/PIC18F27-47Q10-Micorcontroller-Data-Sheet-DS40002043.pdf
  (the `Micorcontroller` spelling is Microchip's own; the URL must keep it)
- Errata:
  https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/Errata/PIC18F274-7Q10-Si-Errata-Data-Sheet-Clarifications-DS80000832.pdf
- Product page: https://www.microchip.com/en-us/product/PIC18F47Q10

## How to use these

- **Check the errata before chasing an odd peripheral behaviour.** Several of this project's
  traps (ADC result width/justification, config-word defaults) are the kind of thing the errata
  and data sheet clarify; the 150C temperature trip in particular was found by reading the ADCC
  chapter, not by guessing.
- The **DFP header** (`PIC18F-Q_DFP/1.30.487/xc8/pic/include/proc/pic18f47q10.h`, resolved by
  `cmake/My_Pic_Project/default/device.cmake`) remains the authority for *register and bit names*.
  The data sheet explains *behaviour*. When the two disagree, the DFP decides what compiles and
  the data sheet decides what it means.
- Do not paraphrase a register description out of these documents into code comments without
  citing the section - a wrong paraphrase is how the `NVMCON1`/`NVMCON0` bit-name mistake in
  `Eeprom-changes.md` happened.

Historical data sheets for parts this project no longer uses (PIC16F18875, PIC16F722A/723A) belong
under `prototype_reference/`, not here.
