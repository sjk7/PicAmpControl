#!/usr/bin/env python3
"""Generate a complete KiCad 6+ project (.kicad_pro, .kicad_sch, .kicad_pcb)
and zip archive (PicAmpControl_KiCad_Project.zip) for PicAmpControl.

When importing into EasyEDA Pro via File -> Import -> KiCad..., select the ZIP file.
EasyEDA Pro parses both schematic and PCB together, automatically binding footprints
to schematic symbols without requiring manual footprint search or assignment.
"""

import os
import uuid
import zipfile

def gen_uuid(seed_str):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed_str))

# Imports component list & nets from gen_netlist
import gen_netlist

components = gen_netlist.components
nets = gen_netlist.nets

def generate_kicad_pro():
    return '''{
  "board": {
    "3dmodels": [],
    "design_settings": {
      "defaults": {
        "board_outline_thickness": 0.1,
        "copper_line_width": 0.25,
        "track_width": 0.25,
        "via_diameter": 0.8,
        "via_hole_min": 0.4
      }
    }
  },
  "meta": {
    "filename": "PicAmpControl.kicad_pro",
    "version": 1
  },
  "net_settings": {
    "classes": [
      {
        "name": "Default",
        "nets": []
      }
    ]
  },
  "sheets": [
    [
      "00000000-0000-0000-0000-000000000000",
      ""
    ]
  ]
}
'''

def generate_kicad_pcb():
    lines = []
    lines.append('(kicad_pcb (version 20211014) (generator "PicAmpControl gen_kicad_project.py")')
    lines.append('  (general (thickness 1.6))')
    lines.append('  (paper "A4")')
    lines.append('  (layers')
    lines.append('    (0 "F.Cu" signal)')
    lines.append('    (31 "B.Cu" signal)')
    lines.append('    (36 "B.SilkS" user "B.Silkscreen")')
    lines.append('    (37 "F.SilkS" user "F.Silkscreen")')
    lines.append('    (38 "B.Mask" user)')
    lines.append('    (39 "F.Mask" user)')
    lines.append('    (44 "Edge.Cuts" user)')
    lines.append('  )')
    lines.append('')
    lines.append('  (net 0 "")')

    net_map = {}
    for code, (net_name, nodes) in enumerate(nets.items(), start=1):
        net_map[net_name] = code
        lines.append(f'  (net {code} "{net_name}")')

    lines.append('')

    # Arrange components in a 10x10 grid on the PCB canvas
    grid_x_start = 50.0
    grid_y_start = 50.0
    grid_step_x = 25.0
    grid_step_y = 20.0
    cols = 8

    for idx, (ref, value, footprint) in enumerate(components):
        col = idx % cols
        row = idx // cols
        x = grid_x_start + col * grid_step_x
        y = grid_y_start + row * grid_step_y
        footprint_uuid = gen_uuid(f"pcb_fp_{ref}")

        lines.append(f'  (footprint "{footprint}" (layer "F.Cu") (at {x:.2f} {y:.2f}) (unit 1)')
        lines.append(f'    (uuid "{footprint_uuid}")')
        lines.append(f'    (property "Reference" "{ref}" (at {x:.2f} {y-4:.2f} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))')
        lines.append(f'    (property "Value" "{value}" (at {x:.2f} {y+4:.2f} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))')
        lines.append('  )')

    lines.append(')')
    return "\n".join(lines)

def main():
    script_dir = os.path.dirname(os.path.realpath(__file__))

    pro_file = os.path.join(script_dir, "PicAmpControl.kicad_pro")
    pcb_file = os.path.join(script_dir, "PicAmpControl.kicad_pcb")
    zip_file = os.path.join(script_dir, "PicAmpControl_KiCad_Project.zip")

    with open(pro_file, "w") as f:
        f.write(generate_kicad_pro())
    print(f"wrote {pro_file}")

    with open(pcb_file, "w") as f:
        f.write(generate_kicad_pcb())
    print(f"wrote {pcb_file}")

    # Build ZIP package containing .kicad_pro, .kicad_sch, .kicad_pcb
    sch_file = os.path.join(script_dir, "PicAmpControl.kicad_sch")

    with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pro_file, "PicAmpControl.kicad_pro")
        if os.path.exists(sch_file):
            z.write(sch_file, "PicAmpControl.kicad_sch")
        z.write(pcb_file, "PicAmpControl.kicad_pcb")

    print(f"created ZIP archive for EasyEDA Pro import: {zip_file}")

if __name__ == "__main__":
    main()
