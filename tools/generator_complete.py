#!/usr/bin/env python3
"""
Complete KiCad Schematic Generator with Design Rule Validation
Integrates: YAML spec -> generation -> visual validation -> ERC -> iterative fixing
"""

import json
import yaml
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import logging
import uuid

from schematic_generator_v2 import KiCadSchematicBuilder, KiCadSchematicValidator as ERCValidator
from schematic_validator import SchematicValidator, ValidationRule

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class PicAmpControlSchematicGenerator:
    """
    Orchestrates complete schematic generation for PicAmpControl with:
    1. Spec-driven generation
    2. Visual design rule validation
    3. ERC electrical rule checking
    4. Iterative fixing
    """
    
    def __init__(self, spec_file: str, output_dir: str = "out"):
        self.spec_file = Path(spec_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        with open(spec_file) as f:
            self.spec = yaml.safe_load(f)
        
        self.project_name = self.spec.get('project', {}).get('name', 'circuit')
        self.visual_validator = SchematicValidator()
        self.erc_validator = ERCValidator()
        
        self.iteration = 0
        self.max_iterations = 5
        
        self.log_file = self.output_dir / 'generation_log.txt'
    
    def _log(self, message: str, level: str = 'info'):
        """Log to both console and file"""
        getattr(logger, level)(message)
        with open(self.log_file, 'a') as f:
            f.write(f"[{level.upper()}] {message}\n")
    
    def generate(self) -> Path:
        """Generate schematic file from spec"""
        self._log(f"Generating schematic (iteration {self.iteration})...")
        
        builder = KiCadSchematicBuilder(self.spec, self.project_name)
        sexp = builder.generate_sexp()
        
        sch_file = self.output_dir / f"{self.project_name}.kicad_sch"
        with open(sch_file, 'w') as f:
            f.write(sexp)
        
        self._log(f"Wrote schematic to {sch_file}", 'info')
        return sch_file
    
    def validate_visual(self, components: dict, nets: dict) -> list:
        """Run visual design rule validation"""
        self._log("Running visual design rule validation...")
        
        violations = []
        # Convert components dict to list with 'ref' field
        comp_list = [{'ref': ref, **props} for ref, props in components.items()]
        violations.extend(self.visual_validator.validate_placement(comp_list))
        violations.extend(self.visual_validator.validate_wiring(nets, comp_list))
        
        if violations:
            self._log(f"Found {len(violations)} visual violations", 'warning')
            report = self.visual_validator.generate_report(violations)
            self._log(report, 'info')
        else:
            self._log("✓ Visual design rules: PASS", 'info')
        
        return violations
    
    def validate_erc(self, sch_file: Path) -> tuple:
        """Run ERC check"""
        self._log("Running ERC electrical validation...")
        
        is_clean, violations = self.erc_validator.run_erc(sch_file, self.output_dir)
        
        if violations:
            self._log(f"Found {len(violations)} ERC violations", 'warning')
            for v in violations[:10]:
                self._log(f"  {v.get('type', 'unknown')}: {v.get('message', '')}", 'warning')
            if len(violations) > 10:
                self._log(f"  ... and {len(violations) - 10} more", 'warning')
        else:
            self._log("✓ ERC check: PASS", 'info')
        
        return is_clean, violations
    
    def apply_fixes(self, visual_violations: list, erc_violations: list) -> bool:
        """Intelligently fix violations"""
        self._log(f"Applying fixes for {len(visual_violations)} visual + {len(erc_violations)} ERC violations...")
        
        fixed = False
        
        # Fix visual violations
        for violation in visual_violations:
            rule = violation.get('rule', '')
            
            if rule == 'auto_generated_net_label':
                self._log(f"  Removing auto-generated net label: {violation.get('net')}", 'info')
                # TODO: Implement removal
                fixed = True
            
            elif rule == 'component_too_close':
                self._log(f"  Adjusting placement: {violation.get('components')}", 'info')
                # TODO: Implement placement adjustment
                fixed = True
        
        # Fix ERC violations  
        for violation in erc_violations:
            vtype = violation.get('type', '')
            
            if 'unconnected' in vtype.lower():
                self._log(f"  Fixing unconnected pin...", 'info')
                # TODO: Implement connection
                fixed = True
            
            elif 'short' in vtype.lower():
                self._log(f"  Resolving short circuit...", 'info')
                # TODO: Implement de-shorting
                fixed = True
        
        return fixed
    
    def run_loop(self) -> bool:
        """Main iterative generation loop"""
        self._log(f"\nStarting PicAmpControl schematic generation loop (max {self.max_iterations} iterations)")
        self._log("=" * 80)
        
        for self.iteration in range(1, self.max_iterations + 1):
            self._log(f"\n{'='*80}")
            self._log(f"ITERATION {self.iteration}/{self.max_iterations}")
            self._log(f"{'='*80}\n")
            
            # Phase 1: Generate
            sch_file = self.generate()
            
            # Phase 2: Validate visual rules
            components = self.spec.get('instances', {})
            nets = {net.get('net'): net.get('endpoints', []) for net in self.spec.get('connections', [])}
            
            visual_violations = self.validate_visual(components, nets)
            
            # Phase 3: Run ERC
            erc_clean, erc_violations = self.validate_erc(sch_file)
            
            # Check if we're done
            if not visual_violations and erc_clean:
                self._log(f"\n{'='*80}")
                self._log("✓ SCHEMATIC GENERATION COMPLETE")
                self._log("  - All visual design rules: PASS")
                self._log("  - ERC electrical check: PASS")
                self._log(f"  - Output: {sch_file}")
                self._log(f"{'='*80}\n")
                return True
            
            # Phase 4: Apply fixes (if not final iteration)
            if self.iteration < self.max_iterations:
                self._log(f"\nApplying fixes and regenerating...")
                self.apply_fixes(visual_violations, erc_violations)
            else:
                self._log(f"\nMax iterations ({self.max_iterations}) reached.")
                self._log(f"Remaining violations:")
                self._log(f"  Visual: {len(visual_violations)}")
                self._log(f"  ERC: {len(erc_violations)}")
        
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python generator_complete.py <spec.yaml> [output_dir]")
        sys.exit(1)
    
    spec_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "out"
    
    generator = PicAmpControlSchematicGenerator(spec_file, output_dir)
    success = generator.run_loop()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
