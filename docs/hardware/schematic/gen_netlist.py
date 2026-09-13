#!/usr/bin/env python3
"""Generate a KiCad-format netlist (.net, s-expression) for the PicAmpControl
PIC16F18855-I/SP protection controller board with comprehensive input protection
(optocoupler, series resistors, filter caps, dual Schottky clamps, Zener TVS) and
jellybean general-purpose NPN transistor drivers for key outputs (TX, TX_VCC,
TX_BIAS, TRIP, COMP_RESET).

This is hand-authored from the documented design (docs/hardware/PIC16F18855_pin_map.md,
README.md, docs/project-architecture.md) since there is no schematic-capture source.
Connectors J1-J11 provide interconnects to external sub-boards.
"""

import os

# (ref, value, footprint)
components = [
    # Microcontroller & Power
    ("U1", "PIC16F18855-I/SP", "Package_DIP:DIP-28_W7.62mm"),  # SPDIP-28 (300mil/7.62mm row spacing, per "-I/SP" suffix)
    ("U12", "LM7805_TO220", "Package_TO_SOT_THT:TO-220-3_Vertical"),              # Local +5V Linear Regulator
    ("C1", "330nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),                 # 7805 Input Cap
    ("C2", "100nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),                 # 7805 Output Cap
    ("C3", "100nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),
    ("C4", "10uF", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm"),
    ("D7", "BZX84C5V6", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),  # Rail TVS clamp
    ("R1", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # MCLR pull-up

    # Optocoupler Isolation for PTT Input
    ("U2", "PC817", "Package_DIP:DIP-4_W7.62mm"),
    ("R17", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),   # PTT input series 1W
    ("R18", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # Opto collector pull-up
    ("R27", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),   # PTT to MCU series protection
    ("C5", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),                      # PTT filter cap

    # Individual 2-Pin Schottky Clamps (BAT54 / 1N5819: Pin 1=Cathode K, Pin 2=Anode A)
    # Channel 1: SWR1_FWD (D8: GND->Signal, D9: Signal->+5V)
    ("D8", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    ("D9", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    # Channel 2: SWR1_REF
    ("D10", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    ("D11", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    # Channel 3: SWR2_FWD
    ("D12", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    ("D13", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    # Channel 4: SWR2_REF
    ("D14", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    ("D15", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    # Channel 5: TEMP
    ("D16", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    ("D17", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    # Channel 6: CURRENT
    ("D18", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    ("D19", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    # Channel 7: OVERDRIVE
    ("D20", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    ("D21", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    # Channel 8: OC_FAULT
    ("D22", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    ("D23", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    # Channel 9: DRAIN_PEAK
    ("D24", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),
    ("D25", "BAT54", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),

    # Input Series Protection Resistors (1k)
    ("R19", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # SWR1_FWD
    ("R20", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # SWR1_REF
    ("R21", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # SWR2_FWD
    ("R22", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # SWR2_REF
    ("R23", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # TEMP
    ("R24", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # CURRENT
    ("R25", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # OVERDRIVE
    ("R26", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # OC_FAULT
    ("R31", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # DRAIN_PEAK series
    ("R32", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # MENU_ADJUST series
    ("R33", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # MENU_NEXT series

    # Input RC Filter Capacitors
    ("C6", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),   # SWR1_FWD
    ("C7", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),   # SWR1_REF
    ("C8", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),   # SWR2_FWD
    ("C9", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),   # SWR2_REF
    ("C10", "100nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"), # TEMP
    ("C11", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),  # CURRENT
    ("C12", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),  # OVERDRIVE
    ("C13", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),  # OC_FAULT
    ("C14", "100nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"), # DRAIN_PEAK
    ("C15", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),  # MENU_ADJUST
    ("C16", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),  # MENU_NEXT

    # Drain Peak 300V Voltage Divider & Zener Protection
    ("R28", "33k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),   # Top divider 1
    ("R29", "33k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),   # Top divider 2
    ("R30", "33k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),   # Top divider 3
    ("R34", "1.69k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"), # Lower divider
    ("D6", "BZX84C5V1", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),                  # 5.1V Zener

    # Fan MOSFET Driver
    ("R2", "220R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),   # Fan gate series
    ("R3", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),    # Fan gate pull-down
    ("Q1", "IRLZ44N", "Package_TO_SOT_THT:TO-220-3_Vertical"),                           # Fan N-MOSFET
    ("D1", "1N5819", "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal"),                    # Fan Schottky flyback (Pin 1=K, Pin 2=A)

    # Jellybean General Purpose Transistor Output Drivers (2N3904 NPN)
    ("Q2", "2N3904", "Package_TO_SOT_THT:TO-92_Inline"),  # TX Driver
    ("Q3", "2N3904", "Package_TO_SOT_THT:TO-92_Inline"),  # TX_VCC Driver
    ("Q4", "2N3904", "Package_TO_SOT_THT:TO-92_Inline"),  # TX_BIAS Driver
    ("Q5", "2N3904", "Package_TO_SOT_THT:TO-92_Inline"),  # TRIP Driver
    ("Q6", "2N3904", "Package_TO_SOT_THT:TO-92_Inline"),  # COMP_RESET Driver

    # Driver Base Resistors & Pull-Downs
    ("R7", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),   # TX Base R
    ("R8", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # TX Base Pull-Down
    ("R9", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),   # TX_VCC Base R
    ("R10", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"), # TX_VCC Base Pull-Down
    ("R11", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # TX_BIAS Base R
    ("R12", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"), # TX_BIAS Base Pull-Down
    ("R13", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # TRIP Base R
    ("R14", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"), # TRIP Base Pull-Down
    ("R15", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # COMP_RESET Base R
    ("R16", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"), # COMP_RESET Base Pull-Down

    # Relay Output Flyback Diodes (1N4148)
    ("D2", "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),  # TX Flyback
    ("D3", "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),  # TX_VCC Flyback
    ("D4", "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),  # TX_BIAS Flyback
    ("D5", "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"),  # TRIP Flyback

    # User Interface & I2C
    ("SW1", "SW_PUSH", "Button_Switch_THT:SW_PUSH_6mm"),  # MENU_ADJUST
    ("SW2", "SW_PUSH", "Button_Switch_THT:SW_PUSH_6mm"),  # MENU_NEXT
    ("R4", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),  # MENU_NEXT pull-up
    ("R5", "4.7k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"), # I2C SCL pull-up
    ("R6", "4.7k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"), # I2C SDA pull-up

    # Connectors
    ("J1", "Conn_01x04", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"),  # LCD Backpack (GND, 5V, SDA, SCL)
    ("J2", "Conn_01x06", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"),  # Comparator/Sense Board
    ("J3", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"),  # Fan Header
    ("J4", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"),  # PTT In (Isolated: Pin 1=PTT, Pin 2=GND_RET)
    ("J5", "Conn_01x03", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"),  # TX Sequence Outputs
    ("J6", "Conn_01x01", "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical"),  # TRIP Status Output
    ("J7", "Conn_01x03", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"),  # Power In (5V, 12V, GND)
    ("J8", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"),  # SWR1 Bridge
    ("J9", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"),  # SWR2 Bridge
    ("J10", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"), # NTC Temp Sensor
    ("J11", "Conn_01x01", "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical"), # Current Sensor Input
]

# net_name -> [(ref, pin), ...]
nets = {
    "+5V": [
        ("U1", "20"), ("R1", "2"), ("C3", "1"), ("C4", "1"), ("D7", "1"),
        ("U12", "3"), ("C2", "1"),
        ("J1", "2"), ("J2", "5"), ("R4", "2"), ("R5", "2"), ("R6", "2"),
        ("J7", "1"), ("R18", "2"),
        ("D9", "1"), ("D11", "1"), ("D13", "1"), ("D15", "1"), ("D17", "1"),
        ("D19", "1"), ("D21", "1"), ("D23", "1"), ("D25", "1")
    ],
    "GND": [
        ("U1", "8"), ("U1", "19"), ("C3", "2"), ("C4", "2"), ("D7", "2"),
        ("U12", "2"), ("C1", "2"), ("C2", "2"),
        ("SW1", "2"), ("SW2", "2"), ("R3", "2"), ("Q1", "3"),
        ("J1", "1"), ("J2", "6"), ("J7", "3"), ("J10", "2"),
        ("U2", "3"), ("C5", "2"),
        ("D8", "2"), ("D10", "2"), ("D12", "2"), ("D14", "2"), ("D16", "2"),
        ("D18", "2"), ("D20", "2"), ("D22", "2"), ("D24", "2"),
        ("C6", "2"), ("C7", "2"), ("C8", "2"), ("C9", "2"), ("C10", "2"),
        ("C11", "2"), ("C12", "2"), ("C13", "2"), ("C14", "2"), ("C15", "2"), ("C16", "2"),
        ("R34", "2"), ("D6", "2"),
        ("Q2", "1"), ("Q3", "1"), ("Q4", "1"), ("Q5", "1"), ("Q6", "1"),
        ("R8", "2"), ("R10", "2"), ("R12", "2"), ("R14", "2"), ("R16", "2")
    ],
    "+12V_RAIL": [
        ("J7", "2"), ("D1", "1"), ("J3", "1"),
        ("U12", "1"), ("C1", "1"),
        ("D2", "1"), ("D3", "1"), ("D4", "1"), ("D5", "1")
    ],
    "MCLR": [("U1", "1"), ("R1", "1")],

    # Input Signals (Connector -> Series Protection Resistor -> MCU Pin Node)
    "SWR1_FWD_RAW": [("J8", "1"), ("R19", "1")],
    "SWR1_FWD": [("R19", "2"), ("U1", "2"), ("C6", "1"), ("D8", "1"), ("D9", "2")],

    "SWR1_REF_RAW": [("J8", "2"), ("R20", "1")],
    "SWR1_REF": [("R20", "2"), ("U1", "3"), ("C7", "1"), ("D10", "1"), ("D11", "2")],

    "SWR2_FWD_RAW": [("J9", "1"), ("R21", "1")],
    "SWR2_FWD": [("R21", "2"), ("U1", "4"), ("C8", "1"), ("D12", "1"), ("D13", "2")],

    "SWR2_REF_RAW": [("J9", "2"), ("R22", "1")],
    "SWR2_REF": [("R22", "2"), ("U1", "5"), ("C9", "1"), ("D14", "1"), ("D15", "2")],

    "RA4_NC": [("U1", "6")],

    "TEMP_RAW": [("J10", "1"), ("R23", "1")],
    "TEMP": [("R23", "2"), ("U1", "7"), ("C10", "1"), ("D16", "1"), ("D17", "2")],

    "RA6_SPARE": [("U1", "10")],
    "RA7_SPARE": [("U1", "9")],
    "RB6_SPARE": [("U1", "27")],

    "CURRENT_RAW": [("J11", "1"), ("R24", "1")],
    "CURRENT": [("R24", "2"), ("U1", "22"), ("C11", "1"), ("D18", "1"), ("D19", "2")],

    "OVERDRIVE_RAW": [("J2", "1"), ("R25", "1")],
    "OVERDRIVE": [("R25", "2"), ("U1", "23"), ("C12", "1"), ("D20", "1"), ("D21", "2")],

    # Drain Peak Voltage Divider & Protection
    "DRAIN_HIGH_VOLTAGE": [("J2", "2"), ("R28", "1")],
    "DRAIN_DIV_MID1": [("R28", "2"), ("R29", "1")],
    "DRAIN_DIV_MID2": [("R29", "2"), ("R30", "1")],
    "DRAIN_DIV_SCALED": [("R30", "2"), ("R34", "1"), ("D6", "1"), ("R31", "1")],
    "DRAIN_PEAK": [("R31", "2"), ("U1", "24"), ("C14", "1"), ("D24", "1"), ("D25", "2")],

    "OC_FAULT_RAW": [("J2", "3"), ("R26", "1")],
    "OC_FAULT": [("R26", "2"), ("U1", "25"), ("C13", "1"), ("D22", "1"), ("D23", "2")],

    # Switches & Optocoupler PTT
    "MENU_ADJUST_SW": [("SW1", "1"), ("R32", "1")],
    "MENU_ADJUST": [("R32", "2"), ("U1", "21"), ("C15", "1")],

    "MENU_NEXT_SW": [("SW2", "1"), ("R4", "1"), ("R33", "1")],
    "MENU_NEXT": [("R33", "2"), ("U1", "13"), ("C16", "1")],

    "PTT_EXT": [("J4", "1"), ("R17", "1")],
    "PTT_OPTO_ANODE": [("R17", "2"), ("U2", "1")],
    "PTT_OPTO_CATHODE": [("U2", "2"), ("J4", "2")],
    "PTT_OPTO_COLLECTOR": [("U2", "4"), ("R18", "1"), ("R27", "1")],
    "PTT": [("R27", "2"), ("U1", "11"), ("C5", "1")],

    # LCD I2C Bus
    "LCD_SCL": [("U1", "14"), ("J1", "4"), ("R5", "1")],
    "LCD_SDA": [("U1", "15"), ("J1", "3"), ("R6", "1")],

    # Fan PWM Control
    "FAN_PWM": [("U1", "26"), ("R2", "1")],
    "FAN_GATE": [("R2", "2"), ("Q1", "1"), ("R3", "1")],
    "FAN_DRAIN": [("Q1", "2"), ("D1", "2"), ("J3", "2")],

    # Output Transistor Drivers
    "TX_MCU": [("U1", "16"), ("R7", "1")],
    "TX_BASE": [("R7", "2"), ("Q2", "2"), ("R8", "1")],
    "TX": [("Q2", "3"), ("J5", "1"), ("D2", "2")],

    "TX_VCC_MCU": [("U1", "17"), ("R9", "1")],
    "TX_VCC_BASE": [("R9", "2"), ("Q3", "2"), ("R10", "1")],
    "TX_VCC": [("Q3", "3"), ("J5", "2"), ("D3", "2")],

    "TX_BIAS_MCU": [("U1", "18"), ("R11", "1")],
    "TX_BIAS_BASE": [("R11", "2"), ("Q4", "2"), ("R12", "1")],
    "TX_BIAS": [("Q4", "3"), ("J5", "3"), ("D4", "2")],

    "TRIP_MCU": [("U1", "28"), ("R13", "1")],
    "TRIP_BASE": [("R13", "2"), ("Q5", "2"), ("R14", "1")],
    "TRIP": [("Q5", "3"), ("J6", "1"), ("D5", "2")],

    "COMP_RESET_MCU": [("U1", "12"), ("R15", "1")],
    "COMP_RESET_BASE": [("R15", "2"), ("Q6", "2"), ("R16", "1")],
    "COMP_RESET": [("Q6", "3"), ("J2", "4")],
}


def comp_sexpr(ref, value, footprint, idx):
    tstamp = f"{idx:08X}"
    return f'''    (comp (ref "{ref}")
      (value "{value}")
      (footprint "{footprint}")
      (libsource (lib "PicAmpControl") (part "{value}") (description ""))
      (sheetpath (names "/") (tstamps "/"))
      (tstamps "{tstamp}"))'''


def net_sexpr(code, name, nodes):
    node_lines = "\n".join(
        f'      (node (ref "{ref}") (pin "{pin}"))' for ref, pin in nodes
    )
    return f'''    (net (code "{code}") (name "{name}")
{node_lines})'''


def build():
    comp_lines = [
        comp_sexpr(ref, value, footprint, i + 1)
        for i, (ref, value, footprint) in enumerate(components)
    ]
    net_lines = [
        net_sexpr(i + 1, name, nodes) for i, (name, nodes) in enumerate(nets.items())
    ]
    return f'''(export (version "E")
  (design
    (source "PicAmpControl (hand-authored, no schematic-capture source)")
    (date "2026-09-13")
    (tool "PicAmpControl gen_netlist.py")
    (sheet (number "1") (name "/") (tstamps "/")
      (title_block
        (title "PicAmpControl Protection Controller")
        (company "")
        (rev "2")
        (date "2026-09-13")
        (source "PicAmpControl")
        (comment (number "1") (value "Includes input protection & 2N3904 transistor output drivers")))))
  (components
{chr(10).join(comp_lines)})
  (libparts)
  (libraries)
  (nets
{chr(10).join(net_lines)}))
'''


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.realpath(__file__))
    out_file = os.path.join(script_dir, "PicAmpControl.net")
    text = build()
    with open(out_file, "w") as f:
        f.write(text)
    print(f"wrote {out_file}: {len(components)} components, {len(nets)} nets")

