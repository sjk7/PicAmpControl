#!/usr/bin/env python3
"""
Hierarchical Schematic Integrator

Integrates subcircuit sheets into main schematic via sheet instances.
Creates a new extended version of pic_amp_protection.kicad_sch with subcircuit blocks.
"""

import re
import uuid
from pathlib import Path
from typing import List, Dict


class HierarchicalIntegrator:
    """Adds hierarchical sheet instances to a schematic"""
    
    def __init__(self, main_sch_path: str, subcircuits_dir: str):
        self.main_sch_path = Path(main_sch_path)
        self.subcircuits_dir = Path(subcircuits_dir)
        
        with open(main_sch_path) as f:
            self.main_content = f.read()
        
        self.sheet_instances: List[Dict] = []
    
    def add_sheet_instance(self, sheet_name: str, file_path: str, x: float, y: float):
        """Register a sheet instance to add"""
        self.sheet_instances.append({
            'name': sheet_name,
            'file': file_path,
            'x': x,
            'y': y
        })
    
    def integrate(self) -> str:
        """
        Integrate all sheet instances into the main schematic.
        
        Adds sheet_instance S-expressions before the closing paren.
        """
        integrated = self.main_content
        
        # Find insertion point (before final closing paren)
        insertion_point = integrated.rfind('\n)')
        if insertion_point < 0:
            raise ValueError("Cannot find schematic closing paren")
        
        # Generate sheet instance S-expressions
        sheet_sexp = self._generate_sheet_instances_sexp()
        
        # Insert before closing paren
        integrated = integrated[:insertion_point] + '\n' + sheet_sexp + integrated[insertion_point:]
        
        return integrated
    
    def _generate_sheet_instances_sexp(self) -> str:
        """Generate S-expressions for all sheet instances"""
        lines = ['\n  ; ===== HIERARCHICAL SUBCIRCUIT BLOCKS =====\n']
        
        for sheet in self.sheet_instances:
            # Relative path from main schematic to subcircuit
            # KiCad uses (sheet_instances) to embed child sheets
            sheet_uuid = str(uuid.uuid4())
            
            sexp = (
                f'  (sheet_instance (sheetname "{sheet["name"]}") '
                f'(uuid "{sheet_uuid}")\n'
                f'    (file "{sheet["file"]}")\n'
                f'    (at {sheet["x"]} {sheet["y"]})\n'
                f'  )\n'
            )
            lines.append(sexp)
        
        return ''.join(lines)
    
    def save(self, output_path: str):
        """Save integrated schematic"""
        integrated = self.integrate()
        with open(output_path, 'w') as f:
            f.write(integrated)
        print(f"Wrote integrated schematic to {output_path}")


def create_extended_schematic():
    """
    Create extended PicAmpControl schematic with all subcircuit blocks.
    
    Layout:
    - Top-left: Input power (J2, U2, bypass caps) - EXISTING
    - Center-left: MCU (U1, MCLR) - EXISTING  
    - Center: ADC Pre-filter and Post-filter blocks (stacked)
    - Right-center: ADC Conditioning (temp/OCP/OD/drain)
    - Right-top: Comparator stage
    - Right-middle: Digital outputs
    - Right-bottom: I2C interface
    - Bottom-left: Encoder interface
    - Bottom-center: PTT input
    - Right: Fan control (existing)
    """
    
    main_sch = 'docs/hardware/project_schematic_package/generated/mcp-final/pic_amp_protection.kicad_sch'
    subcircuits_dir = 'out/subcircuits'
    
    integrator = HierarchicalIntegrator(main_sch, subcircuits_dir)
    
    # Add sheet instances in logical positions
    integrator.add_sheet_instance(
        'ADC_PreFilter', 
        'out/subcircuits/adc_prefilter.kicad_sch',
        x=320, y=80
    )
    
    integrator.add_sheet_instance(
        'ADC_PostFilter',
        'out/subcircuits/adc_postfilter.kicad_sch',
        x=320, y=180
    )
    
    integrator.add_sheet_instance(
        'ADC_Conditioning',
        'out/subcircuits/adc_conditioning.kicad_sch',
        x=420, y=100
    )
    
    integrator.add_sheet_instance(
        'Comparator',
        'out/subcircuits/comparator.kicad_sch',
        x=420, y=250
    )
    
    integrator.add_sheet_instance(
        'DigitalOutputs',
        'out/subcircuits/digital_outputs.kicad_sch',
        x=320, y=280
    )
    
    integrator.add_sheet_instance(
        'I2C_Interface',
        'out/subcircuits/i2c_interface.kicad_sch',
        x=420, y=320
    )
    
    integrator.add_sheet_instance(
        'Encoder',
        'out/subcircuits/encoder.kicad_sch',
        x=180, y=280
    )
    
    integrator.add_sheet_instance(
        'PTT_Input',
        'out/subcircuits/ptt_input.kicad_sch',
        x=180, y=360
    )
    
    output_sch = 'out/pic_amp_protection_extended.kicad_sch'
    integrator.save(output_sch)
    
    return output_sch


if __name__ == '__main__':
    output = create_extended_schematic()
    print(f"\n✓ Created extended schematic with subcircuit blocks")
    print(f"  Path: {output}")
    print(f"\nNext steps:")
    print(f"  1. Open {output} in KiCad")
    print(f"  2. Use 'Update Fields from Libraries' to load subcircuits")
    print(f"  3. Connect hierarchical pins via MCP tools:")
    print(f"     - wire_pins_to_net for power rails (+5V, GND)")
    print(f"     - connect_pins for signal paths (ADC_FWD_PRE, etc.)")
    print(f"  4. Run ERC to validate all connections")
