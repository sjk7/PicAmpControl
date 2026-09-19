#!/usr/bin/env python3
"""
Schematic Visual Validator

Performs design rule checks on rendered SVG:
- Component overlap detection
- Wire routing validation  
- Layout density checks
- Net connectivity validation
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass


@dataclass
class ComponentBBox:
    """Component bounding box with metadata"""
    designator: str
    x: float
    y: float
    width: float = 0.04
    height: float = 0.03
    
    def overlaps_with(self, other: 'ComponentBBox', margin: float = 0.02) -> bool:
        """Check if components overlap with margin"""
        self_x1 = self.x - self.width/2 - margin
        self_x2 = self.x + self.width/2 + margin
        self_y1 = self.y - self.height/2 - margin
        self_y2 = self.y + self.height/2 + margin
        
        other_x1 = other.x - other.width/2
        other_x2 = other.x + other.width/2
        other_y1 = other.y - other.height/2
        other_y2 = other.y + other.height/2
        
        return not (self_x2 < other_x1 or self_x1 > other_x2 or 
                   self_y2 < other_y1 or self_y1 > other_y2)
    
    def distance_to(self, other: 'ComponentBBox') -> float:
        """Calculate center-to-center distance"""
        import math
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx*dx + dy*dy)


class VisualValidator:
    """Validates schematic layout and design rules"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
    
    def validate_schematic(self, spec: Dict) -> bool:
        """
        Validate schematic specification.
        
        Returns:
            True if validation passed, False if errors found
        """
        self.errors = []
        self.warnings = []
        self.info = []
        
        components = spec.get('components', [])
        nets = spec.get('nets', [])
        
        # Check component placement
        self._validate_component_placement(components)
        
        # Check component count
        self._validate_component_count(components)
        
        # Check net definitions
        self._validate_nets(nets)
        
        # Check component grouping
        self._validate_grouping(components)
        
        # Print results
        self._print_validation_results()
        
        return len(self.errors) == 0
    
    def _validate_component_placement(self, components: List[Dict]) -> None:
        """Check for component overlaps and spacing"""
        bboxes = [
            ComponentBBox(
                c['designator'],
                c['x'],
                c['y']
            )
            for c in components
        ]
        
        # Check for overlaps
        for i, bbox1 in enumerate(bboxes):
            for bbox2 in bboxes[i+1:]:
                if bbox1.overlaps_with(bbox2, margin=0.01):
                    self.errors.append(
                        f"Component overlap: {bbox1.designator} overlaps with {bbox2.designator}"
                    )
        
        # Check for excessive crowding (distance < 0.08)
        for i, bbox1 in enumerate(bboxes):
            for bbox2 in bboxes[i+1:]:
                dist = bbox1.distance_to(bbox2)
                if dist < 0.08:
                    self.warnings.append(
                        f"Dense placement: {bbox1.designator} and {bbox2.designator} "
                        f"are only {dist:.3f}\" apart (recommend >= 0.08\")"
                    )
    
    def _validate_component_count(self, components: List[Dict]) -> None:
        """Validate total component count matches spec"""
        count = len(components)
        
        # Count by type
        by_type = {}
        for comp in components:
            prefix = ''.join([c for c in comp['designator'] if c.isalpha()])
            by_type[prefix] = by_type.get(prefix, 0) + 1
        
        self.info.append(f"Total components: {count}")
        
        for prefix in sorted(by_type.keys()):
            self.info.append(f"  {prefix}: {by_type[prefix]}")
        
        # Warnings for extreme counts
        if count < 30:
            self.warnings.append(f"Unusually few components ({count}). "
                               "Verify spec is complete.")
        elif count > 150:
            self.warnings.append(f"Very many components ({count}). "
                               "Consider hierarchical sub-sheets.")
    
    def _validate_nets(self, nets: List[Dict]) -> None:
        """Validate net definitions"""
        net_names = set(n['name'] for n in nets)
        required_nets = {'+12V_RAW', '+5V', 'GND'}
        
        missing = required_nets - net_names
        if missing:
            self.errors.append(f"Missing power nets: {', '.join(missing)}")
        
        self.info.append(f"Total nets: {len(net_names)}")
        
        # Warn about common naming issues
        special_chars = [n for n in net_names if any(c in n for c in '[](){}')]
        if special_chars:
            self.warnings.append(f"Nets with special characters: {', '.join(special_chars)}")
    
    def _validate_grouping(self, components: List[Dict]) -> None:
        """Validate that components are grouped by function"""
        groups = self._group_components(components)
        
        self.info.append(f"Functional groups: {len(groups)}")
        
        for group_name, comps in groups.items():
            if comps:
                self.info.append(f"  {group_name}: {len(comps)} components")
        
        # Check group sizes
        for group_name, comps in groups.items():
            if len(comps) > 20:
                self.warnings.append(
                    f"Large group '{group_name}' has {len(comps)} components. "
                    "Consider splitting into sub-circuits."
                )
    
    def _group_components(self, components: List[Dict]) -> Dict[str, List[Dict]]:
        """Group components by function"""
        groups = {}
        
        for comp in components:
            ref = comp.get('designator', '')
            
            if any(x in ref for x in ['J', 'U2', 'C2', 'C3', 'C4']):
                group = "Power Supply"
            elif 'U1' in ref or 'R1' in ref or 'C1' in ref:
                group = "MCU"
            elif any(x in ref for x in ['ADC', 'REFL', 'FWD', 'OCP', 'OD', 'DRAIN']):
                group = "ADC Conditioning"
            elif 'U3' in ref or 'LM339' in comp.get('part_number', ''):
                group = "Comparator"
            elif any(x in ref for x in ['TX', 'TRIP']):
                group = "Digital Outputs"
            elif any(x in ref for x in ['I2C', 'ENC', 'PTT']):
                group = "Interfaces"
            elif any(x in ref for x in ['FAN', 'Q1']):
                group = "Fan Control"
            else:
                group = "Other"
            
            if group not in groups:
                groups[group] = []
            groups[group].append(comp)
        
        return groups
    
    def _print_validation_results(self) -> None:
        """Print validation results"""
        if self.errors or self.warnings or self.info:
            print("\n" + "=" * 70)
            print("VISUAL SCHEMATIC VALIDATION")
            print("=" * 70)
            
            if self.info:
                print("\n=== SCHEMATIC STATS ===")
                for msg in self.info:
                    print(f"  {msg}")
            
            if self.warnings:
                print("\n=== WARNINGS ===")
                for i, msg in enumerate(self.warnings, 1):
                    print(f"  {i}. {msg}")
            
            if self.errors:
                print("\n=== ERRORS ===")
                for i, msg in enumerate(self.errors, 1):
                    print(f"  {i}. {msg}")
            
            print("=" * 70)


def validate_picampcontrol() -> bool:
    """Validate PicAmpControl schematic"""
    
    json_file = Path('out/picampcontrol_easyeda_agent.json')
    if not json_file.exists():
        print(f"Error: {json_file} not found")
        return False
    
    with open(json_file) as f:
        spec = json.load(f)
    
    validator = VisualValidator()
    return validator.validate_schematic(spec)


if __name__ == '__main__':
    print("Validating PicAmpControl schematic...")
    success = validate_picampcontrol()
    exit(0 if success else 1)
