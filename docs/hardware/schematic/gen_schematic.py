#!/usr/bin/env python3
"""Generate a KiCad 6+ schematic (.kicad_sch) for PicAmpControl.

This allows importing directly into EasyEDA Pro via File -> Import -> KiCad...
as a Schematic diagram, complete with symbols, properties, footprints, net labels,
and organized layout blocks.
"""

import os
import uuid

def gen_uuid(seed_str):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed_str))

# Define components with positions on grid (in mm)
# Block 1: MCU U1 at center (150, 100)
# Block 2: Power & Bypass C3, C4, D7, R1 at top-left (50, 40)
# Block 3: Optocoupler PTT U2, R17, R18, R27, C5 at left (50, 90)
# Block 4: User Switches SW1, SW2, R4, R32, R33, C15, C16 at top-right (230, 40)
# Block 5: I2C Pullups R5, R6 at top-center (150, 40)
# Block 6: Analog Protection Clamps & Filters (SWR1, SWR2, Temp, Current, Overdrive, OC) at left/bottom (50, 150)
# Block 7: High Voltage Drain Divider R28, R29, R30, R34, D6, R31, C14 at bottom-center (150, 180)
# Block 8: Fan MOSFET Driver Q1, R2, R3, D1 at bottom-right (230, 100)
# Block 9: NPN Output Drivers Q2..Q6, R7..R16, D2..D5 at bottom-right (230, 160)
# Connectors J1..J11 placed neatly along edges

components_layout = [
    # Ref, Value, Footprint, X, Y, LibSymbol
    ("U1", "PIC16F18855-I/SP", "Package_DIP:DIP-28_W7.62mm", 150, 110, "MCU_Microchip_PIC:PIC16F18855-I_SP"),
    
    # Power & Reset
    ("R1", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 110, 60, "Device:R"),
    ("C3", "100nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 120, 60, "Device:C"),
    ("C4", "10uF", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", 130, 60, "Device:C_Polarized"),
    ("D7", "BZX84C5V6", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", 140, 60, "Device:D_Zener"),

    # PTT Optocoupler
    ("U2", "PC817", "Package_DIP:DIP-4_W7.62mm", 50, 90, "Isolator:PC817"),
    ("R17", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 30, 90, "Device:R"),
    ("R18", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 65, 80, "Device:R"),
    ("R27", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 80, 90, "Device:R"),
    ("C5", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 95, 95, "Device:C"),

    # Switches
    ("SW1", "SW_PUSH", "Button_Switch_THT:SW_PUSH_6mm", 210, 40, "Switch:SW_Push"),
    ("SW2", "SW_PUSH", "Button_Switch_THT:SW_PUSH_6mm", 210, 60, "Switch:SW_Push"),
    ("R4", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 225, 55, "Device:R"),
    ("R32", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 195, 40, "Device:R"),
    ("R33", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 195, 60, "Device:R"),
    ("C15", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 180, 45, "Device:C"),
    ("C16", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 180, 65, "Device:C"),

    # I2C Pullups
    ("R5", "4.7k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 160, 40, "Device:R"),
    ("R6", "4.7k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 170, 40, "Device:R"),

    # Analog Clamps & Filters
    ("U3", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 75, 120, "Device:D_Schottky_x2_KA_AK"),
    ("R19", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 50, 120, "Device:R"),
    ("C6", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 85, 125, "Device:C"),

    ("U4", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 75, 135, "Device:D_Schottky_x2_KA_AK"),
    ("R20", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 50, 135, "Device:R"),
    ("C7", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 85, 140, "Device:C"),

    ("U5", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 75, 150, "Device:D_Schottky_x2_KA_AK"),
    ("R21", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 50, 150, "Device:R"),
    ("C8", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 85, 155, "Device:C"),

    ("U6", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 75, 165, "Device:D_Schottky_x2_KA_AK"),
    ("R22", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 50, 165, "Device:R"),
    ("C9", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 85, 170, "Device:C"),

    ("U7", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 75, 180, "Device:D_Schottky_x2_KA_AK"),
    ("R23", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 50, 180, "Device:R"),
    ("C10", "100nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 85, 185, "Device:C"),

    ("U8", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 75, 195, "Device:D_Schottky_x2_KA_AK"),
    ("R24", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 50, 195, "Device:R"),
    ("C11", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 85, 200, "Device:C"),

    ("U9", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 75, 210, "Device:D_Schottky_x2_KA_AK"),
    ("R25", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 50, 210, "Device:R"),
    ("C12", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 85, 215, "Device:C"),

    ("U10", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 75, 225, "Device:D_Schottky_x2_KA_AK"),
    ("R26", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 50, 225, "Device:R"),
    ("C13", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 85, 230, "Device:C"),

    # Drain Peak Voltage Divider
    ("R28", "33k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 110, 240, "Device:R"),
    ("R29", "33k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 125, 240, "Device:R"),
    ("R30", "33k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 140, 240, "Device:R"),
    ("R34", "1.69k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 155, 250, "Device:R"),
    ("D6", "BZX84C5V1", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", 165, 250, "Device:D_Zener"),
    ("R31", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 175, 240, "Device:R"),
    ("U11", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 190, 240, "Device:D_Schottky_x2_KA_AK"),
    ("C14", "100nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 200, 245, "Device:C"),

    # Fan Driver
    ("R2", "220R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 210, 100, "Device:R"),
    ("R3", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 225, 105, "Device:R"),
    ("Q1", "IRLZ44N", "Package_TO_SOT_THT:TO-220-3_Vertical", 240, 100, "Transistor_FET:IRLZ44N"),
    ("D1", "1N5819", "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal", 255, 100, "Device:D_Schottky"),

    # NPN Output Drivers
    ("Q2", "2N3904", "Package_TO_SOT_THT:TO-92_Inline", 230, 140, "Transistor_BJT:2N3904"),
    ("R7", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 210, 140, "Device:R"),
    ("R8", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 220, 145, "Device:R"),
    ("D2", "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", 245, 140, "Device:D"),

    ("Q3", "2N3904", "Package_TO_SOT_THT:TO-92_Inline", 230, 160, "Transistor_BJT:2N3904"),
    ("R9", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 210, 160, "Device:R"),
    ("R10", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 220, 165, "Device:R"),
    ("D3", "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", 245, 160, "Device:D"),

    ("Q4", "2N3904", "Package_TO_SOT_THT:TO-92_Inline", 230, 180, "Transistor_BJT:2N3904"),
    ("R11", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 210, 180, "Device:R"),
    ("R12", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 220, 185, "Device:R"),
    ("D4", "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", 245, 180, "Device:D"),

    ("Q5", "2N3904", "Package_TO_SOT_THT:TO-92_Inline", 230, 200, "Transistor_BJT:2N3904"),
    ("R13", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 210, 200, "Device:R"),
    ("R14", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 220, 205, "Device:R"),
    ("D5", "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", 245, 200, "Device:D"),

    ("Q6", "2N3904", "Package_TO_SOT_THT:TO-92_Inline", 230, 220, "Transistor_BJT:2N3904"),
    ("R15", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 210, 220, "Device:R"),
    ("R16", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 220, 225, "Device:R"),

    # Connectors
    ("J1", "Conn_01x04", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", 170, 25, "Connector:Conn_01x04_Pin"),
    ("J2", "Conn_01x06", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical", 25, 210, "Connector:Conn_01x06_Pin"),
    ("J3", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 270, 100, "Connector:Conn_01x02_Pin"),
    ("J4", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 15, 90, "Connector:Conn_01x02_Pin"),
    ("J5", "Conn_01x03", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", 270, 160, "Connector:Conn_01x03_Pin"),
    ("J6", "Conn_01x01", "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical", 270, 200, "Connector:Conn_01x01_Pin"),
    ("J7", "Conn_01x03", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", 100, 25, "Connector:Conn_01x03_Pin"),
    ("J8", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 25, 125, "Connector:Conn_01x02_Pin"),
    ("J9", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 25, 155, "Connector:Conn_01x02_Pin"),
    ("J10", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 25, 180, "Connector:Conn_01x02_Pin"),
    ("J11", "Conn_01x01", "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical", 25, 195, "Connector:Conn_01x01_Pin"),
]

# Net connections with explicit net labels
net_labels = [
    ("+5V", 120, 30),
    ("GND", 120, 270),
    ("+12V_RAIL", 260, 30),
    ("SWR1_FWD", 100, 120),
    ("SWR1_REF", 100, 135),
    ("SWR2_FWD", 100, 150),
    ("SWR2_REF", 100, 165),
    ("TEMP", 100, 180),
    ("CURRENT", 100, 195),
    ("OVERDRIVE", 100, 210),
    ("OC_FAULT", 100, 225),
    ("DRAIN_PEAK", 205, 240),
    ("MENU_ADJUST", 175, 40),
    ("MENU_NEXT", 175, 60),
    ("PTT", 100, 90),
    ("LCD_SCL", 155, 30),
    ("LCD_SDA", 165, 30),
    ("FAN_PWM", 200, 100),
    ("TX_MCU", 200, 140),
    ("TX_VCC_MCU", 200, 160),
    ("TX_BIAS_MCU", 200, 180),
    ("TRIP_MCU", 200, 200),
    ("COMP_RESET_MCU", 200, 220),
]

def build_lib_symbols():
    """Build embedded (lib_symbols ...) section containing graphical symbol definitions."""
    mcu_pins = [
        ("1", "MCLR/VPP", "input"),
        ("2", "RA0/AN0", "bidirectional"),
        ("3", "RA1/AN1", "bidirectional"),
        ("4", "RA2/AN2", "bidirectional"),
        ("5", "RA3/AN3", "bidirectional"),
        ("6", "RA4", "bidirectional"),
        ("7", "RA5/AN5", "bidirectional"),
        ("8", "VSS", "power_in"),
        ("9", "RA6", "bidirectional"),
        ("10", "RA7", "bidirectional"),
        ("11", "VDD", "power_in"),
        ("12", "RB0", "bidirectional"),
        ("13", "RB1/AN9", "bidirectional"),
        ("14", "RB2/AN10", "bidirectional"),
        ("15", "RB3/AN11", "bidirectional"),
        ("16", "RB4", "bidirectional"),
        ("17", "RB5", "bidirectional"),
        ("18", "RB6", "bidirectional"),
        ("19", "RB7", "bidirectional"),
        ("20", "VSS", "power_in"),
        ("21", "RC0", "bidirectional"),
        ("22", "RC1", "bidirectional"),
        ("23", "RC2", "bidirectional"),
        ("24", "RC3/SCL", "bidirectional"),
        ("25", "RC4/SDA", "bidirectional"),
        ("26", "RC5", "bidirectional"),
        ("27", "RC6", "bidirectional"),
        ("28", "RC7", "bidirectional"),
    ]

    mcu_pin_lines = []
    for i in range(14):
        pnum, pname, ptype = mcu_pins[i]
        y_pos = 17.78 - (i * 2.54)
        mcu_pin_lines.append(f'      (pin {ptype} line (at -15.24 {y_pos:.2f} 0) (length 2.54) (name "{pname}" (effects (font (size 1.27 1.27)))) (number "{pnum}" (effects (font (size 1.27 1.27)))))')

    for i in range(14):
        pnum, pname, ptype = mcu_pins[14 + i]
        y_pos = -15.24 + (i * 2.54)
        mcu_pin_lines.append(f'      (pin {ptype} line (at 15.24 {y_pos:.2f} 180) (length 2.54) (name "{pname}" (effects (font (size 1.27 1.27)))) (number "{pnum}" (effects (font (size 1.27 1.27)))))')

    mcu_pins_str = "\n".join(mcu_pin_lines)

    def gen_conn_pins(count):
        lines = []
        for i in range(count):
            y = (count - 1) * 1.27 - i * 2.54
            lines.append(f'      (pin passive line (at -5.08 {y:.2f} 0) (length 2.54) (name "Pin_{i+1}" (effects (font (size 1.27 1.27)))) (number "{i+1}" (effects (font (size 1.27 1.27)))))')
        return "\n".join(lines)

    return f'''  (lib_symbols
    (symbol "Regulator_Linear:LM7805_TO220" (in_bom yes) (on_board yes)
      (property "Reference" "U" (id 0) (at 0 6.35 0) (effects (font (size 1.27 1.27))))
      (property "Value" "LM7805_TO220" (id 1) (at 0 -6.35 0) (effects (font (size 1.27 1.27))))
      (symbol "LM7805_TO220_0_1"
        (rectangle (start -6.35 5.08) (end 6.35 -5.08) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin input line (at -8.89 0 0) (length 2.54) (name "VI" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin power_in line (at 0 -7.62 90) (length 2.54) (name "GND" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin power_out line (at 8.89 0 180) (length 2.54) (name "VO" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "MCU_Microchip_PIC:PIC16F18855-I_SP" (in_bom yes) (on_board yes)
      (symbol "PIC16F18855-I_SP_0_1"
        (rectangle (start -12.7 20.32) (end 12.7 -17.78) (stroke (width 0.254) (type default)) (fill (type background)))
{mcu_pins_str}
      )
    )
    (symbol "Device:R" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (symbol "R_0_1"
        (rectangle (start -1.016 2.54) (end 1.016 -2.54) (stroke (width 0.254) (type default)) (fill (type none)))
        (pin passive line (at 0 5.08 270) (length 2.54) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -5.08 90) (length 2.54) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:C" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (symbol "C_0_1"
        (polyline (pts (xy -2.54 0.635) (xy 2.54 0.635)) (stroke (width 0.508) (type default)))
        (polyline (pts (xy -2.54 -0.635) (xy 2.54 -0.635)) (stroke (width 0.508) (type default)))
        (pin passive line (at 0 3.81 270) (length 3.175) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 3.175) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:C_Polarized" (pin_names hide) (in_bom yes) (on_board yes)
      (symbol "C_Polarized_0_1"
        (polyline (pts (xy -2.54 0.635) (xy 2.54 0.635)) (stroke (width 0.508) (type default)))
        (polyline (pts (xy -2.54 -0.635) (xy 2.54 -0.635)) (stroke (width 0.508) (type default)))
        (pin passive line (at 0 3.81 270) (length 3.175) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -3.81 90) (length 3.175) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:D" (pin_names hide) (in_bom yes) (on_board yes)
      (symbol "D_0_1"
        (polyline (pts (xy -1.27 1.27) (xy -1.27 -1.27) (xy 1.27 0) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 1.27) (xy 1.27 -1.27)) (stroke (width 0.254) (type default)))
        (pin passive line (at -3.81 0 0) (length 2.54) (name "K" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 3.81 0 180) (length 2.54) (name "A" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:D_Zener" (pin_names hide) (in_bom yes) (on_board yes)
      (symbol "D_Zener_0_1"
        (polyline (pts (xy -1.27 1.27) (xy -1.27 -1.27) (xy 1.27 0) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 1.27) (xy 1.27 -1.27)) (stroke (width 0.254) (type default)))
        (pin passive line (at -3.81 0 0) (length 2.54) (name "K" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 3.81 0 180) (length 2.54) (name "A" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:D_Schottky" (pin_names hide) (in_bom yes) (on_board yes)
      (symbol "D_Schottky_0_1"
        (polyline (pts (xy -1.27 1.27) (xy -1.27 -1.27) (xy 1.27 0) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 1.27) (xy 1.27 -1.27)) (stroke (width 0.254) (type default)))
        (pin passive line (at -3.81 0 0) (length 2.54) (name "K" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 3.81 0 180) (length 2.54) (name "A" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:D_Schottky_x2_KA_AK" (in_bom yes) (on_board yes)
      (symbol "D_Schottky_x2_KA_AK_0_1"
        (rectangle (start -5.08 5.08) (end 5.08 -5.08) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin passive line (at -7.62 2.54 0) (length 2.54) (name "A1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -7.62 -2.54 0) (length 2.54) (name "K2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 7.62 0 180) (length 2.54) (name "K1A2" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Isolator:PC817" (in_bom yes) (on_board yes)
      (symbol "PC817_0_1"
        (rectangle (start -7.62 5.08) (end 7.62 -5.08) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin passive line (at -10.16 2.54 0) (length 2.54) (name "A" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -10.16 -2.54 0) (length 2.54) (name "K" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 10.16 -2.54 180) (length 2.54) (name "E" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 10.16 2.54 180) (length 2.54) (name "C" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Switch:SW_Push" (pin_names hide) (in_bom yes) (on_board yes)
      (symbol "SW_Push_0_1"
        (circle (center -1.27 0) (radius 0.635) (stroke (width 0.254) (type default)) (fill (type none)))
        (circle (center 1.27 0) (radius 0.635) (stroke (width 0.254) (type default)) (fill (type none)))
        (pin passive line (at -3.81 0 0) (length 2.54) (name "1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 3.81 0 180) (length 2.54) (name "2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Transistor_FET:IRLZ44N" (in_bom yes) (on_board yes)
      (symbol "IRLZ44N_0_1"
        (polyline (pts (xy 0 2.54) (xy 0 -2.54)) (stroke (width 0.508) (type default)))
        (pin input line (at -5.08 -1.27 0) (length 3.81) (name "G" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 2.54 5.08 270) (length 2.54) (name "D" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 2.54 -5.08 90) (length 2.54) (name "S" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Transistor_BJT:2N3904" (in_bom yes) (on_board yes)
      (symbol "2N3904_0_1"
        (polyline (pts (xy 0 2.54) (xy 0 -2.54)) (stroke (width 0.508) (type default)))
        (pin passive line (at 2.54 -5.08 90) (length 2.54) (name "E" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin input line (at -5.08 0 0) (length 3.81) (name "B" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 2.54 5.08 270) (length 2.54) (name "C" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Connector:Conn_01x01_Pin" (in_bom yes) (on_board yes)
      (symbol "Conn_01x01_Pin_0_1"
        (rectangle (start -2.54 2.54) (end 2.54 -2.54) (stroke (width 0.254) (type default)) (fill (type background)))
{gen_conn_pins(1)}
      )
    )
    (symbol "Connector:Conn_01x02_Pin" (in_bom yes) (on_board yes)
      (symbol "Conn_01x02_Pin_0_1"
        (rectangle (start -2.54 3.81) (end 2.54 -3.81) (stroke (width 0.254) (type default)) (fill (type background)))
{gen_conn_pins(2)}
      )
    )
    (symbol "Connector:Conn_01x03_Pin" (in_bom yes) (on_board yes)
      (symbol "Conn_01x03_Pin_0_1"
        (rectangle (start -2.54 5.08) (end 2.54 -5.08) (stroke (width 0.254) (type default)) (fill (type background)))
{gen_conn_pins(3)}
      )
    )
    (symbol "Connector:Conn_01x04_Pin" (in_bom yes) (on_board yes)
      (symbol "Conn_01x04_Pin_0_1"
        (rectangle (start -2.54 6.35) (end 2.54 -6.35) (stroke (width 0.254) (type default)) (fill (type background)))
{gen_conn_pins(4)}
      )
    )
    (symbol "Connector:Conn_01x06_Pin" (in_bom yes) (on_board yes)
      (symbol "Conn_01x06_Pin_0_1"
        (rectangle (start -2.54 8.89) (end 2.54 -8.89) (stroke (width 0.254) (type default)) (fill (type background)))
{gen_conn_pins(6)}
      )
    )
  )'''

def build_kicad_sch():
    u_str = lambda s: gen_uuid(s)

    lines = []
    lines.append('(kicad_sch (version 20231120) (generator "PicAmpControl gen_schematic.py")')
    lines.append(f'  (uuid "{u_str("root")}")')
    lines.append('  (paper "A2")')
    lines.append('  (title_block')
    lines.append('    (title "PicAmpControl Protection Controller")')
    lines.append('    (date "2026-09-13")')
    lines.append('    (rev "2")')
    lines.append('    (comment 1 "Includes Input Protection & NPN Drivers")')
    lines.append('  )')
    lines.append('')
    lines.append(build_lib_symbols())
    lines.append('')

    #!/usr/bin/env python3
"""Generate a complete, fully-wired KiCad 6+ schematic (.kicad_sch) for PicAmpControl.

Features:
1. Complete embedded lib_symbols with proper default Reference/Value properties.
2. Complete pin UUID mapping in symbol instances so component references (U1, R1, C3, Q1, D1, etc.) render clearly instead of "U?".
3. Explicit wires (wire ...) connecting component pins directly to net labels, power symbols (+5V, GND, +12V_RAIL), and neighboring components.
"""

import os
import uuid

def gen_uuid(seed_str):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed_str))

# (ref, val, footprint, x, y, lib_sym, pref, pins_dict)
# Pins dict maps pin_number -> net_name

components_data = [
    # MCU U1 at (150, 150)
    ("U1", "PIC16F18855-I/SP", "Package_DIP:DIP-28_W7.62mm", 150, 150, "MCU_Microchip_PIC:PIC16F18855-I_SP", "U", {
        "1": "MCLR", "2": "SWR1_FWD", "3": "SWR1_REF", "4": "SWR2_FWD", "5": "SWR2_REF",
        "6": "NC", "7": "TEMP", "8": "GND", "9": "NC", "10": "NC", "11": "+5V",
        "12": "MENU_ADJUST", "13": "CURRENT", "14": "OVERDRIVE", "15": "DRAIN_PEAK",
        "16": "OC_FAULT", "17": "FAN_PWM", "18": "NC", "19": "TRIP_MCU", "20": "GND",
        "21": "PTT", "22": "COMP_RESET_MCU", "23": "MENU_NEXT", "24": "LCD_SCL",
        "25": "LCD_SDA", "26": "TX_MCU", "27": "TX_VCC_MCU", "28": "TX_BIAS_MCU"
    }),

    # Power & Decoupling at MCU
    ("U12", "LM7805_TO220", "Package_TO_SOT_THT:TO-220-3_Vertical", 90, 60, "Regulator_Linear:LM7805_TO220", "U", {"1": "+12V_RAIL", "2": "GND", "3": "+5V"}),
    ("C1", "330nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 75, 60, "Device:C", "C", {"1": "+12V_RAIL", "2": "GND"}),
    ("C2", "100nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 105, 60, "Device:C", "C", {"1": "+5V", "2": "GND"}),
    ("R1", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 120, 100, "Device:R", "R", {"1": "+5V", "2": "MCLR"}),
    ("C3", "100nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 130, 100, "Device:C", "C", {"1": "+5V", "2": "GND"}),
    ("C4", "10uF", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", 140, 100, "Device:C_Polarized", "C", {"1": "+5V", "2": "GND"}),
    ("D7", "BZX84C5V6", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", 150, 100, "Device:D_Zener", "D", {"1": "+5V", "2": "GND"}),

    # PTT Optocoupler Block
    ("R17", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 30, 80, "Device:R", "R", {"1": "PTT_EXT", "2": "PTT_ANODE"}),
    ("U2", "PC817", "Package_DIP:DIP-4_W7.62mm", 50, 80, "Isolator:PC817", "U", {"1": "PTT_ANODE", "2": "PTT_CATHODE", "3": "GND", "4": "PTT_COLLECTOR"}),
    ("R18", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 70, 70, "Device:R", "R", {"1": "+5V", "2": "PTT_COLLECTOR"}),
    ("R27", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 85, 80, "Device:R", "R", {"1": "PTT_COLLECTOR", "2": "PTT"}),
    ("C5", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 100, 90, "Device:C", "C", {"1": "PTT", "2": "GND"}),

    # Analog Input Channels (SWR1_FWD, SWR1_REF, SWR2_FWD, SWR2_REF, TEMP, CURRENT, OVERDRIVE, OC_FAULT)
    # Channel 1: SWR1_FWD
    ("R19", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 30, 120, "Device:R", "R", {"1": "SWR1_FWD_RAW", "2": "SWR1_FWD"}),
    ("U3", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 55, 120, "Device:D_Schottky_x2_KA_AK", "U", {"1": "GND", "2": "+5V", "3": "SWR1_FWD"}),
    ("C6", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 75, 125, "Device:C", "C", {"1": "SWR1_FWD", "2": "GND"}),

    # Channel 2: SWR1_REF
    ("R20", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 30, 140, "Device:R", "R", {"1": "SWR1_REF_RAW", "2": "SWR1_REF"}),
    ("U4", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 55, 140, "Device:D_Schottky_x2_KA_AK", "U", {"1": "GND", "2": "+5V", "3": "SWR1_REF"}),
    ("C7", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 75, 145, "Device:C", "C", {"1": "SWR1_REF", "2": "GND"}),

    # Channel 3: SWR2_FWD
    ("R21", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 30, 160, "Device:R", "R", {"1": "SWR2_FWD_RAW", "2": "SWR2_FWD"}),
    ("U5", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 55, 160, "Device:D_Schottky_x2_KA_AK", "U", {"1": "GND", "2": "+5V", "3": "SWR2_FWD"}),
    ("C8", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 75, 165, "Device:C", "C", {"1": "SWR2_FWD", "2": "GND"}),

    # Channel 4: SWR2_REF
    ("R22", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 30, 180, "Device:R", "R", {"1": "SWR2_REF_RAW", "2": "SWR2_REF"}),
    ("U6", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 55, 180, "Device:D_Schottky_x2_KA_AK", "U", {"1": "GND", "2": "+5V", "3": "SWR2_REF"}),
    ("C9", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 75, 185, "Device:C", "C", {"1": "SWR2_REF", "2": "GND"}),

    # Channel 5: TEMP
    ("R23", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 30, 200, "Device:R", "R", {"1": "TEMP_RAW", "2": "TEMP"}),
    ("U7", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 55, 200, "Device:D_Schottky_x2_KA_AK", "U", {"1": "GND", "2": "+5V", "3": "TEMP"}),
    ("C10", "100nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 75, 205, "Device:C", "C", {"1": "TEMP", "2": "GND"}),

    # Channel 6: CURRENT
    ("R24", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 30, 220, "Device:R", "R", {"1": "CURRENT_RAW", "2": "CURRENT"}),
    ("U8", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 55, 220, "Device:D_Schottky_x2_KA_AK", "U", {"1": "GND", "2": "+5V", "3": "CURRENT"}),
    ("C11", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 75, 225, "Device:C", "C", {"1": "CURRENT", "2": "GND"}),

    # Channel 7: OVERDRIVE
    ("R25", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 30, 240, "Device:R", "R", {"1": "OVERDRIVE_RAW", "2": "OVERDRIVE"}),
    ("U9", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 55, 240, "Device:D_Schottky_x2_KA_AK", "U", {"1": "GND", "2": "+5V", "3": "OVERDRIVE"}),
    ("C12", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 75, 245, "Device:C", "C", {"1": "OVERDRIVE", "2": "GND"}),

    # Channel 8: OC_FAULT
    ("R26", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 30, 260, "Device:R", "R", {"1": "OC_FAULT_RAW", "2": "OC_FAULT"}),
    ("U10", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 55, 260, "Device:D_Schottky_x2_KA_AK", "U", {"1": "GND", "2": "+5V", "3": "OC_FAULT"}),
    ("C13", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 75, 265, "Device:C", "C", {"1": "OC_FAULT", "2": "GND"}),

    # Drain Peak 300V Voltage Divider Block
    ("R28", "33k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 110, 260, "Device:R", "R", {"1": "DRAIN_HV", "2": "DRAIN_MID1"}),
    ("R29", "33k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 125, 260, "Device:R", "R", {"1": "DRAIN_MID1", "2": "DRAIN_MID2"}),
    ("R30", "33k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 140, 260, "Device:R", "R", {"1": "DRAIN_MID2", "2": "DRAIN_SCALED"}),
    ("R34", "1.69k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 155, 270, "Device:R", "R", {"1": "DRAIN_SCALED", "2": "GND"}),
    ("D6", "BZX84C5V1", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", 165, 270, "Device:D_Zener", "D", {"1": "DRAIN_SCALED", "2": "GND"}),
    ("R31", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 175, 260, "Device:R", "R", {"1": "DRAIN_SCALED", "2": "DRAIN_PEAK"}),
    ("U11", "BAT54S", "Package_TO_SOT_SMD:SOT-23", 195, 260, "Device:D_Schottky_x2_KA_AK", "U", {"1": "GND", "2": "+5V", "3": "DRAIN_PEAK"}),
    ("C14", "100nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 210, 265, "Device:C", "C", {"1": "DRAIN_PEAK", "2": "GND"}),

    # User Interface Switches
    ("SW1", "SW_PUSH", "Button_Switch_THT:SW_PUSH_6mm", 190, 50, "Switch:SW_Push", "SW", {"1": "SW1_NODE", "2": "GND"}),
    ("R32", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 175, 50, "Device:R", "R", {"1": "SW1_NODE", "2": "MENU_ADJUST"}),
    ("C15", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 160, 55, "Device:C", "C", {"1": "MENU_ADJUST", "2": "GND"}),

    ("SW2", "SW_PUSH", "Button_Switch_THT:SW_PUSH_6mm", 190, 80, "Switch:SW_Push", "SW", {"1": "SW2_NODE", "2": "GND"}),
    ("R4", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 205, 80, "Device:R", "R", {"1": "+5V", "2": "SW2_NODE"}),
    ("R33", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 175, 80, "Device:R", "R", {"1": "SW2_NODE", "2": "MENU_NEXT"}),
    ("C16", "10nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm", 160, 85, "Device:C", "C", {"1": "MENU_NEXT", "2": "GND"}),

    # I2C Bus Pullups
    ("R5", "4.7k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 190, 110, "Device:R", "R", {"1": "+5V", "2": "LCD_SCL"}),
    ("R6", "4.7k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 200, 110, "Device:R", "R", {"1": "+5V", "2": "LCD_SDA"}),

    # Fan MOSFET Driver Block
    ("R2", "220R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 210, 140, "Device:R", "R", {"1": "FAN_PWM", "2": "FAN_GATE"}),
    ("R3", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 225, 145, "Device:R", "R", {"1": "FAN_GATE", "2": "GND"}),
    ("Q1", "IRLZ44N", "Package_TO_SOT_THT:TO-220-3_Vertical", 240, 140, "Transistor_FET:IRLZ44N", "Q", {"1": "FAN_GATE", "2": "FAN_DRAIN", "3": "GND"}),
    ("D1", "1N5819", "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal", 255, 140, "Device:D_Schottky", "D", {"1": "+12V_RAIL", "2": "FAN_DRAIN"}),

    # Output Transistor Drivers (Q2..Q6)
    ("R7", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 205, 170, "Device:R", "R", {"1": "TX_MCU", "2": "TX_BASE"}),
    ("R8", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 220, 175, "Device:R", "R", {"1": "TX_BASE", "2": "GND"}),
    ("Q2", "2N3904", "Package_TO_SOT_THT:TO-92_Inline", 230, 170, "Transistor_BJT:2N3904", "Q", {"1": "GND", "2": "TX_BASE", "3": "TX"}),
    ("D2", "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", 245, 170, "Device:D", "D", {"1": "+12V_RAIL", "2": "TX"}),

    ("R9", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 205, 190, "Device:R", "R", {"1": "TX_VCC_MCU", "2": "TX_VCC_BASE"}),
    ("R10", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 220, 195, "Device:R", "R", {"1": "TX_VCC_BASE", "2": "GND"}),
    ("Q3", "2N3904", "Package_TO_SOT_THT:TO-92_Inline", 230, 190, "Transistor_BJT:2N3904", "Q", {"1": "GND", "2": "TX_VCC_BASE", "3": "TX_VCC"}),
    ("D3", "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", 245, 190, "Device:D", "D", {"1": "+12V_RAIL", "2": "TX_VCC"}),

    ("R11", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 205, 210, "Device:R", "R", {"1": "TX_BIAS_MCU", "2": "TX_BIAS_BASE"}),
    ("R12", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 220, 215, "Device:R", "R", {"1": "TX_BIAS_BASE", "2": "GND"}),
    ("Q4", "2N3904", "Package_TO_SOT_THT:TO-92_Inline", 230, 210, "Transistor_BJT:2N3904", "Q", {"1": "GND", "2": "TX_BIAS_BASE", "3": "TX_BIAS"}),
    ("D4", "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", 245, 210, "Device:D", "D", {"1": "+12V_RAIL", "2": "TX_BIAS"}),

    ("R13", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 205, 230, "Device:R", "R", {"1": "TRIP_MCU", "2": "TRIP_BASE"}),
    ("R14", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 220, 235, "Device:R", "R", {"1": "TRIP_BASE", "2": "GND"}),
    ("Q5", "2N3904", "Package_TO_SOT_THT:TO-92_Inline", 230, 230, "Transistor_BJT:2N3904", "Q", {"1": "GND", "2": "TRIP_BASE", "3": "TRIP"}),
    ("D5", "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal", 245, 230, "Device:D", "D", {"1": "+12V_RAIL", "2": "TRIP"}),

    ("R15", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 205, 250, "Device:R", "R", {"1": "COMP_RESET_MCU", "2": "COMP_RESET_BASE"}),
    ("R16", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 220, 255, "Device:R", "R", {"1": "COMP_RESET_BASE", "2": "GND"}),
    ("Q6", "2N3904", "Package_TO_SOT_THT:TO-92_Inline", 230, 250, "Transistor_BJT:2N3904", "Q", {"1": "GND", "2": "COMP_RESET_BASE", "3": "COMP_RESET"}),

    # Connectors
    ("J1", "Conn_01x04", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", 215, 110, "Connector:Conn_01x04_Pin", "J", {"1": "GND", "2": "+5V", "3": "LCD_SDA", "4": "LCD_SCL"}),
    ("J2", "Conn_01x06", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical", 10, 230, "Connector:Conn_01x06_Pin", "J", {"1": "OVERDRIVE_RAW", "2": "DRAIN_HV", "3": "OC_FAULT_RAW", "4": "COMP_RESET", "5": "+5V", "6": "GND"}),
    ("J3", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 270, 140, "Connector:Conn_01x02_Pin", "J", {"1": "+12V_RAIL", "2": "FAN_DRAIN"}),
    ("J4", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 10, 80, "Connector:Conn_01x02_Pin", "J", {"1": "PTT_EXT", "2": "PTT_CATHODE"}),
    ("J5", "Conn_01x03", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", 270, 180, "Connector:Conn_01x03_Pin", "J", {"1": "TX", "2": "TX_VCC", "3": "TX_BIAS"}),
    ("J6", "Conn_01x01", "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical", 270, 230, "Connector:Conn_01x01_Pin", "J", {"1": "TRIP"}),
    ("J7", "Conn_01x03", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", 100, 40, "Connector:Conn_01x03_Pin", "J", {"1": "+5V", "2": "+12V_RAIL", "3": "GND"}),
    ("J8", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 10, 130, "Connector:Conn_01x02_Pin", "J", {"1": "SWR1_FWD_RAW", "2": "SWR1_REF_RAW"}),
    ("J9", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 10, 170, "Connector:Conn_01x02_Pin", "J", {"1": "SWR2_FWD_RAW", "2": "SWR2_REF_RAW"}),
    ("J10", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", 10, 200, "Connector:Conn_01x02_Pin", "J", {"1": "TEMP_RAW", "2": "GND"}),
    ("J11", "Conn_01x01", "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical", 10, 220, "Connector:Conn_01x01_Pin", "J", {"1": "CURRENT_RAW"}),
]

def build_lib_symbols():
    mcu_pins = [
        ("1", "MCLR/VPP", "input"),
        ("2", "RA0/AN0", "bidirectional"),
        ("3", "RA1/AN1", "bidirectional"),
        ("4", "RA2/AN2", "bidirectional"),
        ("5", "RA3/AN3", "bidirectional"),
        ("6", "RA4", "bidirectional"),
        ("7", "RA5/AN5", "bidirectional"),
        ("8", "VSS", "power_in"),
        ("9", "RA6", "bidirectional"),
        ("10", "RA7", "bidirectional"),
        ("11", "VDD", "power_in"),
        ("12", "RB0", "bidirectional"),
        ("13", "RB1/AN9", "bidirectional"),
        ("14", "RB2/AN10", "bidirectional"),
        ("15", "RB3/AN11", "bidirectional"),
        ("16", "RB4", "bidirectional"),
        ("17", "RB5", "bidirectional"),
        ("18", "RB6", "bidirectional"),
        ("19", "RB7", "bidirectional"),
        ("20", "VSS", "power_in"),
        ("21", "RC0", "bidirectional"),
        ("22", "RC1", "bidirectional"),
        ("23", "RC2", "bidirectional"),
        ("24", "RC3/SCL", "bidirectional"),
        ("25", "RC4/SDA", "bidirectional"),
        ("26", "RC5", "bidirectional"),
        ("27", "RC6", "bidirectional"),
        ("28", "RC7", "bidirectional"),
    ]

    mcu_pin_lines = []
    for i in range(14):
        pnum, pname, ptype = mcu_pins[i]
        y_pos = 16.51 - (i * 2.54)
        mcu_pin_lines.append(f'      (pin {ptype} line (at -15.24 {y_pos:.2f} 0) (length 2.54) (name "{pname}" (effects (font (size 1.27 1.27)))) (number "{pnum}" (effects (font (size 1.27 1.27)))))')

    for i in range(14):
        pnum, pname, ptype = mcu_pins[14 + i]
        y_pos = -16.51 + (i * 2.54)
        mcu_pin_lines.append(f'      (pin {ptype} line (at 15.24 {y_pos:.2f} 180) (length 2.54) (name "{pname}" (effects (font (size 1.27 1.27)))) (number "{pnum}" (effects (font (size 1.27 1.27)))))')

    mcu_pins_str = "\n".join(mcu_pin_lines)

    def gen_conn_pins(count):
        lines = []
        for i in range(count):
            y = (count - 1) * 1.27 - i * 2.54
            lines.append(f'      (pin passive line (at -5.08 {y:.2f} 0) (length 2.54) (name "Pin_{i+1}" (effects (font (size 1.27 1.27)))) (number "{i+1}" (effects (font (size 1.27 1.27)))))')
        return "\n".join(lines)

    return f'''  (lib_symbols
    (symbol "MCU_Microchip_PIC:PIC16F18855-I_SP" (in_bom yes) (on_board yes)
      (property "Reference" "U" (id 0) (at 0 21.59 0) (effects (font (size 1.27 1.27))))
      (property "Value" "PIC16F18855-I_SP" (id 1) (at 0 -19.05 0) (effects (font (size 1.27 1.27))))
      (symbol "PIC16F18855-I_SP_0_1"
        (rectangle (start -12.7 19.05) (end 12.7 -19.05) (stroke (width 0.254) (type default)) (fill (type background)))
{mcu_pins_str}
      )
    )
    (symbol "Device:R" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "R" (id 0) (at 2.032 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "R" (id 1) (at -2.032 0 0) (effects (font (size 1.27 1.27))))
      (symbol "R_0_1"
        (rectangle (start -1.016 2.54) (end 1.016 -2.54) (stroke (width 0.254) (type default)) (fill (type none)))
        (pin passive line (at 0 5.08 270) (length 2.54) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -5.08 90) (length 2.54) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:C" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "C" (id 0) (at 2.032 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "C" (id 1) (at -2.032 0 0) (effects (font (size 1.27 1.27))))
      (symbol "C_0_1"
        (polyline (pts (xy -2.54 0.635) (xy 2.54 0.635)) (stroke (width 0.508) (type default)))
        (polyline (pts (xy -2.54 -0.635) (xy 2.54 -0.635)) (stroke (width 0.508) (type default)))
        (pin passive line (at 0 5.08 270) (length 4.445) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -5.08 90) (length 4.445) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:C_Polarized" (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "C" (id 0) (at 2.032 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "C_Polarized" (id 1) (at -2.032 0 0) (effects (font (size 1.27 1.27))))
      (symbol "C_Polarized_0_1"
        (polyline (pts (xy -2.54 0.635) (xy 2.54 0.635)) (stroke (width 0.508) (type default)))
        (polyline (pts (xy -2.54 -0.635) (xy 2.54 -0.635)) (stroke (width 0.508) (type default)))
        (pin passive line (at 0 5.08 270) (length 4.445) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 0 -5.08 90) (length 4.445) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:D" (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "D" (id 0) (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (property "Value" "D" (id 1) (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
      (symbol "D_0_1"
        (polyline (pts (xy -1.27 1.27) (xy -1.27 -1.27) (xy 1.27 0) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 1.27) (xy 1.27 -1.27)) (stroke (width 0.254) (type default)))
        (pin passive line (at -5.08 0 0) (length 3.81) (name "K" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 5.08 0 180) (length 3.81) (name "A" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:D_Zener" (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "D" (id 0) (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (property "Value" "D_Zener" (id 1) (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
      (symbol "D_Zener_0_1"
        (polyline (pts (xy -1.27 1.27) (xy -1.27 -1.27) (xy 1.27 0) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 1.27) (xy 1.27 -1.27)) (stroke (width 0.254) (type default)))
        (pin passive line (at -5.08 0 0) (length 3.81) (name "K" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 5.08 0 180) (length 3.81) (name "A" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:D_Schottky" (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "D" (id 0) (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (property "Value" "D_Schottky" (id 1) (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
      (symbol "D_Schottky_0_1"
        (polyline (pts (xy -1.27 1.27) (xy -1.27 -1.27) (xy 1.27 0) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 1.27) (xy 1.27 -1.27)) (stroke (width 0.254) (type default)))
        (pin passive line (at -5.08 0 0) (length 3.81) (name "K" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 5.08 0 180) (length 3.81) (name "A" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Device:D_Schottky_x2_KA_AK" (in_bom yes) (on_board yes)
      (property "Reference" "U" (id 0) (at 0 6.35 0) (effects (font (size 1.27 1.27))))
      (property "Value" "BAT54S" (id 1) (at 0 -6.35 0) (effects (font (size 1.27 1.27))))
      (symbol "D_Schottky_x2_KA_AK_0_1"
        (rectangle (start -5.08 5.08) (end 5.08 -5.08) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin passive line (at -7.62 -2.54 0) (length 2.54) (name "A1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -7.62 2.54 0) (length 2.54) (name "K2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 7.62 0 180) (length 2.54) (name "K1A2" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Isolator:PC817" (in_bom yes) (on_board yes)
      (property "Reference" "U" (id 0) (at 0 6.35 0) (effects (font (size 1.27 1.27))))
      (property "Value" "PC817" (id 1) (at 0 -6.35 0) (effects (font (size 1.27 1.27))))
      (symbol "PC817_0_1"
        (rectangle (start -7.62 5.08) (end 7.62 -5.08) (stroke (width 0.254) (type default)) (fill (type background)))
        (pin passive line (at -10.16 2.54 0) (length 2.54) (name "A" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at -10.16 -2.54 0) (length 2.54) (name "K" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 10.16 -2.54 180) (length 2.54) (name "E" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 10.16 2.54 180) (length 2.54) (name "C" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Switch:SW_Push" (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "SW" (id 0) (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (property "Value" "SW_Push" (id 1) (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
      (symbol "SW_Push_0_1"
        (circle (center -1.27 0) (radius 0.635) (stroke (width 0.254) (type default)) (fill (type none)))
        (circle (center 1.27 0) (radius 0.635) (stroke (width 0.254) (type default)) (fill (type none)))
        (pin passive line (at -5.08 0 0) (length 3.81) (name "1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 5.08 0 180) (length 3.81) (name "2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Transistor_FET:IRLZ44N" (in_bom yes) (on_board yes)
      (property "Reference" "Q" (id 0) (at 0 6.35 0) (effects (font (size 1.27 1.27))))
      (property "Value" "IRLZ44N" (id 1) (at 0 -6.35 0) (effects (font (size 1.27 1.27))))
      (symbol "IRLZ44N_0_1"
        (polyline (pts (xy 0 2.54) (xy 0 -2.54)) (stroke (width 0.508) (type default)))
        (pin input line (at -5.08 0 0) (length 5.08) (name "G" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 2.54 5.08 270) (length 2.54) (name "D" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 2.54 -5.08 90) (length 2.54) (name "S" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Transistor_BJT:2N3904" (in_bom yes) (on_board yes)
      (property "Reference" "Q" (id 0) (at 0 6.35 0) (effects (font (size 1.27 1.27))))
      (property "Value" "2N3904" (id 1) (at 0 -6.35 0) (effects (font (size 1.27 1.27))))
      (symbol "2N3904_0_1"
        (polyline (pts (xy 0 2.54) (xy 0 -2.54)) (stroke (width 0.508) (type default)))
        (pin passive line (at 2.54 -5.08 90) (length 2.54) (name "E" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
        (pin input line (at -5.08 0 0) (length 5.08) (name "B" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
        (pin passive line (at 2.54 5.08 270) (length 2.54) (name "C" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      )
    )
    (symbol "Connector:Conn_01x01_Pin" (in_bom yes) (on_board yes)
      (property "Reference" "J" (id 0) (at 0 3.81 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Conn_01x01_Pin" (id 1) (at 0 -3.81 0) (effects (font (size 1.27 1.27))))
      (symbol "Conn_01x01_Pin_0_1"
        (rectangle (start -2.54 2.54) (end 2.54 -2.54) (stroke (width 0.254) (type default)) (fill (type background)))
{gen_conn_pins(1)}
      )
    )
    (symbol "Connector:Conn_01x02_Pin" (in_bom yes) (on_board yes)
      (property "Reference" "J" (id 0) (at 0 5.08 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Conn_01x02_Pin" (id 1) (at 0 -5.08 0) (effects (font (size 1.27 1.27))))
      (symbol "Conn_01x02_Pin_0_1"
        (rectangle (start -2.54 3.81) (end 2.54 -3.81) (stroke (width 0.254) (type default)) (fill (type background)))
{gen_conn_pins(2)}
      )
    )
    (symbol "Connector:Conn_01x03_Pin" (in_bom yes) (on_board yes)
      (property "Reference" "J" (id 0) (at 0 6.35 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Conn_01x03_Pin" (id 1) (at 0 -6.35 0) (effects (font (size 1.27 1.27))))
      (symbol "Conn_01x03_Pin_0_1"
        (rectangle (start -2.54 5.08) (end 2.54 -5.08) (stroke (width 0.254) (type default)) (fill (type background)))
{gen_conn_pins(3)}
      )
    )
    (symbol "Connector:Conn_01x04_Pin" (in_bom yes) (on_board yes)
      (property "Reference" "J" (id 0) (at 0 7.62 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Conn_01x04_Pin" (id 1) (at 0 -7.62 0) (effects (font (size 1.27 1.27))))
      (symbol "Conn_01x04_Pin_0_1"
        (rectangle (start -2.54 6.35) (end 2.54 -6.35) (stroke (width 0.254) (type default)) (fill (type background)))
{gen_conn_pins(4)}
      )
    )
    (symbol "Connector:Conn_01x06_Pin" (in_bom yes) (on_board yes)
      (property "Reference" "J" (id 0) (at 0 10.16 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Conn_01x06_Pin" (id 1) (at 0 -10.16 0) (effects (font (size 1.27 1.27))))
      (symbol "Conn_01x06_Pin_0_1"
        (rectangle (start -2.54 8.89) (end 2.54 -8.89) (stroke (width 0.254) (type default)) (fill (type background)))
{gen_conn_pins(6)}
      )
    )
  )'''

def calc_pin_pos(comp_tuple, pin_num):
    ref, val, fp, cx, cy, lib_sym, pref, pins = comp_tuple
    pstr = str(pin_num)

    if "PIC16F18855" in lib_sym:
        p = int(pin_num)
        if p <= 14:
            return (cx - 15.24, cy - 16.51 + (p - 1) * 2.54)
        else:
            return (cx + 15.24, cy + 16.51 - (p - 15) * 2.54)

    elif lib_sym == "Device:R" or lib_sym == "Device:C" or lib_sym == "Device:C_Polarized":
        if pstr == "1":
            return (cx, cy - 5.08)
        else:
            return (cx, cy + 5.08)

    elif lib_sym in ("Device:D", "Device:D_Zener", "Device:D_Schottky"):
        if pstr == "1":
            return (cx - 5.08, cy)
        else:
            return (cx + 5.08, cy)

    elif lib_sym == "Device:D_Schottky_x2_KA_AK":  # BAT54S
        if pstr == "1":
            return (cx - 7.62, cy + 2.54)  # GND
        elif pstr == "2":
            return (cx - 7.62, cy - 2.54)  # +5V
        else:
            return (cx + 7.62, cy)        # Signal

    elif lib_sym == "Isolator:PC817":
        if pstr == "1":
            return (cx - 10.16, cy - 2.54)
        elif pstr == "2":
            return (cx - 10.16, cy + 2.54)
        elif pstr == "3":
            return (cx + 10.16, cy + 2.54)
        else:
            return (cx + 10.16, cy - 2.54)

    elif lib_sym == "Transistor_BJT:2N3904":
        if pstr == "1":
            return (cx + 2.54, cy + 5.08)  # Emitter
        elif pstr == "2":
            return (cx - 5.08, cy)         # Base
        else:
            return (cx + 2.54, cy - 5.08)  # Collector

    elif lib_sym == "Transistor_FET:IRLZ44N":
        if pstr == "1":
            return (cx - 5.08, cy)         # Gate
        elif pstr == "2":
            return (cx + 2.54, cy - 5.08)  # Drain
        else:
            return (cx + 2.54, cy + 5.08)  # Source

    elif lib_sym == "Switch:SW_Push":
        if pstr == "1":
            return (cx - 5.08, cy)
        else:
            return (cx + 5.08, cy)

    elif "Conn_" in lib_sym:
        p = int(pin_num)
        count = int(lib_sym.split("Conn_01x")[1].split("_")[0])
        y_offset = (count - 1) * 1.27 - (p - 1) * 2.54
        return (cx - 5.08, cy - y_offset)

    return (cx, cy)

def build_kicad_sch():
    u_str = lambda s: gen_uuid(s)

    lines = []
    lines.append('(kicad_sch (version 20231120) (generator "PicAmpControl gen_schematic.py")')
    lines.append(f'  (uuid "{u_str("root")}")')
    lines.append('  (paper "A2")')
    lines.append('  (title_block')
    lines.append('    (title "PicAmpControl Protection Controller")')
    lines.append('    (date "2026-09-13")')
    lines.append('    (rev "2")')
    lines.append('    (comment 1 "Includes Input Protection & NPN Drivers")')
    lines.append('  )')
    lines.append('')
    lines.append(build_lib_symbols())
    lines.append('')

    # Track net nodes to draw wires
    net_pin_nodes = {}

    # Placed Symbol Instances
    for comp in components_data:
        ref, val, footprint, x, y, lib_sym, pref, pins_dict = comp
        comp_uuid = u_str(f"symbol_{ref}")
        lines.append(f'  (symbol (lib_id "{lib_sym}") (at {x} {y} 0) (unit 1)')
        lines.append('    (in_bom yes) (on_board yes)')
        lines.append(f'    (uuid "{comp_uuid}")')
        lines.append(f'    (property "Reference" "{ref}" (id 0) (at {x} {y-4} 0) (effects (font (size 1.27 1.27))))')
        lines.append(f'    (property "Value" "{val}" (id 1) (at {x} {y+4} 0) (effects (font (size 1.27 1.27))))')
        lines.append(f'    (property "Footprint" "{footprint}" (id 2) (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))')

        for pnum, nname in pins_dict.items():
            pin_uuid = u_str(f"pin_{ref}_{pnum}")
            lines.append(f'    (pin "{pnum}" (uuid "{pin_uuid}"))')
            pos = calc_pin_pos(comp, pnum)
            if nname not in net_pin_nodes:
                net_pin_nodes[nname] = []
            net_pin_nodes[nname].append((ref, pnum, pos))

        lines.append('  )')

    # Draw Wires & Net Labels for clean connection mapping
    wire_idx = 0
    label_idx = 0

    for nname, nodes in net_pin_nodes.items():
        if nname in ("NC", ""):
            continue

        # If it's a net with 2 or more nodes, draw wires between adjacent nodes
        for i in range(len(nodes) - 1):
            x1, y1 = nodes[i][2]
            x2, y2 = nodes[i+1][2]
            wire_uuid = u_str(f"wire_{nname}_{i}")

            # Draw L-shaped wire if X and Y differ
            if x1 != x2 and y1 != y2:
                mid_x = (x1 + x2) / 2
                wire_uuid1 = u_str(f"wire_{nname}_{i}_a")
                wire_uuid2 = u_str(f"wire_{nname}_{i}_b")
                wire_uuid3 = u_str(f"wire_{nname}_{i}_c")

                lines.append(f'  (wire (pts (xy {x1:.2f} {y1:.2f}) (xy {mid_x:.2f} {y1:.2f})) (stroke (width 0) (type default)) (uuid "{wire_uuid1}"))')
                lines.append(f'  (wire (pts (xy {mid_x:.2f} {y1:.2f}) (xy {mid_x:.2f} {y2:.2f})) (stroke (width 0) (type default)) (uuid "{wire_uuid2}"))')
                lines.append(f'  (wire (pts (xy {mid_x:.2f} {y2:.2f}) (xy {x2:.2f} {y2:.2f})) (stroke (width 0) (type default)) (uuid "{wire_uuid3}"))')
            else:
                lines.append(f'  (wire (pts (xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f})) (stroke (width 0) (type default)) (uuid "{wire_uuid}"))')

        # Place a Net Label at the first pin node of the net
        lx, ly = nodes[0][2]
        lbl_uuid = u_str(f"label_{nname}_{lx}_{ly}")
        lines.append(f'  (label "{nname}" (at {lx:.2f} {ly:.2f} 0) (fields_autoplaced)')
        lines.append(f'    (effects (font (size 1.27 1.27)) (justify left bottom))')
        lines.append(f'    (uuid "{lbl_uuid}")')
        lines.append('  )')

    lines.append(')')
    return "\n".join(lines)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.realpath(__file__))
    sch_file = os.path.join(script_dir, "PicAmpControl.kicad_sch")
    content = build_kicad_sch()
    with open(sch_file, "w") as f:
        f.write(content)
    print(f"wrote {sch_file}: {len(components_data)} symbols, complete pins & wires generated")

