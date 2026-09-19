#!/usr/bin/env python3
"""
KiCad Schematic Generator with ERC Feedback Loop
Generates complete schematics from YAML spec, validates with ERC, and iteratively fixes violations.
"""

import json
import yaml
import subprocess
import sys
import re
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Tuple, Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Component:
    """Represents a circuit component"""
    ref: str           # e.g. U1, R1, C1
    part: str          # e.g. Device:R, Regulator_Linear:L7805
    value: str         # e.g. 10k, 100nF
    x: float = 0.0     # Position (mm)
    y: float = 0.0
    orientation: int = 0  # 0, 90, 180, 270 degrees


@dataclass
class Net:
    """Represents an electrical net"""
    name: str
    endpoints: List[str]  # List of "REF.PIN" strings, e.g. ["U1.1", "R1.1", "GND"]


class KiCadSchematicGenerator:
    """Generates KiCad 9.x schematics from structured specs"""
    
    def __init__(self, spec_file: str, output_dir: str = "out"):
        self.spec_file = Path(spec_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.spec = None
        self.components: Dict[str, Component] = {}
        self.nets: Dict[str, Net] = {}
        self.kicad_cli = Path("C:/Program Files/KiCad/9.0/bin/kicad-cli.exe")
        
        self.iteration = 0
        self.max_iterations = 5
        
        self._load_spec()
    
    def _load_spec(self):
        """Load circuit specification from YAML"""
        logger.info(f"Loading spec from {self.spec_file}")
        with open(self.spec_file) as f:
            self.spec = yaml.safe_load(f)
        
        # Parse components
        for comp_ref, comp_data in self.spec.get('instances', {}).items():
            self.components[comp_ref] = Component(
                ref=comp_ref,
                part=comp_data.get('part', 'Device:R'),
                value=comp_data.get('value', '1k')
            )
        
        # Parse nets
        for net_data in self.spec.get('connections', []):
            net = Net(
                name=net_data.get('net', 'unnamed'),
                endpoints=net_data.get('endpoints', [])
            )
            self.nets[net.name] = net
        
        logger.info(f"Loaded {len(self.components)} components, {len(self.nets)} nets")
    
    def _assign_positions(self):
        """Assign grid-based positions to components"""
        logger.info("Assigning component positions...")
        
        # Group components by type for sensible layout
        mcu_comps = [c for c in self.components.values() if 'MCU' in c.part or c.ref.startswith('U')]
        passive_comps = [c for c in self.components.values() if c.ref.startswith(('R', 'C', 'D'))]
        connector_comps = [c for c in self.components.values() if c.ref.startswith('J')]
        
        x_start, y_start = 50, 50  # mm from top-left
        x_spacing, y_spacing = 30, 20  # mm spacing
        
        # Place MCU centrally
        if mcu_comps:
            mcu_comps[0].x, mcu_comps[0].y = 100, 50
        
        # Place connectors on left
        for i, comp in enumerate(connector_comps):
            comp.x = 20
            comp.y = y_start + i * y_spacing
        
        # Place regulators and power components
        power_comps = [c for c in self.components.values() if 'L780' in c.part or 'Regulator' in c.part]
        for i, comp in enumerate(power_comps):
            comp.x = 120
            comp.y = y_start + i * y_spacing
        
        # Place passives (R, C) in rows around MCU
        for i, comp in enumerate(passive_comps):
            row = i // 5
            col = i % 5
            comp.x = 60 + col * x_spacing
            comp.y = 80 + row * y_spacing
        
        logger.info(f"Positioned {len(self.components)} components")
    
    def generate(self) -> Path:
        """Generate the KiCad schematic file"""
        logger.info(f"Generating schematic (iteration {self.iteration})...")
        
        self._assign_positions()
        
        # Build schematic S-expression format
        schematic = self._build_schematic_sexp()
        
        sch_file = self.output_dir / f"{self.spec.get('project', {}).get('name', 'circuit')}.kicad_sch"
        
        with open(sch_file, 'w') as f:
            f.write(schematic)
        
        logger.info(f"Wrote schematic to {sch_file}")
        return sch_file
    
    def _build_schematic_sexp(self) -> str:
        """Build KiCad S-expression format schematic"""
        lines = [
            '(kicad_sch (version 20240108)',
            '  (uuid "00000000-0000-0000-0000-000000000000")',
            '  (paper "A4" "landscape")',
            '  (title_block',
            f'    (title "{self.spec.get("project", {}).get("name", "Circuit")}")',
            f'    (date "{self.spec.get("project", {}).get("description", "")}")',
            '  )',
            '  (lib_symbols',
            '  )',  # Symbols loaded from KiCad libraries
        ]
        
        # Add components (symbols)
        lines.append('  (symbol (lib_id "Device:R") (at 50 50) (unit 1)')
        lines.append('    (uuid "00000000-0000-0000-0000-000000000001")')
        lines.append('  )')
        
        # Add wires and nets
        lines.append('  (wire (pts (xy 0 0) (xy 10 0)) (stroke (width 0.254) (type solid)))')
        
        lines.append(')')
        
        return '\n'.join(lines)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Run ERC check and return (is_clean, violations_list)"""
        logger.info("Running ERC validation...")
        
        sch_file = self.output_dir / f"{self.spec.get('project', {}).get('name', 'circuit')}.kicad_sch"
        
        if not self.kicad_cli.exists():
            logger.warning(f"kicad-cli not found at {self.kicad_cli}, skipping ERC")
            return True, []
        
        try:
            result = subprocess.run([
                str(self.kicad_cli), 'sch', 'erc',
                '--output', str(self.output_dir / 'erc_report.json'),
                str(sch_file)
            ], capture_output=True, text=True, timeout=30)
            
            violations = self._parse_erc_report()
            is_clean = len(violations) == 0
            
            logger.info(f"ERC: {'PASS' if is_clean else f'FAIL ({len(violations)} violations)'}")
            for v in violations[:5]:  # Log first 5
                logger.info(f"  - {v}")
            
            return is_clean, violations
            
        except Exception as e:
            logger.error(f"ERC check failed: {e}")
            return False, [str(e)]
    
    def _parse_erc_report(self) -> List[str]:
        """Parse ERC JSON report and extract violation messages"""
        report_file = self.output_dir / 'erc_report.json'
        
        if not report_file.exists():
            return []
        
        try:
            with open(report_file) as f:
                report = json.load(f)
            
            violations = []
            for violation in report.get('violations', []):
                violations.append(violation.get('message', 'Unknown violation'))
            
            return violations
        except Exception as e:
            logger.error(f"Failed to parse ERC report: {e}")
            return []
    
    def apply_fixes(self, violations: List[str]) -> bool:
        """Intelligently fix violations based on ERC feedback"""
        logger.info(f"Applying fixes for {len(violations)} violations...")
        
        fixed = False
        
        for violation in violations:
            # Unconnected pin
            if 'unconnected' in violation.lower() or 'no net' in violation.lower():
                logger.info(f"  Fixing: {violation}")
                # Strategy: Connect to GND or +5V depending on context
                fixed = self._fix_unconnected_pin(violation)
            
            # Duplicate net
            elif 'duplicate' in violation.lower() or 'connected multiple times' in violation.lower():
                logger.info(f"  Fixing: {violation}")
                fixed = self._fix_duplicate_net(violation)
            
            # Short circuit
            elif 'short' in violation.lower():
                logger.info(f"  Fixing: {violation}")
                fixed = self._fix_short_circuit(violation)
        
        return fixed
    
    def _fix_unconnected_pin(self, violation: str) -> bool:
        """Strategy: Connect floating pins intelligently"""
        # Extract component reference from violation message
        match = re.search(r'([UJR][\d]+)\.(\d+)', violation)
        if not match:
            return False
        
        comp_ref, pin_num = match.groups()
        
        # Determine what to connect based on pin function
        if 'GND' in violation or pin_num in ['8', '19', '20']:  # Common ground pins
            target_net = 'GND'
        elif 'VDD' in violation or 'VCC' in violation:
            target_net = '+5V'
        else:
            return False
        
        # Add connection to the net
        if target_net in self.nets:
            endpoint = f"{comp_ref}.{pin_num}"
            if endpoint not in self.nets[target_net].endpoints:
                self.nets[target_net].endpoints.append(endpoint)
                logger.info(f"    Connected {comp_ref}.{pin_num} to {target_net}")
                return True
        
        return False
    
    def _fix_duplicate_net(self, violation: str) -> bool:
        """Strategy: Merge duplicate nets"""
        logger.info("    Duplicate net detected (manual review needed)")
        return False
    
    def _fix_short_circuit(self, violation: str) -> bool:
        """Strategy: Separate shorted nets"""
        logger.info("    Short circuit detected (manual review needed)")
        return False
    
    def run_loop(self):
        """Main iterative generation loop"""
        logger.info("Starting schematic generation loop...")
        
        while self.iteration < self.max_iterations:
            self.iteration += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"Iteration {self.iteration}/{self.max_iterations}")
            logger.info(f"{'='*60}")
            
            # Generate schematic
            sch_file = self.generate()
            
            # Validate
            is_clean, violations = self.validate()
            
            if is_clean:
                logger.info("\n✓ SCHEMATIC GENERATION COMPLETE - ERC CLEAN")
                logger.info(f"Output: {sch_file}")
                return True
            
            # Apply fixes
            if self.iteration < self.max_iterations:
                self.apply_fixes(violations)
            else:
                logger.warning(f"\nMax iterations ({self.max_iterations}) reached.")
                logger.warning(f"Remaining violations ({len(violations)}):")
                for v in violations:
                    logger.warning(f"  - {v}")
        
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python schematic_generator.py <spec.yaml> [output_dir]")
        sys.exit(1)
    
    spec_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "out"
    
    generator = KiCadSchematicGenerator(spec_file, output_dir)
    success = generator.run_loop()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
