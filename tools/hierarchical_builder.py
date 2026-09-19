#!/usr/bin/env python3
"""
Hierarchical KiCad Schematic Builder using Subcircuits

Generates modular blocks as separate sheets:
- adc_prefilter.kicad_sch (RA0/RA1 SWR bridge)
- adc_postfilter.kicad_sch (RA2/RA3 SWR bridge)
- adc_conditioning.kicad_sch (temp, OCP, OD, drain)
- comparator_stage.kicad_sch (overcurrent detection)
- digital_outputs.kicad_sch (TX, TX_VCC, TX_BIAS, TRIP)
- i2c_interface.kicad_sch (LCD)
- encoder_interface.kicad_sch (rotary encoder)
- ptt_input.kicad_sch (PTT connector)
- top.kicad_sch (integrates all via hierarchical pins)
"""

import uuid
from pathlib import Path
from typing import List, Dict, Tuple


class KiCadSubcircuit:
    """Base class for hierarchical subcircuit sheets"""
    
    def __init__(self, name: str, title: str):
        self.name = name
        self.title = title
        self.uuid = str(uuid.uuid4())
        self.components: List[Dict] = []
        self.wires: List[Dict] = []
        self.labels: List[Dict] = []
        self.hier_pins: List[Dict] = []  # Hierarchical pins for inter-sheet connections
    
    def add_component(self, lib_id: str, ref: str, value: str, x: float, y: float, 
                      rotation: int = 0, pins: Dict = None):
        """Add a component to the subcircuit"""
        self.components.append({
            'lib_id': lib_id,
            'ref': ref,
            'value': value,
            'x': x,
            'y': y,
            'rotation': rotation,
            'pins': pins or {}
        })
    
    def add_hierarchical_pin(self, name: str, pin_type: str, x: float, y: float):
        """Add a hierarchical pin (interface to parent sheet)"""
        self.hier_pins.append({
            'name': name,
            'type': pin_type,  # 'input', 'output', 'bidirectional', 'passive'
            'x': x,
            'y': y
        })
    
    def add_label(self, text: str, x: float, y: float):
        """Add a net label"""
        self.labels.append({
            'text': text,
            'x': x,
            'y': y
        })
    
    def generate_sexp(self) -> str:
        """Generate KiCad S-expression for this sheet"""
        lines = [
            f'(kicad_sch (version 20240108)',
            f'  (uuid "{self.uuid}")',
            f'  (paper "A4")',
            f'  (title_block',
            f'    (title "{self.title}")',
            f'    (date "2026-09-19")',
            f'  )',
            f''
        ]
        
        # Add hierarchical pins first (interfaces to parent)
        if self.hier_pins:
            lines.append('  ; Hierarchical pins (connections to parent sheet)')
            for pin in self.hier_pins:
                pin_type = self._hier_pin_type(pin['type'])
                lines.append(
                    f'  (hierarchical_pin {pin_type} (at {pin["x"]} {pin["y"]} 0)'
                    f'    (effects (font (size 1.27 1.27)) (justify {self._justify_for_side(pin["x"])}))'
                    f'    (uuid "{uuid.uuid4()}")'
                    f'  )'
                )
        
        # Add components
        if self.components:
            lines.append('  ; Components')
            for comp in self.components:
                lines.append(self._component_sexp(comp))
        
        # Add labels
        if self.labels:
            lines.append('  ; Net labels')
            for label in self.labels:
                lines.append(
                    f'  (global_label "{label["text"]}" (shape passive)'
                    f'    (at {label["x"]} {label["y"]} 0)'
                    f'    (effects (font (size 1.27 1.27)) (justify left))'
                    f'    (uuid "{uuid.uuid4()}")'
                    f'  )'
                )
        
        lines.append(')')
        return '\n'.join(lines)
    
    def _component_sexp(self, comp: Dict) -> str:
        """Generate S-expression for a component"""
        comp_uuid = str(uuid.uuid4())
        return (
            f'  (symbol (lib_id "{comp["lib_id"]}") '
            f'(at {comp["x"]} {comp["y"]} {comp["rotation"]})\n'
            f'    (uuid "{comp_uuid}")\n'
            f'    (property "Reference" "{comp["ref"]}" (at {comp["x"]} {comp["y"]-2} 0)\n'
            f'      (effects (font (size 1.27 1.27)))\n'
            f'    )\n'
            f'    (property "Value" "{comp["value"]}" (at {comp["x"]} {comp["y"]+2} 0)\n'
            f'      (effects (font (size 1.27 1.27)))\n'
            f'    )\n'
        )
    
    def _hier_pin_type(self, pin_type: str) -> str:
        """Map pin type to KiCad hierarchical pin shape"""
        mapping = {
            'input': 'input',
            'output': 'output',
            'bidirectional': 'bidirectional',
            'passive': 'passive'
        }
        return mapping.get(pin_type, 'passive')
    
    def _justify_for_side(self, x: float) -> str:
        """Justify text based on pin position (left or right side)"""
        return 'left' if x < 150 else 'right'


class ADCPreFilterSheet(KiCadSubcircuit):
    """SWR bridge pre-filter stage (forward & reflected power)"""
    
    def __init__(self):
        super().__init__('adc_prefilter', 'ADC Pre-Filter Stage (SWR Bridge)')
        self._build()
    
    def _build(self):
        """Build the pre-filter subcircuit"""
        # Hierarchical pins (interfaces to parent)
        self.add_hierarchical_pin('+5V', 'input', 20, 50)
        self.add_hierarchical_pin('GND', 'input', 20, 240)
        self.add_hierarchical_pin('ADC_FWD_PRE', 'output', 280, 100)
        self.add_hierarchical_pin('ADC_REFL_PRE', 'output', 280, 180)
        
        # Forward voltage divider (high + low resistors + LPF)
        self.add_component('Device:R', 'R1', '100k', 100, 80)    # High divider
        self.add_component('Device:R', 'R2', '10k', 100, 140)    # Low divider
        self.add_component('Device:C', 'C1', '10nF', 150, 110)   # LPF cap
        
        # Reflected voltage divider
        self.add_component('Device:R', 'R3', '100k', 200, 160)   # High divider
        self.add_component('Device:R', 'R4', '10k', 200, 220)    # Low divider
        self.add_component('Device:C', 'C2', '10nF', 250, 190)   # LPF cap
        
        # Labels for internal nets
        self.add_label('+5V', 50, 50)
        self.add_label('GND', 50, 240)
        self.add_label('ADC_FWD_PRE', 280, 100)
        self.add_label('ADC_REFL_PRE', 280, 180)


class ADCPostFilterSheet(KiCadSubcircuit):
    """SWR bridge post-filter stage (forward & reflected power)"""
    
    def __init__(self):
        super().__init__('adc_postfilter', 'ADC Post-Filter Stage (SWR Bridge)')
        self._build()
    
    def _build(self):
        """Build the post-filter subcircuit"""
        self.add_hierarchical_pin('+5V', 'input', 20, 50)
        self.add_hierarchical_pin('GND', 'input', 20, 240)
        self.add_hierarchical_pin('ADC_FWD_POST', 'output', 280, 100)
        self.add_hierarchical_pin('ADC_REFL_POST', 'output', 280, 180)
        
        # Forward voltage divider
        self.add_component('Device:R', 'R1', '100k', 100, 80)
        self.add_component('Device:R', 'R2', '10k', 100, 140)
        self.add_component('Device:C', 'C1', '10nF', 150, 110)
        
        # Reflected voltage divider
        self.add_component('Device:R', 'R3', '100k', 200, 160)
        self.add_component('Device:R', 'R4', '10k', 200, 220)
        self.add_component('Device:C', 'C2', '10nF', 250, 190)
        
        self.add_label('+5V', 50, 50)
        self.add_label('GND', 50, 240)
        self.add_label('ADC_FWD_POST', 280, 100)
        self.add_label('ADC_REFL_POST', 280, 180)


class ADCConditioningSheet(KiCadSubcircuit):
    """Remaining ADC inputs: temperature, overcurrent, overdrive, drain"""
    
    def __init__(self):
        super().__init__('adc_conditioning', 'ADC Conditioning (Temp/OCP/OD/Drain)')
        self._build()
    
    def _build(self):
        """Build conditioning subcircuit"""
        self.add_hierarchical_pin('+5V', 'input', 20, 50)
        self.add_hierarchical_pin('GND', 'input', 20, 280)
        self.add_hierarchical_pin('ADC_TEMP', 'output', 280, 80)
        self.add_hierarchical_pin('ADC_OCP', 'output', 280, 130)
        self.add_hierarchical_pin('ADC_OD', 'output', 280, 180)
        self.add_hierarchical_pin('ADC_DRAIN', 'output', 280, 230)
        
        # Temperature sensor (NTC thermistor)
        self.add_component('Device:R_Thermistor', 'R_TEMP', '10k NTC', 100, 80)
        self.add_component('Device:R', 'R_TEMP_PU', '10k', 150, 80)
        self.add_component('Device:C', 'C_TEMP', '10nF', 200, 80)
        
        # Overcurrent divider
        self.add_component('Device:R', 'R_OCP_H', '47k', 100, 130)
        self.add_component('Device:R', 'R_OCP_L', '10k', 150, 130)
        self.add_component('Device:C', 'C_OCP', '10nF', 200, 130)
        
        # Overdrive divider
        self.add_component('Device:R', 'R_OD_H', '100k', 100, 180)
        self.add_component('Device:R', 'R_OD_L', '10k', 150, 180)
        self.add_component('Device:C', 'C_OD', '10nF', 200, 180)
        
        # Drain voltage divider
        self.add_component('Device:R', 'R_DRAIN_H', '200k', 100, 230)
        self.add_component('Device:R', 'R_DRAIN_L', '10k', 150, 230)
        self.add_component('Device:C', 'C_DRAIN', '10nF', 200, 230)
        
        self.add_label('+5V', 50, 50)
        self.add_label('GND', 50, 280)


class ComparatorSheet(KiCadSubcircuit):
    """Overcurrent detection comparator (LM339)"""
    
    def __init__(self):
        super().__init__('comparator', 'Overcurrent Comparator Stage')
        self._build()
    
    def _build(self):
        self.add_hierarchical_pin('+5V', 'input', 20, 50)
        self.add_hierarchical_pin('GND', 'input', 20, 150)
        self.add_hierarchical_pin('ADC_OCP', 'input', 20, 100)
        self.add_hierarchical_pin('HARD_FAULT', 'output', 280, 100)
        
        # LM339 comparator
        self.add_component('Amplifier_Operational:LM339', 'U1', 'LM339', 150, 100)
        
        # Feedback resistor
        self.add_component('Device:R', 'R_FB', '100k', 100, 80)
        
        # Reference resistor
        self.add_component('Device:R', 'R_REF', '10k', 100, 120)
        
        self.add_label('+5V', 50, 50)
        self.add_label('GND', 50, 150)


class DigitalOutputsSheet(KiCadSubcircuit):
    """Digital control outputs: TX, TX_VCC, TX_BIAS, TRIP"""
    
    def __init__(self):
        super().__init__('digital_outputs', 'Digital Control Outputs')
        self._build()
    
    def _build(self):
        self.add_hierarchical_pin('+5V', 'input', 20, 50)
        self.add_hierarchical_pin('GND', 'input', 20, 200)
        self.add_hierarchical_pin('TX', 'input', 20, 80)
        self.add_hierarchical_pin('TX_VCC', 'input', 20, 110)
        self.add_hierarchical_pin('TX_BIAS', 'input', 20, 140)
        self.add_hierarchical_pin('TRIP', 'input', 20, 170)
        
        # Pull-down resistors for each output
        y_pos = 80
        for i, (name, ref) in enumerate([('TX', 'R1'), ('TX_VCC', 'R2'), 
                                          ('TX_BIAS', 'R3'), ('TRIP', 'R4')]):
            self.add_component('Device:R', ref, '10k', 150, y_pos)
            y_pos += 30
        
        self.add_label('+5V', 50, 50)
        self.add_label('GND', 50, 200)


class I2CInterfaceSheet(KiCadSubcircuit):
    """I2C LCD interface with pull-ups"""
    
    def __init__(self):
        super().__init__('i2c_interface', 'I2C LCD Interface')
        self._build()
    
    def _build(self):
        self.add_hierarchical_pin('+5V', 'input', 20, 50)
        self.add_hierarchical_pin('GND', 'input', 20, 150)
        self.add_hierarchical_pin('I2C_SDA', 'bidirectional', 20, 100)
        self.add_hierarchical_pin('I2C_SCL', 'bidirectional', 20, 130)
        self.add_hierarchical_pin('J_I2C', 'output', 280, 100)
        
        # Pull-up resistors
        self.add_component('Device:R', 'R_SDA_PU', '4.7k', 100, 100)
        self.add_component('Device:R', 'R_SCL_PU', '4.7k', 100, 130)
        
        # Connector
        self.add_component('Connector_Generic:Conn_01x04', 'J1', 'I2C_LCD', 200, 115)
        
        self.add_label('+5V', 50, 50)
        self.add_label('GND', 50, 150)


class EncoderInterfaceSheet(KiCadSubcircuit):
    """Rotary encoder interface with pull-ups"""
    
    def __init__(self):
        super().__init__('encoder', 'Rotary Encoder Interface')
        self._build()
    
    def _build(self):
        self.add_hierarchical_pin('+5V', 'input', 20, 50)
        self.add_hierarchical_pin('GND', 'input', 20, 200)
        self.add_hierarchical_pin('ENC_A', 'input', 20, 100)
        self.add_hierarchical_pin('ENC_B', 'input', 20, 130)
        self.add_hierarchical_pin('ENC_SW', 'input', 20, 160)
        
        # Pull-up resistors
        self.add_component('Device:R', 'R_A_PU', '10k', 100, 100)
        self.add_component('Device:R', 'R_B_PU', '10k', 100, 130)
        self.add_component('Device:R', 'R_SW_PU', '10k', 100, 160)
        
        # Encoder
        self.add_component('Device:Rotary_Encoder_EC11', 'SW1', 'EC11', 200, 130)
        
        self.add_label('+5V', 50, 50)
        self.add_label('GND', 50, 200)


class PTTInputSheet(KiCadSubcircuit):
    """PTT input with pull-down"""
    
    def __init__(self):
        super().__init__('ptt_input', 'PTT Input')
        self._build()
    
    def _build(self):
        self.add_hierarchical_pin('+5V', 'input', 20, 50)
        self.add_hierarchical_pin('GND', 'input', 20, 150)
        self.add_hierarchical_pin('PTT_IN', 'input', 20, 100)
        
        # Pull-down resistor
        self.add_component('Device:R', 'R_PTT_PD', '10k', 100, 100)
        
        # Connector
        self.add_component('Connector_Generic:Conn_01x02', 'J1', 'PTT_INPUT', 200, 100)
        
        self.add_label('+5V', 50, 50)
        self.add_label('GND', 50, 150)


def generate_all_subcircuits(output_dir: str):
    """Generate all subcircuit sheets"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    subcircuits = [
        ADCPreFilterSheet(),
        ADCPostFilterSheet(),
        ADCConditioningSheet(),
        ComparatorSheet(),
        DigitalOutputsSheet(),
        I2CInterfaceSheet(),
        EncoderInterfaceSheet(),
        PTTInputSheet(),
    ]
    
    for subcircuit in subcircuits:
        sch_file = output_path / f"{subcircuit.name}.kicad_sch"
        with open(sch_file, 'w') as f:
            f.write(subcircuit.generate_sexp())
        print(f"Generated {sch_file}")


if __name__ == '__main__':
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else 'out/subcircuits'
    generate_all_subcircuits(output_dir)
    print(f"\nGenerated {len([ADCPreFilterSheet, ADCPostFilterSheet, ADCConditioningSheet, ComparatorSheet, DigitalOutputsSheet, I2CInterfaceSheet, EncoderInterfaceSheet, PTTInputSheet])} subcircuits in {output_dir}/")
