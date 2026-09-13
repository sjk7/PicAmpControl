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

    # Placed Symbol Instances
    for ref, val, footprint, x, y, lib_sym in components_layout:
        comp_uuid = u_str(f"symbol_{ref}")
        lines.append(f'  (symbol (lib_id "{lib_sym}") (at {x} {y} 0) (unit 1)')
        lines.append('    (in_bom yes) (on_board yes)')
        lines.append(f'    (uuid "{comp_uuid}")')
        lines.append(f'    (property "Reference" "{ref}" (id 0) (at {x} {y-3} 0) (effects (font (size 1.27 1.27))))')
        lines.append(f'    (property "Value" "{val}" (id 1) (at {x} {y+3} 0) (effects (font (size 1.27 1.27))))')
        lines.append(f'    (property "Footprint" "{footprint}" (id 2) (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))')
        lines.append('  )')

    # Global Net Labels for clean connection mapping
    for net_name, lx, ly in net_labels:
        lbl_uuid = u_str(f"label_{net_name}_{lx}_{ly}")
        lines.append(f'  (label "{net_name}" (at {lx} {ly} 0) (fields_autoplaced)')
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
    print(f"wrote {sch_file}: {len(components_layout)} symbols, {len(net_labels)} net labels")
