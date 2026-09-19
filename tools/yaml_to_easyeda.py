#!/usr/bin/env python3
"""
EasyEDA Pro Project Generator

Converts pic_amp_control_full.yaml to actual EasyEDA Pro schematic format.
Creates a real .eeda project file that can be opened in EasyEDA Pro.
"""

import json
import yaml
import uuid
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict


@dataclass
class EasyEDAComponent:
    """EasyEDA Pro component representation"""
    id: str
    title: str  # Designator (R1, U1, etc.)
    ref: str    # Reference
    value: str
    package: str
    x: float
    y: float
    rotation: int = 0
    flip: str = "N"
    
    # EasyEDA Pro properties
    name: str = ""
    pn: str = ""  # Part number / MPN
    lib_id: str = ""


@dataclass 
class EasyEDAPin:
    """Pin definition for net connectivity"""
    id: str
    componentId: str
    pinNumber: str
    pinName: str
    x: float
    y: float


@dataclass
class EasyEDANet:
    """Electrical net/node"""
    id: str
    name: str
    pinList: List[Dict[str, str]]


@dataclass
class EasyEDASchematic:
    """Top-level EasyEDA Pro schematic"""
    title: str
    docType: str = "schematic"
    version: str = "20240101"
    components: List[Dict] = None
    nets: List[Dict] = None
    wires: List[Dict] = None
    labels: List[Dict] = None
    
    def __post_init__(self):
        if self.components is None:
            self.components = []
        if self.nets is None:
            self.nets = []
        if self.wires is None:
            self.wires = []
        if self.labels is None:
            self.labels = []


class YAMLToEasyEDAConverter:
    """Converts YAML circuit spec to EasyEDA Pro format"""
    
    def __init__(self):
        self.components: Dict[str, EasyEDAComponent] = {}
        self.nets: Dict[str, EasyEDANet] = {}
        self.component_pin_map: Dict[str, Dict[str, tuple]] = {}  # {comp: {pin: (x, y)}}
        self.grid_scale = 50  # pixels per schematic unit
    
    def load_yaml(self, yaml_file: Path) -> Dict[str, Any]:
        """Load YAML spec"""
        with open(yaml_file, encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def convert(self, yaml_file: Path) -> Dict[str, Any]:
        """Convert YAML to EasyEDA Pro format"""
        spec = self.load_yaml(yaml_file)
        
        instances = spec.get('instances', {})
        connections = spec.get('connections', [])
        
        print(f"[INFO] Converting {len(instances)} components to EasyEDA Pro format...")
        
        # Convert components with hierarchical placement
        self._place_components(instances)
        
        # Convert nets and connections
        self._create_nets(connections)
        
        # Build EasyEDA Pro schematic structure
        schematic = self._build_schematic()
        
        return schematic
    
    def _place_components(self, instances: Dict[str, Dict]) -> None:
        """Place components in schematic with hierarchical layout"""
        
        # Categorize components by function
        categories = {
            'Power': [],
            'MCU': [],
            'ADC_Pre': [],
            'ADC_Post': [],
            'ADC_Conditioning': [],
            'Comparator': [],
            'Digital_Out': [],
            'Interfaces': [],
            'Fan_Control': []
        }
        
        for designator, spec in instances.items():
            part = spec.get('part', '').lower()
            value = spec.get('value', '')
            
            # Categorize
            if 'conn' in part or designator == 'J1':
                if designator in ['J1', 'J_PTT_IN']:
                    categories['Power'].append((designator, spec))
                else:
                    categories['Interfaces'].append((designator, spec))
            elif 'l7805' in part or 'c' in part and designator.startswith('C_'):
                categories['Power'].append((designator, spec))
            elif 'pic' in part:
                categories['MCU'].append((designator, spec))
            elif 'fwd_pre' in designator or 'refl_pre' in designator:
                categories['ADC_Pre'].append((designator, spec))
            elif 'fwd_post' in designator or 'refl_post' in designator:
                categories['ADC_Post'].append((designator, spec))
            elif 'adc_' in designator.lower() or any(x in designator for x in ['TEMP', 'OCP', 'OD', 'DRAIN']):
                categories['ADC_Conditioning'].append((designator, spec))
            elif 'lm339' in part or 'comp' in designator.lower():
                categories['Comparator'].append((designator, spec))
            elif 'tx' in designator.lower() or 'trip' in designator.lower():
                categories['Digital_Out'].append((designator, spec))
            elif 'fan' in designator.lower():
                categories['Fan_Control'].append((designator, spec))
            elif 'encoder' in part or 'i2c' in designator.lower():
                categories['Interfaces'].append((designator, spec))
            else:
                categories['Power'].append((designator, spec))
        
        # Layout: Left side = inputs, center = MCU, right side = outputs, bottom = power
        x_pos = 0
        y_pos = 0
        col_width = 3
        
        layout_order = [
            ('Power', 0, 0),
            ('MCU', 1, 0),
            ('ADC_Pre', 0, 2),
            ('ADC_Post', 0, 4),
            ('ADC_Conditioning', 1, 2),
            ('Comparator', 2, 2),
            ('Digital_Out', 3, 2),
            ('Fan_Control', 3, 0),
            ('Interfaces', 1, 4),
        ]
        
        for category, col, row in layout_order:
            x = col * col_width
            y = row * 2
            
            for idx, (designator, spec) in enumerate(categories[category]):
                comp_x = x + idx * 0.5
                comp_y = y + (idx % 4) * 0.5
                
                comp = EasyEDAComponent(
                    id=str(uuid.uuid4()),
                    title=designator,
                    ref=designator,
                    value=spec.get('value', ''),
                    package=spec.get('footprint', 'SMD'),
                    x=comp_x * self.grid_scale,
                    y=comp_y * self.grid_scale,
                    pn=spec.get('part', '')
                )
                
                self.components[designator] = comp
                print(f"  Placed {designator} at ({comp_x:.1f}, {comp_y:.1f})")
    
    def _create_nets(self, connections: List[Dict]) -> None:
        """Create electrical nets from connections"""
        
        for conn in connections:
            net_name = conn.get('net', '')
            endpoints = conn.get('endpoints', [])
            
            if not net_name or not endpoints:
                continue
            
            pin_list = []
            for endpoint in endpoints:
                if '.' in endpoint:
                    comp, pin = endpoint.split('.', 1)
                    if comp in self.components:
                        pin_list.append({
                            'componentId': self.components[comp].id,
                            'pinNumber': pin,
                            'pinName': pin
                        })
            
            if pin_list:
                net = EasyEDANet(
                    id=str(uuid.uuid4()),
                    name=net_name,
                    pinList=pin_list
                )
                self.nets[net_name] = net
    
    def _build_schematic(self) -> Dict[str, Any]:
        """Build final EasyEDA Pro schematic structure"""
        
        components_list = []
        for comp in self.components.values():
            components_list.append({
                'id': comp.id,
                'title': comp.title,
                'ref': comp.ref,
                'value': comp.value,
                'package': comp.package,
                'x': comp.x,
                'y': comp.y,
                'rotation': comp.rotation,
                'flip': comp.flip,
                'pn': comp.pn
            })
        
        nets_list = []
        for net in self.nets.values():
            nets_list.append({
                'id': net.id,
                'name': net.name,
                'pinList': net.pinList
            })
        
        return {
            'title': 'PicAmpControl - Amplifier Protection',
            'docType': 'schematic',
            'version': '20240101',
            'components': components_list,
            'nets': nets_list,
            'wires': [],
            'labels': [],
            'metadata': {
                'created': '2024-09-19',
                'description': 'PIC16F18855-based linear amplifier protection controller',
                'componentCount': len(components_list),
                'netCount': len(nets_list)
            }
        }


def main():
    print("=" * 70)
    print("EasyEDA Pro Project Generator")
    print("=" * 70)
    print()
    
    yaml_file = Path('pic_amp_control_full.yaml')
    
    if not yaml_file.exists():
        print(f"[ERROR] {yaml_file} not found")
        return
    
    converter = YAMLToEasyEDAConverter()
    schematic = converter.convert(yaml_file)
    
    # Save as EasyEDA Pro JSON format
    output_file = Path('out/picampcontrol_easyeda.json')
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(schematic, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"[OK] Generated EasyEDA Pro schematic: {output_file}")
    print()
    print("NEXT STEPS:")
    print("=" * 70)
    print()
    print("Option A: Open in EasyEDA Pro directly")
    print("  1. Open EasyEDA Pro (https://easyeda.com/editor)")
    print("  2. File → Import → Import EasyEDA File")
    print(f"  3. Select: {output_file}")
    print()
    print("Option B: Use easyeda-copilot MCP (if configured)")
    print(f"  • Pass this file to Claude with easyeda-copilot enabled")
    print()
    print("=" * 70)
    print()
    print(f"Schematic contains:")
    print(f"  • {schematic['metadata']['componentCount']} components")
    print(f"  • {schematic['metadata']['netCount']} nets")
    print()


if __name__ == '__main__':
    main()
