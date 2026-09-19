#!/usr/bin/env python3
"""
EasyEDA Pro to SVG Renderer

Converts component specifications to SVG schematics for visual validation in VS Code.
Generates an interactive visual representation before committing to EasyEDA Pro.
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class BBox:
    """Bounding box for SVG rendering"""
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    
    def width(self):
        return self.x_max - self.x_min
    
    def height(self):
        return self.y_max - self.y_min
    
    def with_margin(self, margin: float):
        """Expand bbox by margin"""
        return BBox(
            self.x_min - margin,
            self.y_min - margin,
            self.x_max + margin,
            self.y_max + margin
        )


class SchematicSVGRenderer:
    """Renders schematic components as SVG"""
    
    def __init__(self, scale: float = 100.0):
        """
        Initialize renderer.
        
        Args:
            scale: Pixels per schematic unit (100 = 100px per 0.01 inch)
        """
        self.scale = scale
        self.svg_elements = []
        self.bbox = None
    
    def render_component(self, comp: Dict, x_offset: float = 0, y_offset: float = 0) -> Tuple[float, float, float, float]:
        """
        Render a component symbol and return its bounding box.
        
        Args:
            comp: Component dict with designator, value, x, y
            x_offset, y_offset: Position offsets
        
        Returns:
            (x_min, y_min, x_max, y_max) in SVG coordinates
        """
        x = comp['x'] * self.scale + x_offset
        y = comp['y'] * self.scale + y_offset
        w = 0.04 * self.scale  # Component width ~0.04 inch
        h = 0.03 * self.scale  # Component height ~0.03 inch
        
        # Component body rectangle
        self.svg_elements.append(
            f'  <rect x="{x - w/2}" y="{y - h/2}" width="{w}" height="{h}" '
            f'fill="white" stroke="black" stroke-width="2"/>'
        )
        
        # Component reference (designator)
        ref_font_size = max(8, int(0.02 * self.scale))
        self.svg_elements.append(
            f'  <text x="{x}" y="{y - h/2 - 8}" font-size="{ref_font_size}" '
            f'font-weight="bold" text-anchor="middle" fill="black">{comp["designator"]}</text>'
        )
        
        # Component value
        val_font_size = max(7, int(0.015 * self.scale))
        if comp.get('value'):
            self.svg_elements.append(
                f'  <text x="{x}" y="{y + h/2 + 12}" font-size="{val_font_size}" '
                f'text-anchor="middle" fill="darkblue">{comp["value"]}</text>'
            )
        
        # Part number (smaller, below value)
        if comp.get('part_number'):
            part_font_size = max(6, int(0.01 * self.scale))
            self.svg_elements.append(
                f'  <text x="{x}" y="{y + h/2 + 22}" font-size="{part_font_size}" '
                f'text-anchor="middle" fill="darkgreen">{comp["part_number"]}</text>'
            )
        
        return (x - w/2, y - h/2, x + w/2, y + h/2)
    
    def render_net_label(self, label: str, x: float, y: float) -> None:
        """Render a net label"""
        x_px = x * self.scale
        y_px = y * self.scale
        font_size = max(8, int(0.015 * self.scale))
        
        # Label background
        self.svg_elements.append(
            f'  <rect x="{x_px - 20}" y="{y_px - 10}" width="40" height="16" '
            f'fill="lightyellow" stroke="orange" stroke-width="1"/>'
        )
        
        # Label text
        self.svg_elements.append(
            f'  <text x="{x_px}" y="{y_px + 4}" font-size="{font_size}" '
            f'text-anchor="middle" fill="darkorange" font-weight="bold">{label}</text>'
        )
    
    def render_schematic(self, components: List[Dict], title: str = "Schematic") -> str:
        """
        Render complete schematic to SVG.
        
        Args:
            components: List of component dicts
            title: Schematic title
        
        Returns:
            SVG string
        """
        self.svg_elements = []
        
        if not components:
            return '<svg></svg>'
        
        # Calculate bounding box from component positions
        xs = [c['x'] for c in components]
        ys = [c['y'] for c in components]
        
        x_min, x_max = min(xs) - 0.1, max(xs) + 0.1
        y_min, y_max = min(ys) - 0.1, max(ys) + 0.1
        
        self.bbox = BBox(x_min, y_min, x_max, y_max).with_margin(0.05)
        
        # Render components and collect bboxes
        comp_bboxes = {}
        for comp in components:
            bbox = self.render_component(comp)
            comp_bboxes[comp['designator']] = bbox
        
        # Group components by function for visual separation
        self._add_functional_groups(components)
        
        # Build SVG
        svg_width = int(self.bbox.width() * self.scale) + 40
        svg_height = int(self.bbox.height() * self.scale) + 100
        
        svg_lines = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" '
            f'viewBox="{int(self.bbox.x_min * self.scale - 20)} {int(self.bbox.y_min * self.scale - 40)} '
            f'{svg_width} {svg_height}">',
            f'  <defs>',
            f'    <style>',
            f'      text {{ font-family: Arial, sans-serif; }}',
            f'      .net-label {{ fill: darkorange; font-weight: bold; }}',
            f'      .component {{ stroke: black; stroke-width: 1.5; }}',
            f'    </style>',
            f'  </defs>',
            f'  <!-- Title -->',
            f'  <text x="{svg_width // 2}" y="20" font-size="18" font-weight="bold" '
            f'text-anchor="middle" fill="black">{title}</text>',
            f'  <!-- Components -->',
        ]
        
        svg_lines.extend(self.svg_elements)
        
        svg_lines.extend([
            f'  <!-- Grid for reference -->',
            f'  <g stroke="lightgray" stroke-width="0.5" opacity="0.3">',
            self._generate_grid_lines(),
            f'  </g>',
            f'</svg>'
        ])
        
        return '\n'.join(svg_lines)
    
    def _add_functional_groups(self, components: List[Dict]) -> None:
        """Add visual grouping for functional blocks"""
        groups = self._group_components(components)
        
        group_colors = {
            "Power Supply": "rgba(255,200,0,0.1)",
            "MCU": "rgba(100,150,255,0.1)",
            "ADC Conditioning": "rgba(100,255,150,0.1)",
            "Comparator": "rgba(255,150,100,0.1)",
            "Digital Outputs": "rgba(200,100,255,0.1)",
            "Interfaces": "rgba(255,100,200,0.1)",
            "Fan Control": "rgba(150,200,100,0.1)",
        }
        
        for group_name, comps in groups.items():
            if not comps:
                continue
            
            xs = [c['x'] for c in comps]
            ys = [c['y'] for c in comps]
            
            x1, x2 = min(xs) - 0.05, max(xs) + 0.05
            y1, y2 = min(ys) - 0.05, max(ys) + 0.05
            
            x1_px, y1_px = x1 * self.scale, y1 * self.scale
            w_px = (x2 - x1) * self.scale
            h_px = (y2 - y1) * self.scale
            
            color = group_colors.get(group_name, "rgba(200,200,200,0.1)")
            
            # Background rectangle
            self.svg_elements.insert(0,
                f'  <rect x="{x1_px}" y="{y1_px}" width="{w_px}" height="{h_px}" '
                f'fill="{color}" stroke="gray" stroke-width="1" stroke-dasharray="5,5"/>'
            )
            
            # Group label
            self.svg_elements.insert(1,
                f'  <text x="{x1_px + 5}" y="{y1_px - 3}" font-size="10" fill="gray" '
                f'font-style="italic">{group_name}</text>'
            )
    
    def _group_components(self, components: List[Dict]) -> Dict[str, List[Dict]]:
        """Group components by function"""
        groups = {
            "Power Supply": [],
            "MCU": [],
            "ADC Conditioning": [],
            "Comparator": [],
            "Digital Outputs": [],
            "Interfaces": [],
            "Fan Control": [],
            "Other": []
        }
        
        for comp in components:
            ref = comp.get('designator', '')
            
            if any(x in ref for x in ['J', 'U2', 'C2', 'C3', 'C4']):
                groups["Power Supply"].append(comp)
            elif 'U1' in ref or 'R1' in ref or 'C1' in ref:
                groups["MCU"].append(comp)
            elif any(x in ref for x in ['ADC', 'REFL', 'FWD', 'OCP', 'OD', 'DRAIN']):
                groups["ADC Conditioning"].append(comp)
            elif 'U3' in ref or 'LM339' in comp.get('part_number', ''):
                groups["Comparator"].append(comp)
            elif any(x in ref for x in ['TX', 'TRIP']):
                groups["Digital Outputs"].append(comp)
            elif any(x in ref for x in ['I2C', 'ENC', 'PTT']):
                groups["Interfaces"].append(comp)
            elif any(x in ref for x in ['FAN', 'Q1']):
                groups["Fan Control"].append(comp)
            else:
                groups["Other"].append(comp)
        
        return {k: v for k, v in groups.items() if v}
    
    def _generate_grid_lines(self) -> str:
        """Generate grid lines for schematic grid"""
        grid_lines = []
        grid_spacing = 0.1 * self.scale
        
        x = int(self.bbox.x_min * self.scale)
        while x < int(self.bbox.x_max * self.scale):
            grid_lines.append(
                f'    <line x1="{x}" y1="{int(self.bbox.y_min * self.scale)}" '
                f'x2="{x}" y2="{int(self.bbox.y_max * self.scale)}"/>'
            )
            x += int(grid_spacing)
        
        y = int(self.bbox.y_min * self.scale)
        while y < int(self.bbox.y_max * self.scale):
            grid_lines.append(
                f'    <line x1="{int(self.bbox.x_min * self.scale)}" y1="{y}" '
                f'x2="{int(self.bbox.x_max * self.scale)}" y2="{y}"/>'
            )
            y += int(grid_spacing)
        
        return '\n'.join(grid_lines)


def render_picampcontrol_schematic() -> str:
    """Render PicAmpControl schematic from generated JSON"""
    
    json_file = Path('out/picampcontrol_easyeda_agent.json')
    if not json_file.exists():
        print(f"Error: {json_file} not found. Run easyeda_pro_generator.py first.")
        return ""
    
    with open(json_file) as f:
        spec = json.load(f)
    
    renderer = SchematicSVGRenderer(scale=80)  # 80px per unit
    svg = renderer.render_schematic(spec['components'], title=spec['title'])
    
    return svg


if __name__ == '__main__':
    print("Rendering schematic to SVG...")
    
    svg_content = render_picampcontrol_schematic()
    
    if svg_content:
        svg_file = Path('out/picampcontrol_schematic.svg')
        svg_file.parent.mkdir(exist_ok=True)
        with open(svg_file, 'w') as f:
            f.write(svg_content)
        
        print(f"[OK] Generated: {svg_file}")
        print(f"  Size: {len(svg_content)} bytes")
        print(f"\nOpen in VS Code Insiders:")
        print(f"  1. Run: code-insiders {svg_file}")
        print(f"  2. Install 'SVG Viewer' extension if needed")
        print(f"  3. Preview will auto-refresh on schematic changes")
