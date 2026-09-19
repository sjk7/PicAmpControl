#!/usr/bin/env python3
"""
Generate clean KiCad subcircuit files for hierarchical schematic structure.
All components will use global labels for power/signal connections.
"""

import uuid

def gen_uuid():
    return str(uuid.uuid4())

# Template for each subcircuit
subcircuits = {
    'adc_prefilter': {
        'title': 'ADC Pre-Filter (Forward & Reflected Power)',
        'components': [
            ('Device:R', 'R1', '100k', 100, 80),
            ('Device:R', 'R2', '10k', 100, 140),
            ('Device:C', 'C1', '10nF', 150, 110),
            ('Device:R', 'R3', '100k', 200, 160),
            ('Device:R', 'R4', '10k', 200, 220),
            ('Device:C', 'C2', '10nF', 250, 190),
        ],
        'labels': [
            ('+5V', 20, 50, 'passive'),
            ('GND', 20, 240, 'passive'),
            ('ADC_FWD_PRE', 280, 100, 'output'),
            ('ADC_REFL_PRE', 280, 180, 'output'),
        ]
    },
    'adc_postfilter': {
        'title': 'ADC Post-Filter (Forward & Reflected Power)',
        'components': [
            ('Device:R', 'R1', '100k', 100, 80),
            ('Device:R', 'R2', '10k', 100, 140),
            ('Device:C', 'C1', '10nF', 150, 110),
            ('Device:R', 'R3', '100k', 200, 160),
            ('Device:R', 'R4', '10k', 200, 220),
            ('Device:C', 'C2', '10nF', 250, 190),
        ],
        'labels': [
            ('+5V', 20, 50, 'passive'),
            ('GND', 20, 240, 'passive'),
            ('ADC_FWD_POST', 280, 100, 'output'),
            ('ADC_REFL_POST', 280, 180, 'output'),
        ]
    },
    'adc_conditioning': {
        'title': 'ADC Conditioning (Temp/OCP/OD/Drain)',
        'components': [
            ('Device:R', 'R_TEMP', '10k', 100, 80),
            ('Device:R', 'R_TEMP_PU', '10k', 150, 80),
            ('Device:C', 'C_TEMP', '10nF', 200, 80),
            ('Device:R', 'R_OCP_H', '47k', 100, 130),
            ('Device:R', 'R_OCP_L', '10k', 150, 130),
            ('Device:C', 'C_OCP', '10nF', 200, 130),
            ('Device:R', 'R_OD_H', '100k', 100, 180),
            ('Device:R', 'R_OD_L', '10k', 150, 180),
            ('Device:C', 'C_OD', '10nF', 200, 180),
            ('Device:R', 'R_DRAIN_H', '200k', 100, 230),
            ('Device:R', 'R_DRAIN_L', '10k', 150, 230),
            ('Device:C', 'C_DRAIN', '10nF', 200, 230),
        ],
        'labels': [
            ('+5V', 20, 50, 'passive'),
            ('GND', 20, 280, 'passive'),
            ('ADC_TEMP', 280, 80, 'output'),
            ('ADC_OCP', 280, 130, 'output'),
            ('ADC_OD', 280, 180, 'output'),
            ('ADC_DRAIN', 280, 230, 'output'),
        ]
    },
    'comparator': {
        'title': 'Overcurrent Comparator Stage',
        'components': [
            ('Amplifier_Operational:LM339', 'U1', 'LM339', 150, 100),
            ('Device:R', 'R_FB', '100k', 100, 80),
            ('Device:R', 'R_REF', '10k', 100, 120),
        ],
        'labels': [
            ('+5V', 20, 50, 'passive'),
            ('GND', 20, 150, 'passive'),
            ('ADC_OCP', 20, 100, 'input'),
            ('HARD_FAULT', 280, 100, 'output'),
        ]
    },
    'digital_outputs': {
        'title': 'Digital Control Outputs',
        'components': [
            ('Device:R', 'R_TX_PD', '10k', 100, 80),
            ('Device:R', 'R_TX_VCC_PD', '10k', 100, 110),
            ('Device:R', 'R_TX_BIAS_PD', '10k', 100, 140),
            ('Device:R', 'R_TRIP_PD', '10k', 100, 170),
        ],
        'labels': [
            ('+5V', 20, 50, 'passive'),
            ('GND', 20, 200, 'passive'),
            ('TX', 20, 80, 'input'),
            ('TX_VCC', 20, 110, 'input'),
            ('TX_BIAS', 20, 140, 'input'),
            ('TRIP', 20, 170, 'input'),
        ]
    },
    'i2c_interface': {
        'title': 'I2C LCD Interface',
        'components': [
            ('Device:R', 'R_SDA_PU', '4.7k', 100, 100),
            ('Device:R', 'R_SCL_PU', '4.7k', 100, 130),
            ('Connector_Generic:Conn_01x04', 'J1', 'I2C_LCD', 200, 115),
        ],
        'labels': [
            ('+5V', 20, 50, 'passive'),
            ('GND', 20, 150, 'passive'),
            ('I2C_SDA', 20, 100, 'bidirectional'),
            ('I2C_SCL', 20, 130, 'bidirectional'),
        ]
    },
    'encoder': {
        'title': 'Rotary Encoder Interface',
        'components': [
            ('Device:R', 'R_A_PU', '10k', 100, 100),
            ('Device:R', 'R_B_PU', '10k', 100, 130),
            ('Device:R', 'R_SW_PU', '10k', 100, 160),
            ('Device:Rotary_Encoder_EC11', 'SW1', 'EC11', 200, 130),
        ],
        'labels': [
            ('+5V', 20, 50, 'passive'),
            ('GND', 20, 200, 'passive'),
            ('ENC_A', 20, 100, 'input'),
            ('ENC_B', 20, 130, 'input'),
            ('ENC_SW', 20, 160, 'input'),
        ]
    },
    'ptt_input': {
        'title': 'PTT Input',
        'components': [
            ('Device:R', 'R_PTT_PD', '10k', 100, 100),
            ('Connector_Generic:Conn_01x02', 'J1', 'PTT_INPUT', 200, 100),
        ],
        'labels': [
            ('+5V', 20, 50, 'passive'),
            ('GND', 20, 150, 'passive'),
            ('PTT_IN', 20, 100, 'input'),
        ]
    },
}

def generate_subcircuit(name, spec):
    """Generate KiCad S-expression for one subcircuit"""
    lines = [
        '(kicad_sch (version 20240108)',
        f'  (uuid "{gen_uuid()}")',
        '  (paper "A4")',
        '  (title_block',
        f'    (title "{spec["title"]}")',
        '    (date "2026-09-19")',
        '  )',
    ]
    
    # Add components
    for lib_id, ref, value, x, y in spec['components']:
        comp_uuid = gen_uuid()
        lines.append(f'  (symbol (lib_id "{lib_id}") (at {x} {y} 0)')
        lines.append(f'    (uuid "{comp_uuid}")')
        lines.append(f'    (property "Reference" "{ref}" (at {x} {y-2} 0)')
        lines.append(f'      (effects (font (size 1.27 1.27) (thickness 0.15)))')
        lines.append(f'    )')
        lines.append(f'    (property "Value" "{value}" (at {x} {y+2} 0)')
        lines.append(f'      (effects (font (size 1.27 1.27) (thickness 0.15)))')
        lines.append(f'    )')
        lines.append(f'  )')
    
    # Add global labels (power and signals)
    for label, x, y, shape in spec['labels']:
        label_uuid = gen_uuid()
        justify = 'right' if x < 150 else 'left'
        lines.append(f'  (global_label "{label}" (shape {shape}) (at {x} {y} 0)')
        lines.append(f'    (effects (font (size 1.27 1.27)) (justify {justify}))')
        lines.append(f'    (uuid "{label_uuid}")')
        lines.append(f'  )')
    
    lines.append(')')
    return '\n'.join(lines)

# Generate all subcircuits
for name, spec in subcircuits.items():
    filepath = f'out/subcircuits/{name}.kicad_sch'
    content = generate_subcircuit(name, spec)
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"Generated {filepath}")

print(f"\n✓ Created {len(subcircuits)} clean subcircuit files")
print(f"  All use global_label for power/signal connections")
print(f"  Ready for MCP hierarchical sheet integration")
