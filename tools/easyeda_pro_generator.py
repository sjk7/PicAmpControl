#!/usr/bin/env python3
"""
EasyEDA Pro Schematic Generator

Generates PicAmpControl schematic directly for EasyEDA Pro using the official eda.* API.
Output can be:
1. Imported via easyeda-agent CLI
2. Consumed by easyeda-copilot MCP server
3. Used with official EasyEDA Pro SDK extension

This approach bypasses KiCad entirely and targets EasyEDA Pro natively.
"""

import json
import uuid
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple


@dataclass
class Pin:
    """Schematic symbol pin definition"""
    pin_id: str
    pin_name: str
    pin_number: str
    position: str  # 'LEFT', 'RIGHT', 'TOP', 'BOTTOM'


@dataclass
class Component:
    """Schematic component instance"""
    uuid: str
    part_number: str  # e.g., "C0603", "R0402", or exact MPN like "PIC16F18855-I/SP"
    designator: str   # e.g., "R1", "U1", "C1"
    value: str        # e.g., "10k", "100nF", ""
    x: float
    y: float
    rotation: int = 0
    mirrored: bool = False
    lcsc_part: str = ""  # Optional LCSC C-number for part resolution


@dataclass
class Net:
    """Electrical net definition"""
    name: str
    color: str = "#000000"


@dataclass
class Wire:
    """Schematic wire/connection"""
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    net_name: str
    stroke_width: float = 0.01


@dataclass
class Label:
    """Text label on schematic"""
    text: str
    x: float
    y: float
    font_size: float = 0.04


class EasyEDAProSchematic:
    """Generates EasyEDA Pro schematic data for PicAmpControl"""
    
    def __init__(self, title: str = "PicAmpControl Extended"):
        self.title = title
        self.components: List[Component] = []
        self.nets: List[Net] = []
        self.wires: List[Wire] = []
        self.labels: List[Label] = []
        self.grid_size = 0.01  # 10mm grid for placement
    
    def add_component(self, part_number: str, designator: str, value: str,
                     x: float, y: float, lcsc_part: str = ""):
        """Add component to schematic"""
        component = Component(
            uuid=str(uuid.uuid4()),
            part_number=part_number,
            designator=designator,
            value=value,
            x=x,
            y=y,
            lcsc_part=lcsc_part
        )
        self.components.append(component)
        return component
    
    def add_net(self, name: str):
        """Define a named net"""
        if not any(n.name == name for n in self.nets):
            self.nets.append(Net(name=name))
    
    def add_wire(self, start: Tuple[float, float], end: Tuple[float, float], net_name: str):
        """Add wire connecting two points"""
        self.add_net(net_name)
        wire = Wire(
            start_x=start[0],
            start_y=start[1],
            end_x=end[0],
            end_y=end[1],
            net_name=net_name
        )
        self.wires.append(wire)
    
    def add_label(self, text: str, x: float, y: float):
        """Add text label"""
        self.labels.append(Label(text=text, x=x, y=y))
    
    def build_for_easyeda_agent(self) -> Dict:
        """
        Generate data structure compatible with easyeda-agent CLI.
        
        This can be used with:
        $ easyeda sch create --spec <this-json>
        """
        return {
            "title": self.title,
            "components": [asdict(c) for c in self.components],
            "nets": [asdict(n) for n in self.nets],
            "wires": [asdict(w) for w in self.wires],
            "labels": [asdict(l) for l in self.labels],
            "version": "1.0",
            "format": "easyeda-agent-schematic-v1"
        }
    
    def build_for_easyeda_copilot(self) -> Dict:
        """
        Generate data structure for easyeda-copilot MCP server.
        
        Structure compatible with copilot's circuit assembly workflow.
        """
        # Group components by functional block
        blocks = self._group_components_by_function()
        
        return {
            "title": self.title,
            "description": "PicAmpControl amplifier protection circuit",
            "blocks": blocks,
            "components": [asdict(c) for c in self.components],
            "connectivity": self._build_connectivity_matrix(),
        }
    
    def _group_components_by_function(self) -> Dict[str, List[Dict]]:
        """Group components by circuit function"""
        groups = {
            "Power Supply": [],
            "MCU": [],
            "ADC Conditioning": [],
            "Comparator": [],
            "Digital Outputs": [],
            "Interfaces": [],
            "Fan Control": [],
        }
        
        designator_prefix = lambda ref: ''.join([c for c in ref if c.isalpha()])
        
        for comp in self.components:
            prefix = designator_prefix(comp.designator)
            
            if prefix == "J" and "12V" in comp.value:
                groups["Power Supply"].append(asdict(comp))
            elif prefix == "U" and "L7805" in comp.part_number:
                groups["Power Supply"].append(asdict(comp))
            elif prefix == "C" and "µF" in comp.value:
                groups["Power Supply"].append(asdict(comp))
            elif prefix == "U" and "PIC" in comp.part_number:
                groups["MCU"].append(asdict(comp))
            elif any(x in comp.designator for x in ["ADC", "REFL", "FWD", "OCP", "OD", "DRAIN"]):
                groups["ADC Conditioning"].append(asdict(comp))
            elif "LM339" in comp.part_number:
                groups["Comparator"].append(asdict(comp))
            elif any(x in comp.designator for x in ["TX", "TRIP"]):
                groups["Digital Outputs"].append(asdict(comp))
            elif any(x in comp.designator for x in ["I2C", "ENC", "PTT"]):
                groups["Interfaces"].append(asdict(comp))
            elif any(x in comp.designator for x in ["FAN", "Q1"]):
                groups["Fan Control"].append(asdict(comp))
        
        return {k: v for k, v in groups.items() if v}
    
    def _build_connectivity_matrix(self) -> Dict[str, List[str]]:
        """Build net-to-component connectivity map"""
        connectivity = {}
        for net in self.nets:
            connectivity[net.name] = []
        
        for wire in self.wires:
            if wire.net_name not in connectivity:
                connectivity[wire.net_name] = []
        
        return connectivity


def generate_picampcontrol_schematic() -> EasyEDAProSchematic:
    """
    Generate complete PicAmpControl schematic for EasyEDA Pro.
    
    Component layout:
    - Power supply (left, top)
    - MCU (center-left)
    - ADC conditioning (center-right)
    - Fan control (right)
    - Interfaces (bottom)
    """
    
    sch = EasyEDAProSchematic("PicAmpControl - Amplifier Protection")
    
    # Define power nets
    for net_name in ["+12V_RAW", "+5V", "GND"]:
        sch.add_net(net_name)
    
    # POWER SUPPLY SECTION (existing baseline components)
    print("Adding power supply components...")
    sch.add_component("Conn_01x02", "J2", "12V_INPUT", 0.0, 0.0)
    sch.add_component("L7805", "U2", "L7805 5V Regulator", 0.10, 0.0, "C6162")
    sch.add_component("C0603", "C2", "100nF", 0.05, 0.05)  # Input cap
    sch.add_component("C0603", "C3", "10µF", 0.15, 0.05)   # Output cap
    sch.add_component("C0603", "C4", "100nF", 0.15, 0.10)  # Bypass
    
    # MCU SECTION
    print("Adding MCU and support components...")
    sch.add_component("DIP-28", "U1", "PIC16F18855-I/SP", 0.10, 0.15, "C1128")
    sch.add_component("R0603", "R1", "10k", 0.08, 0.13)    # MCLR pull-up
    sch.add_component("C0603", "C1", "100nF", 0.12, 0.17)  # Decoupling
    
    # ADC PRE-FILTER SECTION (Forward & Reflected SWR)
    print("Adding ADC pre-filter components...")
    y_offset = 0.25
    # Forward power divider
    sch.add_component("R0603", "R5", "100k", 0.05, y_offset)
    sch.add_component("R0603", "R6", "10k", 0.05, y_offset + 0.05)
    sch.add_component("C0603", "C5", "10nF", 0.08, y_offset + 0.025)  # LPF
    # Reflected power divider
    sch.add_component("R0603", "R7", "100k", 0.15, y_offset)
    sch.add_component("R0603", "R8", "10k", 0.15, y_offset + 0.05)
    sch.add_component("C0603", "C6", "10nF", 0.18, y_offset + 0.025)
    
    # ADC POST-FILTER SECTION
    print("Adding ADC post-filter components...")
    y_offset = 0.38
    sch.add_component("R0603", "R9", "100k", 0.05, y_offset)
    sch.add_component("R0603", "R10", "10k", 0.05, y_offset + 0.05)
    sch.add_component("C0603", "C7", "10nF", 0.08, y_offset + 0.025)
    sch.add_component("R0603", "R11", "100k", 0.15, y_offset)
    sch.add_component("R0603", "R12", "10k", 0.15, y_offset + 0.05)
    sch.add_component("C0603", "C8", "10nF", 0.18, y_offset + 0.025)
    
    # ADC CONDITIONING SECTION (Temp, OCP, OD, Drain)
    print("Adding ADC conditioning components...")
    conditions = [
        ("TEMP", 0.25, 0.51),
        ("OCP", 0.25, 0.58),
        ("OD", 0.25, 0.65),
        ("DRAIN", 0.25, 0.72)
    ]
    
    for idx, (name, x_base, y_pos) in enumerate(conditions):
        sch.add_component("R0603", f"R_ADC_{name}_H", "100k", x_base, y_pos)
        sch.add_component("R0603", f"R_ADC_{name}_L", "10k", x_base + 0.05, y_pos)
        sch.add_component("C0603", f"C_ADC_{name}", "10nF", x_base + 0.1, y_pos)
    
    # COMPARATOR STAGE (LM339)
    print("Adding comparator stage...")
    sch.add_component("SO-14", "U3", "LM339N", 0.15, 0.51, "C5957")
    sch.add_component("R0603", "R_OCP_FB", "100k", 0.13, 0.45)
    sch.add_component("R0603", "R_OCP_REF", "10k", 0.17, 0.45)
    
    # DIGITAL OUTPUTS (TX, TX_VCC, TX_BIAS, TRIP pulldowns)
    print("Adding digital output pull-downs...")
    outputs = [
        ("TX", 0.0, 0.51),
        ("TX_VCC", 0.0, 0.57),
        ("TX_BIAS", 0.0, 0.63),
        ("TRIP", 0.0, 0.69)
    ]
    
    for name, x, y in outputs:
        sch.add_component("R0603", f"R_{name}_PD", "10k", x, y)
    
    # FAN CONTROL (existing)
    print("Adding fan control components...")
    sch.add_component("R0603", "R2", "220R", 0.20, 0.65)   # Gate resistor
    sch.add_component("DO-41", "D1", "5.1V Zener", 0.22, 0.68)
    sch.add_component("SOT-23", "Q1", "NMOS Logic-Level", 0.24, 0.70)
    sch.add_component("Conn_01x02", "J3", "FAN", 0.28, 0.68)
    
    # INTERFACES (I2C, Encoder, PTT)
    print("Adding interface components...")
    
    # I2C LCD
    sch.add_component("R0603", "R_I2C_SDA", "4.7k", 0.05, 0.78)
    sch.add_component("R0603", "R_I2C_SCL", "4.7k", 0.10, 0.78)
    sch.add_component("Conn_01x04", "J_I2C", "I2C_LCD", 0.075, 0.85)
    
    # Encoder
    sch.add_component("R0603", "R_ENC_A_PU", "10k", 0.15, 0.78)
    sch.add_component("R0603", "R_ENC_B_PU", "10k", 0.20, 0.78)
    sch.add_component("R0603", "R_ENC_SW_PU", "10k", 0.25, 0.78)
    sch.add_component("EC11", "SW1", "Rotary Encoder", 0.20, 0.88)
    
    # PTT Input
    sch.add_component("R0603", "R_PTT_PD", "10k", 0.00, 0.88)
    sch.add_component("Conn_01x02", "J_PTT", "PTT_INPUT", 0.05, 0.88)
    
    # Add nets
    for net_name in ["ADC_FWD_PRE", "ADC_REFL_PRE", "ADC_FWD_POST", "ADC_REFL_POST",
                     "ADC_TEMP", "ADC_OCP", "ADC_OD", "ADC_DRAIN",
                     "I2C_SDA", "I2C_SCL", "ENC_A", "ENC_B", "ENC_SW",
                     "TX", "TX_VCC", "TX_BIAS", "TRIP", "PTT_IN",
                     "HARD_FAULT", "FAN_CTRL"]:
        sch.add_net(net_name)
    
    return sch


if __name__ == '__main__':
    print("Generating PicAmpControl schematic for EasyEDA Pro...")
    sch = generate_picampcontrol_schematic()
    
    # Output for easyeda-agent
    agent_spec = sch.build_for_easyeda_agent()
    agent_output = Path('out/picampcontrol_easyeda_agent.json')
    agent_output.parent.mkdir(exist_ok=True)
    with open(agent_output, 'w') as f:
        json.dump(agent_spec, f, indent=2)
    print(f"[OK] Generated for easyeda-agent: {agent_output}")
    
    # Output for easyeda-copilot
    copilot_spec = sch.build_for_easyeda_copilot()
    copilot_output = Path('out/picampcontrol_easyeda_copilot.json')
    with open(copilot_output, 'w') as f:
        json.dump(copilot_spec, f, indent=2)
    print(f"[OK] Generated for easyeda-copilot: {copilot_output}")
    
    print(f"\n=== Schematic Summary ===")
    print(f"  Components: {len(sch.components)}")
    print(f"  Nets: {len(sch.nets)}")
    print(f"  Wires: {len(sch.wires)}")
    print(f"  Labels: {len(sch.labels)}")
    
    print(f"\nNext steps:")
    print(f"1. Using easyeda-agent:")
    print(f"   $ easyeda sch create --spec out/picampcontrol_easyeda_agent.json")
    print(f"2. Using easyeda-copilot (MCP):")
    print(f"   • Pass copilot_spec to Claude with easyeda-copilot MCP enabled")
    print(f"   • Ask: 'Create this circuit in EasyEDA Pro'")
