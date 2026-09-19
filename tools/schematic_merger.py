#!/usr/bin/env python3
"""
KiCad Schematic Merger - Extends existing schematic with missing components from YAML spec.

Reads baseline schematic, parses YAML spec, generates S-expression components,
merges them intelligently, and validates with ERC.
"""

import re
import yaml
import json
import subprocess
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Set

class SchematicMerger:
    """Intelligently merge YAML spec components into existing KiCad schematic"""
    
    def __init__(self, baseline_sch: str, yaml_spec: str):
        self.baseline_sch = Path(baseline_sch)
        self.yaml_spec = Path(yaml_spec)
        
        with open(baseline_sch) as f:
            self.baseline_content = f.read()
        
        with open(yaml_spec) as f:
            self.spec = yaml.safe_load(f)
        
        # Parse existing components
        self.existing_refs = self._parse_existing_components()
        self.spec_refs = set(self.spec.get('instances', {}).keys())
        self.missing_refs = self.spec_refs - self.existing_refs
        
        print(f"Baseline: {len(self.existing_refs)} components")
        print(f"Spec: {len(self.spec_refs)} components")
        print(f"Missing: {len(self.missing_refs)} components")
        print(f"Missing refs: {sorted(self.missing_refs)[:10]}...")
    
    def _parse_existing_components(self) -> Set[str]:
        """Extract all component references from baseline"""
        # Match (symbol (lib_id "...") ... (property "Reference" "R1" ...
        pattern = r'\(property "Reference" "([^"]+)"'
        refs = set(re.findall(pattern, self.baseline_content))
        return refs
    
    def merge(self) -> str:
        """
        Merge spec components into baseline.
        
        Strategy:
        1. Find insertion point (before closing `)` of schematic)
        2. Generate S-expressions for each missing component
        3. Generate wiring (connect_pins calls via MCP, or direct wire S-expressions)
        4. Return merged content
        """
        
        merged = self.baseline_content
        
        # Find insertion point (before final closing paren)
        insertion_point = merged.rfind('\n)')
        if insertion_point < 0:
            raise ValueError("Cannot find insertion point in schematic")
        
        # Generate component S-expressions
        components_sexp = self._generate_components_sexp()
        wiring_sexp = self._generate_wiring_sexp()
        
        # Insert before final closing paren
        merged = merged[:insertion_point] + '\n' + components_sexp + '\n' + wiring_sexp + merged[insertion_point:]
        
        return merged
    
    def _generate_components_sexp(self) -> str:
        """Generate S-expressions for all missing components"""
        lines = ['\n  ; ===== ADDED COMPONENTS FROM YAML SPEC =====\n']
        
        y_pos = 200  # Start placing below existing components
        x_base = 300
        
        for ref in sorted(self.missing_refs):
            comp_spec = self.spec['instances'][ref]
            x_pos = x_base + (hash(ref) % 5) * 50  # Spread components
            
            part = comp_spec.get('part', 'Device:R')
            value = comp_spec.get('value', '')
            footprint = comp_spec.get('footprint', '')
            
            # Generate symbol instance with proper S-expression format
            uuid_str = str(uuid.uuid4())
            symbol_sexp = self._symbol_sexp(ref, part, value, x_pos, y_pos, uuid_str)
            lines.append(symbol_sexp)
            
            y_pos += 25  # Next component below
        
        return ''.join(lines)
    
    def _symbol_sexp(self, ref: str, lib_id: str, value: str, x: float, y: float, uuid_str: str) -> str:
        """Generate S-expression for a single symbol"""
        # Note: simplified version - full version needs proper pin definitions
        # This is why direct S-expression generation is hard; pins need library lookup
        return f'''
  (symbol (lib_id "{lib_id}") (at {x} {y} 0)
    (uuid "{uuid_str}")
    (property "Reference" "{ref}" (at {x} {y-2} 0)
      (effects (font (size 1.27 1.27) (thickness 0.15)))
    )
    (property "Value" "{value}" (at {x} {y+2} 0)
      (effects (font (size 1.27 1.27) (thickness 0.15)))
    )
    (pin "1" (uuid "{uuid.uuid4()}"))
    (pin "2" (uuid "{uuid.uuid4()}"))
  )
'''
    
    def _generate_wiring_sexp(self) -> str:
        """Generate wiring between components"""
        # This requires knowing pin positions, which requires library lookup
        # Recommend using MCP tools for this instead
        return '\n  ; ===== WIRING (use MCP tools: wire_pins_to_net, connect_pins) =====\n'
    
    def save(self, output_path: str):
        """Save merged schematic"""
        merged = self.merge()
        with open(output_path, 'w') as f:
            f.write(merged)
        print(f"Wrote merged schematic to {output_path}")


if __name__ == '__main__':
    import sys
    
    baseline = sys.argv[1] if len(sys.argv) > 1 else \
        'docs/hardware/project_schematic_package/generated/mcp-final/pic_amp_protection.kicad_sch'
    yaml_spec = sys.argv[2] if len(sys.argv) > 2 else 'pic_amp_control_full.yaml'
    
    merger = SchematicMerger(baseline, yaml_spec)
    # Don't auto-save yet - just analyze
    print("\nRecommendation: Use MCP tools to add components incrementally:")
    print("  1. mcp_kicad_place_component for each missing component")
    print("  2. mcp_kicad_wire_pins_to_net for power rails")
    print("  3. mcp_kicad_connect_pins for signal connections")
    print("  4. Run ERC after each group to validate")
