#!/usr/bin/env python3
"""
Minimal KiCad schematic generator - proof of concept
Generates a simple valid schematic to test the pipeline
"""

def generate_minimal_schematic() -> str:
    """Generate a minimal valid KiCad schematic"""
    
    sexp = """(kicad_sch (version 20240108)

  (uuid "00000000-0000-0000-0000-000000000000")

  (paper "A4")

  (title_block
    (title "PicAmpControl Minimal Test")
    (date "2026-09-19")
  )

  (symbol (lib_id "Device:R") (at 100 100 0)
    (uuid "11111111-1111-1111-1111-111111111111")
    (property "Reference" "R1" (at 100 100 0)
      (effects (font (size 1.27 1.27) (thickness 0.15)))
    )
    (property "Value" "10k" (at 100 100 0)
      (effects (font (size 1.27 1.27) (thickness 0.15)))
    )
    (pin "1" (uuid "00000001-0000-0000-0000-000000000000"))
    (pin "2" (uuid "00000002-0000-0000-0000-000000000000"))
  )

  (symbol (lib_id "power:GND") (at 100 120 0)
    (uuid "22222222-2222-2222-2222-222222222222")
    (property "Reference" "#GND01" (at 100 120 0)
      (effects (font (size 1.27 1.27) (thickness 0.15)) hide)
    )
    (property "Value" "GND" (at 100 120 0)
      (effects (font (size 1.27 1.27) (thickness 0.15)) hide)
    )
    (pin "1" (uuid "00000003-0000-0000-0000-000000000000"))
  )

  (wire (pts (xy 105 100) (xy 105 120))
    (stroke (width 0.254) (type solid))
    (uuid "33333333-3333-3333-3333-333333333333")
  )

  (global_label "TEST_NET" (shape passive)
    (at 95 100 0)
    (effects (font (size 1.27 1.27) (thickness 0.15)) (justify left))
    (uuid "44444444-4444-4444-4444-444444444444")
  )

)
"""
    return sexp


if __name__ == '__main__':
    import sys
    output_file = sys.argv[1] if len(sys.argv) > 1 else "test_minimal.kicad_sch"
    
    with open(output_file, 'w') as f:
        f.write(generate_minimal_schematic())
    
    print(f"Generated minimal schematic: {output_file}")
