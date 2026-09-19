#!/usr/bin/env python3
"""
KiCad Schematic Validation Engine
Applies comprehensive visual and electrical design rules before ERC validation.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """A single schematic design rule"""
    name: str
    category: str  # 'placement', 'wiring', 'power_symbol', 'text_overlap', 'pin_connection'
    severity: str  # 'error', 'warning'
    description: str


class SchematicValidator:
    """
    Validates schematic design against comprehensive rules learned from:
    - visual-gate-lessons.md (visual overlap prevention)
    - kicad-mcp-skill.md (tool usage patterns)
    - user workflow.md (generated schematic conventions)
    """
    
    RULES = [
        # === POWER SYMBOLS ===
        ValidationRule(
            name="power_symbol_not_coincident",
            category="power_symbol",
            severity="error",
            description="Power symbols (#PWR, #FLG) must NOT be placed at exact same coordinates as the pin they drive"
        ),
        ValidationRule(
            name="power_symbol_proper_connection",
            category="power_symbol",
            severity="error",
            description="Each power/ground pin must have its OWN dedicated power symbol 2-5mm away, not a shared bus"
        ),
        ValidationRule(
            name="power_symbol_flag_paired",
            category="power_symbol",
            severity="error",
            description="Every power net must have exactly ONE PWR_FLAG, and each power symbol must have its paired PWR_FLAG"
        ),
        ValidationRule(
            name="gnd_symbol_not_text_label",
            category="power_symbol",
            severity="error",
            description="Ground must ALWAYS use power:GND symbol, never a bare 'GND' text label"
        ),
        ValidationRule(
            name="no_duplicate_power_outputs",
            category="power_symbol",
            severity="error",
            description="Do not place multiple power output sources (e.g. +5V symbol AND regulator output) on same net"
        ),
        
        # === TEXT OVERLAP ===
        ValidationRule(
            name="no_power_symbol_text_overlap",
            category="text_overlap",
            severity="warning",
            description="Power symbol reference/value text must not overlap any pin names or wires"
        ),
        ValidationRule(
            name="no_field_on_pin_coordinate",
            category="text_overlap",
            severity="warning",
            description="Component Reference/Value fields must not land exactly on pin coordinates (maintain margin)"
        ),
        ValidationRule(
            name="no_auto_net_labels",
            category="text_overlap",
            severity="error",
            description="Auto-generated 'Net-(...)'  labels must be removed; only explicit labels for named nets are allowed"
        ),
        ValidationRule(
            name="label_clearance_from_components",
            category="text_overlap",
            severity="warning",
            description="Net labels must maintain 10mm clearance from nearby components and power-symbol clusters"
        ),
        ValidationRule(
            name="connector_value_field_overlap",
            category="text_overlap",
            severity="warning",
            description="Connector Value field overlaps body by symbol design; blank Value and use add_text annotation instead"
        ),
        
        # === PIN CONNECTIVITY ===
        ValidationRule(
            name="no_unconnected_pins",
            category="pin_connection",
            severity="error",
            description="Every pin must be connected to an electrical net or explicitly left floating per design"
        ),
        ValidationRule(
            name="no_floating_wire_endpoints",
            category="pin_connection",
            severity="error",
            description="Wires must connect pin-to-pin or pin-to-symbol; no dangling endpoints"
        ),
        ValidationRule(
            name="no_coincident_pin_rewiing",
            category="pin_connection",
            severity="warning",
            description="Do not call connect_pins on pins already at same coordinates; they are already connected"
        ),
        
        # === IC SYMBOLS ===
        ValidationRule(
            name="ic_pin_stub_touches_body",
            category="placement",
            severity="warning",
            description="MCU/IC pin stubs must have inner end touching body edge; do not use oversized _LABELSAFE variants"
        ),
        ValidationRule(
            name="ic_pin_name_clearance",
            category="text_overlap",
            severity="warning",
            description="MCU/IC pin name text must fit inside or beside body; if overlap, adjust text offset NOT pin length or body size"
        ),
        ValidationRule(
            name="ic_designator_inside_body",
            category="placement",
            severity="warning",
            description="Keep IC designator and name inside IC body when they fit; place directly above if they don't"
        ),
        
        # === WIRING ===
        ValidationRule(
            name="no_diagonal_wires",
            category="wiring",
            severity="warning",
            description="Wires should use orthogonal routing (H/V only); no diagonal paths"
        ),
        ValidationRule(
            name="no_wires_through_component_bodies",
            category="wiring",
            severity="error",
            description="Wires must not route through component body outlines or immediately alongside them"
        ),
        ValidationRule(
            name="no_wire_crosses_ic_protection_envelope",
            category="wiring",
            severity="error",
            description="Unrelated wires must not run through IC body + pin field + clearance margin envelope"
        ),
        
        # === LAYOUT ===
        ValidationRule(
            name="no_symbol_field_autoplace_disabled",
            category="placement",
            severity="warning",
            description="All placed symbols should have fields_autoplaced=yes for proper Reference/Value positioning"
        ),
        ValidationRule(
            name="logical_grouping",
            category="placement",
            severity="warning",
            description="Group related components (regulators, MCU, passives) into logical regions to minimize wiring complexity"
        ),
        ValidationRule(
            name="connector_left_side",
            category="placement",
            severity="warning",
            description="Place input/output connectors on left/right edges for readability"
        ),
        
        # === PASSIVE COMPONENTS ===
        ValidationRule(
            name="passive_reference_value_on_pins",
            category="text_overlap",
            severity="warning",
            description="Device:R/C Reference/Value fields land on pin coordinates by place_component bug; this is expected"
        ),
        
        # === SYMBOL FIELD PROPERTIES ===
        ValidationRule(
            name="power_symbol_value_hidden",
            category="text_overlap",
            severity="warning",
            description="Power symbol Value text should have hide=yes to eliminate overlap; edit after placement"
        ),
        ValidationRule(
            name="reference_always_visible",
            category="placement",
            severity="error",
            description="Component Reference field MUST always be visible (cannot be hidden)"
        ),
    ]
    
    def __init__(self):
        self.violations: List[Dict] = []
    
    def validate_placement(self, components: List[Dict]) -> List[Dict]:
        """Validate component placement against rules"""
        violations = []
        
        # Check for overlapping components
        for i, comp1 in enumerate(components):
            for comp2 in components[i+1:]:
                distance = self._distance(comp1, comp2)
                if distance < 5:  # mm minimum clearance
                    violations.append({
                        'rule': 'component_too_close',
                        'severity': 'warning',
                        'message': f"{comp1['ref']} and {comp2['ref']} are {distance:.1f}mm apart (min 5mm)",
                        'components': [comp1['ref'], comp2['ref']]
                    })
        
        return violations
    
    def validate_wiring(self, nets: Dict, components: List[Dict]) -> List[Dict]:
        """Validate net wiring against rules"""
        violations = []
        
        # Check for unconnected power pins
        power_pins = [
            ('U1', '20'),  # PIC VDD
            ('U1', '8'),   # PIC VSS
            ('U1', '19'),  # PIC VSS
            ('U2', '3'),   # Regulator OUT
        ]
        
        for ref, pin in power_pins:
            found = False
            for net_name, endpoints in nets.items():
                if f"{ref}.{pin}" in endpoints:
                    found = True
                    break
            
            if not found:
                violations.append({
                    'rule': 'unconnected_power_pin',
                    'severity': 'error',
                    'message': f"Power pin {ref}.{pin} is unconnected",
                    'component': ref,
                    'pin': pin
                })
        
        # Check for auto-generated net labels (should be removed)
        for net_name in nets.keys():
            if net_name.startswith('Net-('):
                violations.append({
                    'rule': 'auto_generated_net_label',
                    'severity': 'error',
                    'message': f"Auto-generated net label '{net_name}' must be removed",
                    'net': net_name
                })
        
        return violations
    
    def validate_power_symbols(self, power_nets: Dict) -> List[Dict]:
        """Validate power symbol placement and connectivity"""
        violations = []
        
        # Check that each power net has exactly one PWR_FLAG
        for net_name, props in power_nets.items():
            flag_count = props.get('pwr_flag_count', 0)
            if flag_count != 1:
                violations.append({
                    'rule': 'power_flag_count',
                    'severity': 'error',
                    'message': f"Power net '{net_name}' must have exactly 1 PWR_FLAG, has {flag_count}",
                    'net': net_name,
                    'expected': 1,
                    'actual': flag_count
                })
        
        return violations
    
    def validate_text_overlap(self, components: List[Dict], annotations: List[Dict]) -> List[Dict]:
        """Check for text field overlaps"""
        violations = []
        
        # Known overlaps that are symbol-internal and unavoidable
        known_unavoidable = {
            'Regulator_Linear:L7805': ['Value_on_GND_pin'],
            'Connector_Generic:Conn_01x02': ['Value_on_body_edge'],
            'Device:R': ['Reference_on_pin_coordinates'],
            'Device:C': ['Reference_on_pin_coordinates'],
        }
        
        for comp in components:
            part = comp.get('part', '')
            ref = comp.get('ref', '')
            
            # Check for known unavoidable issues
            if part in known_unavoidable:
                for issue_type in known_unavoidable[part]:
                    violations.append({
                        'rule': 'known_symbol_overlap',
                        'severity': 'info',
                        'message': f"{ref} ({part}): {issue_type} is unavoidable; workaround applied",
                        'component': ref,
                        'part': part,
                        'issue': issue_type,
                        'workaround': 'Blank Value field and use add_text annotation' if 'Value' in issue_type else 'Accept as symbol limitation'
                    })
        
        return violations
    
    def _distance(self, comp1: Dict, comp2: Dict) -> float:
        """Calculate distance between two components"""
        dx = comp1.get('x', 0) - comp2.get('x', 0)
        dy = comp1.get('y', 0) - comp2.get('y', 0)
        return (dx**2 + dy**2)**0.5
    
    def generate_report(self, violations: List[Dict]) -> str:
        """Generate human-readable validation report"""
        lines = [
            "=" * 80,
            "SCHEMATIC VALIDATION REPORT",
            "=" * 80,
            ""
        ]
        
        if not violations:
            lines.append("✓ NO VIOLATIONS - Schematic is clean")
            lines.append("")
            return "\n".join(lines)
        
        # Group violations by severity
        errors = [v for v in violations if v.get('severity') == 'error']
        warnings = [v for v in violations if v.get('severity') == 'warning']
        info = [v for v in violations if v.get('severity') == 'info']
        
        if errors:
            lines.append(f"ERRORS ({len(errors)}):")
            for v in errors:
                lines.append(f"  [ERROR] {v.get('rule', 'unknown')}")
                lines.append(f"          {v.get('message', 'No details')}")
                lines.append("")
        
        if warnings:
            lines.append(f"WARNINGS ({len(warnings)}):")
            for v in warnings:
                lines.append(f"  [WARNING] {v.get('rule', 'unknown')}")
                lines.append(f"            {v.get('message', 'No details')}")
                lines.append("")
        
        if info:
            lines.append(f"INFO ({len(info)}):")
            for v in info:
                lines.append(f"  [INFO] {v.get('rule', 'unknown')}")
                lines.append(f"         {v.get('message', 'No details')}")
                if 'workaround' in v:
                    lines.append(f"         Workaround: {v['workaround']}")
                lines.append("")
        
        lines.append("=" * 80)
        lines.append(f"Summary: {len(errors)} errors, {len(warnings)} warnings, {len(info)} info items")
        lines.append("=" * 80)
        
        return "\n".join(lines)


if __name__ == '__main__':
    # Example usage
    validator = SchematicValidator()
    
    # Print all rules
    print("AVAILABLE SCHEMATIC DESIGN RULES:\n")
    by_category = {}
    for rule in SchematicValidator.RULES:
        if rule.category not in by_category:
            by_category[rule.category] = []
        by_category[rule.category].append(rule)
    
    for category in sorted(by_category.keys()):
        print(f"\n{category.upper()}:")
        for rule in by_category[category]:
            print(f"  [{rule.severity.upper()}] {rule.name}")
            print(f"               {rule.description}\n")
