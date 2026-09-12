#!/usr/bin/env python3
"""Generate a KiCad-format netlist (.net, s-expression) for the PicAmpControl
PIC16F18855-I/SP protection controller board.

This is hand-authored from the documented design (docs/hardware/PIC16F18855_pin_map.md,
README.md, docs/project-architecture.md) since there is no schematic-capture source.
Connectors J1-J11 are added as explicit interconnects to the external sub-boards
(comparator/protection board, sensor bridges, LCD backpack, fan) that the docs
describe as separate boards/modules. The MCU runs from its internal HFINT32
oscillator (32 MHz); no crystal or load capacitors are fitted. Adjust footprints
after import to match the parts you actually buy.
"""

# (ref, value, footprint)
components = [
    ("U1", "PIC16F18855-I/SP", "Package_DIP:DIP-28_W7.62mm"),
    ("R1", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),
    ("R2", "220R", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),
    ("R3", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),
    ("R4", "10k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),
    ("R5", "4.7k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),
    ("R6", "4.7k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"),
    ("C3", "100nF", "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm"),
    ("C4", "10uF", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm"),
    ("Q1", "IRLZ44N", "Package_TO_SOT_THT:TO-220-3_Vertical"),
    ("D1", "1N5819", "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal"),
    ("SW1", "SW_PUSH", "Button_Switch_THT:SW_PUSH_6mm"),
    ("SW2", "SW_PUSH", "Button_Switch_THT:SW_PUSH_6mm"),
    ("J1", "Conn_01x04", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"),
    ("J2", "Conn_01x06", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"),
    ("J3", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"),
    ("J4", "Conn_01x01", "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical"),
    ("J5", "Conn_01x03", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"),
    ("J6", "Conn_01x01", "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical"),
    ("J7", "Conn_01x03", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"),
    ("J8", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"),
    ("J9", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"),
    ("J10", "Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"),
    ("J11", "Conn_01x01", "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical"),
]

# net_name -> [(ref, pin), ...]
nets = {
    "+5V": [("U1", "11"), ("R1", "2"), ("C3", "1"), ("C4", "1"),
            ("J1", "2"), ("J2", "5"), ("R4", "2"), ("R5", "2"), ("R6", "2"),
            ("J7", "1")],
    "GND": [("U1", "8"), ("U1", "20"), ("C3", "2"), ("C4", "2"),
            ("SW1", "2"), ("SW2", "2"), ("R3", "2"), ("Q1", "3"),
            ("J1", "1"), ("J2", "6"), ("J7", "3"), ("J10", "2")],
    "MCLR": [("U1", "1"), ("R1", "1")],
    "SWR1_FWD": [("U1", "2"), ("J8", "1")],
    "SWR1_REF": [("U1", "3"), ("J8", "2")],
    "SWR2_FWD": [("U1", "4"), ("J9", "1")],
    "SWR2_REF": [("U1", "5"), ("J9", "2")],
    "RA4_NC": [("U1", "6")],
    "TEMP": [("U1", "7"), ("J10", "1")],
    "RA6_SPARE": [("U1", "9")],
    "RA7_SPARE": [("U1", "10")],
    "RB6_SPARE": [("U1", "18")],
    "MENU_ADJUST": [("U1", "12"), ("SW1", "1")],
    "CURRENT": [("U1", "13"), ("J11", "1")],
    "OVERDRIVE": [("U1", "14"), ("J2", "1")],
    "DRAIN_PEAK": [("U1", "15"), ("J2", "2")],
    "OC_FAULT": [("U1", "16"), ("J2", "3")],
    "FAN_PWM": [("U1", "17"), ("R2", "1")],
    "FAN_GATE": [("R2", "2"), ("Q1", "1"), ("R3", "1")],
    "TRIP": [("U1", "19"), ("J6", "1")],
    "PTT": [("U1", "21"), ("J4", "1")],
    "COMP_RESET": [("U1", "22"), ("J2", "4")],
    "MENU_NEXT": [("U1", "23"), ("SW2", "1"), ("R4", "1")],
    "LCD_SCL": [("U1", "24"), ("J1", "4"), ("R5", "1")],
    "LCD_SDA": [("U1", "25"), ("J1", "3"), ("R6", "1")],
    "TX": [("U1", "26"), ("J5", "1")],
    "TX_VCC": [("U1", "27"), ("J5", "2")],
    "TX_BIAS": [("U1", "28"), ("J5", "3")],
    "+12V_FAN": [("J7", "2"), ("D1", "2"), ("J3", "1")],
    "FAN_DRAIN": [("Q1", "2"), ("D1", "1"), ("J3", "2")],
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
    (date "2026-09-12")
    (tool "PicAmpControl gen_netlist.py")
    (sheet (number "1") (name "/") (tstamps "/")
      (title_block
        (title "PicAmpControl Protection Controller")
        (company "")
        (rev "1")
        (date "2026-09-12")
        (source "PicAmpControl")
        (comment (number "1") (value "")))))
  (components
{chr(10).join(comp_lines)})
  (libparts)
  (libraries)
  (nets
{chr(10).join(net_lines)}))
'''


if __name__ == "__main__":
    text = build()
    with open("PicAmpControl.net", "w") as f:
        f.write(text)
    print(f"wrote PicAmpControl.net: {len(components)} components, {len(nets)} nets")
