#!/usr/bin/env python3
"""
Hierarchical Sheet Integration Tool

Manually constructs the sheet_instance S-expressions and integrates them
into the main KiCad schematic.
"""

import re
import uuid
from pathlib import Path

def add_sheet_instances_to_schematic(main_sch_path: str, output_path: str = None):
    """
    Add hierarchical sheet instances to the main schematic.
    
    Each sheet_instance references a subcircuit file and defines connection points.
    """
    
    if output_path is None:
        output_path = main_sch_path.replace('.kicad_sch', '_with_sheets.kicad_sch')
    
    with open(main_sch_path, 'r') as f:
        content = f.read()
    
    # Find insertion point (before final closing paren)
    insertion_idx = content.rfind('\n)')
    if insertion_idx < 0:
        raise ValueError("Cannot find closing paren in schematic")
    
    # Define sheet instances with their positions and pin connections
    sheet_instances = [
        {
            'name': 'ADC_PreFilter',
            'file': '../../../out/subcircuits/adc_prefilter.kicad_sch',
            'x': 320,
            'y': 80,
            'pins': ['+5V', 'GND', 'ADC_FWD_PRE', 'ADC_REFL_PRE']
        },
        {
            'name': 'ADC_PostFilter',
            'file': '../../../out/subcircuits/adc_postfilter.kicad_sch',
            'x': 320,
            'y': 180,
            'pins': ['+5V', 'GND', 'ADC_FWD_POST', 'ADC_REFL_POST']
        },
        {
            'name': 'ADC_Conditioning',
            'file': '../../../out/subcircuits/adc_conditioning.kicad_sch',
            'x': 420,
            'y': 100,
            'pins': ['+5V', 'GND', 'ADC_TEMP', 'ADC_OCP', 'ADC_OD', 'ADC_DRAIN']
        },
        {
            'name': 'Comparator',
            'file': '../../../out/subcircuits/comparator.kicad_sch',
            'x': 420,
            'y': 250,
            'pins': ['+5V', 'GND', 'ADC_OCP', 'HARD_FAULT']
        },
        {
            'name': 'DigitalOutputs',
            'file': '../../../out/subcircuits/digital_outputs.kicad_sch',
            'x': 320,
            'y': 280,
            'pins': ['+5V', 'GND', 'TX', 'TX_VCC', 'TX_BIAS', 'TRIP']
        },
        {
            'name': 'I2C_Interface',
            'file': '../../../out/subcircuits/i2c_interface.kicad_sch',
            'x': 420,
            'y': 320,
            'pins': ['+5V', 'GND', 'I2C_SDA', 'I2C_SCL']
        },
        {
            'name': 'Encoder',
            'file': '../../../out/subcircuits/encoder.kicad_sch',
            'x': 180,
            'y': 280,
            'pins': ['+5V', 'GND', 'ENC_A', 'ENC_B', 'ENC_SW']
        },
        {
            'name': 'PTT_Input',
            'file': '../../../out/subcircuits/ptt_input.kicad_sch',
            'x': 180,
            'y': 360,
            'pins': ['+5V', 'GND', 'PTT_IN']
        },
    ]
    
    # Generate sheet_instance S-expressions
    sheet_sexp = []
    sheet_sexp.append('\n  ; ===== HIERARCHICAL SUBCIRCUITS =====')
    
    for sheet in sheet_instances:
        sheet_uuid = str(uuid.uuid4())
        
        # Build sheet_instance S-expression
        sexp = f'\n  (sheet_instance "{sheet["name"]}" (at {sheet["x"]} {sheet["y"]})\n'
        sexp += f'    (uuid "{sheet_uuid}")\n'
        sexp += f'    (file "{sheet["file"]}")\n'
        
        # Add pin connections
        pin_idx = 1
        for pin_name in sheet['pins']:
            pin_uuid = str(uuid.uuid4())
            sexp += f'    (pin "{pin_name}" (uuid "{pin_uuid}") (net "{pin_name}"))\n'
            pin_idx += 1
        
        sexp += '  )'
        sheet_sexp.append(sexp)
    
    # Insert before closing paren
    modified = content[:insertion_idx] + '\n'.join(sheet_sexp) + content[insertion_idx:]
    
    with open(output_path, 'w') as f:
        f.write(modified)
    
    print(f"✓ Integrated {len(sheet_instances)} hierarchical sheets")
    print(f"  Output: {output_path}")
    print(f"\nSheet instances added:")
    for sheet in sheet_instances:
        print(f"  • {sheet['name']:20} at ({sheet['x']:3}, {sheet['y']:3})")
    
    return output_path


if __name__ == '__main__':
    import sys
    
    main_sch = sys.argv[1] if len(sys.argv) > 1 else \
        'docs/hardware/project_schematic_package/generated/mcp-final/pic_amp_protection.kicad_sch'
    
    output = add_sheet_instances_to_schematic(main_sch)
    
    print(f"\n✓ Created: {output}")
    print(f"\nNOTE: Subcircuit files must be opened in KiCad to finalize connections.")
    print(f"      After opening in KiCad, wires will auto-connect via global labels.")
