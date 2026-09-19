#!/usr/bin/env python3
"""
EasyEDA Pro JSON Validator

Validates that the generated JSON file matches EasyEDA Pro's expected format.
Also checks compatibility and provides detailed error reporting.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple


class EasyEDAValidator:
    """Validates EasyEDA Pro JSON format"""
    
    # Required top-level fields in EasyEDA Pro schematic
    REQUIRED_FIELDS = [
        'title',
        'docType',
        'version',
        'components',
        'nets',
    ]
    
    # Required component fields
    COMPONENT_REQUIRED = [
        'id',
        'title',
        'ref',
        'value',
        'x',
        'y'
    ]
    
    # Required net fields
    NET_REQUIRED = [
        'id',
        'name',
        'pinList'
    ]
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def validate_file(self, json_file: Path) -> bool:
        """Validate EasyEDA Pro JSON file"""
        
        if not json_file.exists():
            self.errors.append(f"File not found: {json_file}")
            return False
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON parsing error: {e}")
            return False
        except Exception as e:
            self.errors.append(f"File read error: {e}")
            return False
        
        # Validate top-level structure
        self._validate_top_level(data)
        
        # Validate components
        if 'components' in data:
            self._validate_components(data['components'])
        
        # Validate nets
        if 'nets' in data:
            self._validate_nets(data['nets'])
        
        # Cross-check component IDs in nets
        self._validate_cross_references(data)
        
        return len(self.errors) == 0
    
    def _validate_top_level(self, data: Dict) -> None:
        """Validate top-level schematic structure"""
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in data:
                self.errors.append(f"Missing required field: {field}")
            else:
                self.info.append(f"✓ {field}: {type(data[field]).__name__}")
        
        # Validate docType
        if data.get('docType') not in ['schematic', 'pcb']:
            self.warnings.append(f"Unexpected docType: {data.get('docType')}")
        
        # Validate version format
        version = data.get('version', '')
        if not version or not str(version).isdigit():
            self.warnings.append(f"Invalid version format: {version}")
        
        # Optional but recommended fields
        if 'metadata' not in data:
            self.warnings.append("Missing 'metadata' field (optional but recommended)")
        else:
            self.info.append(f"✓ Metadata: {data['metadata']}")
    
    def _validate_components(self, components: List[Dict]) -> None:
        """Validate component list"""
        
        self.info.append(f"Total components: {len(components)}")
        
        component_ids = set()
        for idx, comp in enumerate(components):
            # Check required fields
            missing = [f for f in self.COMPONENT_REQUIRED if f not in comp]
            if missing:
                self.errors.append(f"Component {idx} missing fields: {missing}")
            
            # Check for duplicate IDs
            comp_id = comp.get('id')
            if comp_id in component_ids:
                self.errors.append(f"Duplicate component ID: {comp_id}")
            component_ids.add(comp_id)
            
            # Validate coordinates are numeric
            try:
                x = float(comp.get('x', 0))
                y = float(comp.get('y', 0))
            except (ValueError, TypeError):
                self.errors.append(f"Component {idx} ({comp.get('title')}): Invalid coordinates")
            
            # Check for standard fields
            if not comp.get('title'):
                self.errors.append(f"Component {idx}: Missing designator/title")
        
        if len(component_ids) == len(components):
            self.info.append("✓ All component IDs unique")
    
    def _validate_nets(self, nets: List[Dict]) -> None:
        """Validate net list"""
        
        self.info.append(f"Total nets: {len(nets)}")
        
        net_ids = set()
        net_names = set()
        
        for idx, net in enumerate(nets):
            # Check required fields
            missing = [f for f in self.NET_REQUIRED if f not in net]
            if missing:
                self.errors.append(f"Net {idx} missing fields: {missing}")
            
            # Check for duplicate IDs and names
            net_id = net.get('id')
            net_name = net.get('name')
            
            if net_id in net_ids:
                self.errors.append(f"Duplicate net ID: {net_id}")
            net_ids.add(net_id)
            
            if net_name in net_names:
                self.errors.append(f"Duplicate net name: {net_name}")
            net_names.add(net_name)
            
            # Validate pinList
            pin_list = net.get('pinList', [])
            if not isinstance(pin_list, list):
                self.errors.append(f"Net '{net_name}': pinList must be a list")
            elif len(pin_list) < 1:
                self.warnings.append(f"Net '{net_name}': No pins connected")
            elif len(pin_list) < 2:
                self.warnings.append(f"Net '{net_name}': Only {len(pin_list)} pin connected")
            else:
                self.info.append(f"  Net '{net_name}': {len(pin_list)} pins")
        
        if len(net_ids) == len(nets):
            self.info.append("✓ All net IDs unique")
    
    def _validate_cross_references(self, data: Dict) -> None:
        """Validate that components referenced in nets exist"""
        
        components = data.get('components', [])
        nets = data.get('nets', [])
        
        # Build component ID map
        comp_id_map = {c.get('id'): c for c in components}
        
        for net in nets:
            net_name = net.get('name', 'UNKNOWN')
            pin_list = net.get('pinList', [])
            
            for pin in pin_list:
                comp_id = pin.get('componentId')
                if comp_id not in comp_id_map:
                    self.errors.append(f"Net '{net_name}': Component ID not found: {comp_id}")
    
    def print_results(self) -> None:
        """Print validation results"""
        
        print("\n" + "=" * 70)
        print("EasyEDA Pro JSON Validation Results")
        print("=" * 70)
        
        if self.info:
            print("\n[INFO]")
            for msg in self.info:
                print(f"  {msg}")
        
        if self.warnings:
            print("\n[WARNINGS]")
            for msg in self.warnings:
                print(f"  ⚠ {msg}")
        
        if self.errors:
            print("\n[ERRORS]")
            for msg in self.errors:
                print(f"  ✗ {msg}")
        else:
            print("\n[SUCCESS] ✓ All validations passed!")
        
        print("\n" + "=" * 70)
        print()
        
        if not self.errors:
            print("✓ File is ready to import into EasyEDA Pro")
            print()
            print("Next steps:")
            print("  1. Open EasyEDA Pro")
            print("  2. File → Import → Import EasyEDA File")
            print("  3. Select: out/picampcontrol_easyeda.json")
            print("  4. Schematic will render with components and wiring")
        else:
            print("✗ Fix errors above before importing")
        
        print()


def main():
    json_file = Path('out/picampcontrol_easyeda.json')
    
    validator = EasyEDAValidator()
    success = validator.validate_file(json_file)
    validator.print_results()
    
    exit(0 if success else 1)


if __name__ == '__main__':
    main()
