#!/usr/bin/env python3
"""
Validate EasyEDA Pro format against official spec
Reference: https://github.com/easyeda/easyeda-pro-format-skill/blob/main/SKILL.md
"""

import json
import re
from pathlib import Path

def validate_easyeda_pro_format(txt_file):
    """Validate EasyEDA Pro line-based format"""
    
    content = Path(txt_file).read_text()
    lines = content.split('\n')
    
    errors = []
    warnings = []
    stats = {
        'total_lines': 0,
        'dochead': 0,
        'canvas': 0,
        'components': 0,
        'wires': 0,
        'other': 0
    }
    
    # Track tickets
    last_ticket = 0
    seen_ids = set()
    
    for line_num, line in enumerate(lines, 1):
        if not line.strip():
            continue
        
        stats['total_lines'] += 1
        
        # Remove trailing | separator
        line = line.rstrip('|')
        
        # Parse {header}||{data}
        if '||' not in line:
            errors.append(f"Line {line_num}: Missing || separator")
            continue
        
        header_str, data_str = line.split('||', 1)
        
        try:
            header = json.loads(header_str)
            data = json.loads(data_str)
        except json.JSONDecodeError as e:
            errors.append(f"Line {line_num}: Invalid JSON - {e}")
            continue
        
        elem_type = header.get('type')
        elem_id = header.get('id')
        elem_ticket = header.get('ticket')
        
        # Validate DOCHEAD (exception: no id, no ticket)
        if elem_type == "DOCHEAD":
            stats['dochead'] += 1
            
            if 'id' in header or 'ticket' in header:
                errors.append(f"Line {line_num}: DOCHEAD should not have id or ticket")
            
            required_fields = ['docType', 'client', 'uuid', 'updateTime', 'version']
            for field in required_fields:
                if field not in data:
                    errors.append(f"Line {line_num}: DOCHEAD missing '{field}'")
            
            # Check client and uuid are 16-char hex
            if 'client' in data and not re.match(r'^[a-f0-9]{16}$', data['client']):
                errors.append(f"Line {line_num}: client must be 16-char hex, got '{data['client']}'")
            
            if 'uuid' in data and not re.match(r'^[a-f0-9]{16}$', data['uuid']):
                errors.append(f"Line {line_num}: uuid must be 16-char hex, got '{data['uuid']}'")
            
            continue
        
        # Validate CANVAS (special: id="CANVAS", ticket=1)
        if elem_type == "CANVAS":
            stats['canvas'] += 1
            
            if elem_id != "CANVAS":
                errors.append(f"Line {line_num}: CANVAS id must be 'CANVAS', got '{elem_id}'")
            
            if elem_ticket != 1:
                errors.append(f"Line {line_num}: CANVAS ticket must be 1, got {elem_ticket}")
            
            required_fields = ['originX', 'originY']
            for field in required_fields:
                if field not in data:
                    errors.append(f"Line {line_num}: CANVAS missing '{field}'")
            
            last_ticket = 1
            continue
        
        # All other elements: must have id and ticket
        if not elem_id:
            errors.append(f"Line {line_num}: Missing 'id' in header")
        elif not re.match(r'^[a-f0-9]{16}$', elem_id):
            errors.append(f"Line {line_num}: id '{elem_id}' is not 16-char hex")
        else:
            if elem_id in seen_ids:
                errors.append(f"Line {line_num}: Duplicate id '{elem_id}'")
            seen_ids.add(elem_id)
        
        if elem_ticket is None:
            errors.append(f"Line {line_num}: Missing 'ticket' in header")
        elif elem_ticket != last_ticket + 1:
            warnings.append(f"Line {line_num}: ticket {elem_ticket} expected {last_ticket + 1}")
        else:
            last_ticket = elem_ticket
        
        # Count element types
        if elem_type == "COMPONENT":
            stats['components'] += 1
            # TMSchComponent required fields
            required_comp = ['groupId', 'locked', 'zIndex', 'partId', 'x', 'y', 'rotation', 'isMirror', 'attrs']
            for field in required_comp:
                if field not in data:
                    errors.append(f"Line {line_num}: COMPONENT missing '{field}'")
        elif elem_type == "LINE":
            stats['wires'] += 1
            # TSchLine required fields
            required_line = ['lineGroup', 'startX', 'startY', 'endX', 'endY', 'strokeColor', 'strokeStyle', 'fillColor', 'strokeWidth', 'fillStyle']
            for field in required_line:
                if field not in data:
                    errors.append(f"Line {line_num}: LINE missing '{field}'")
        elif elem_type == "ATTR":
            # TSchAttr - child element
            pass
        else:
            stats['other'] += 1
    
    # Report
    print("=" * 70)
    print("EasyEDA Pro Format Validation Results")
    print("=" * 70)
    print()
    
    print("✓ Structure Summary:")
    print(f"  Total lines: {stats['total_lines']}")
    print(f"  - DOCHEAD: {stats['dochead']}")
    print(f"  - CANVAS:  {stats['canvas']}")
    print(f"  - Components: {stats['components']}")
    print(f"  - Wires: {stats['wires']}")
    print(f"  - Other: {stats['other']}")
    print()
    
    if errors:
        print(f"✗ ERRORS ({len(errors)}):")
        for err in errors[:10]:  # Show first 10
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
        print()
    
    if warnings:
        print(f"⚠ WARNINGS ({len(warnings)}):")
        for warn in warnings[:5]:
            print(f"  - {warn}")
        if len(warnings) > 5:
            print(f"  ... and {len(warnings) - 5} more")
        print()
    
    print("=" * 70)
    if not errors:
        print("✓ VALID - Format is acceptable for EasyEDA Pro")
        print()
        print("Next steps:")
        print("  1. Insert into .epro database:")
        print("     UPDATE documents SET dataStr = (read file) WHERE uuid = '<doc_uuid>'")
        print("  2. Or import via EasyEDA Pro UI")
        return True
    else:
        print("✗ INVALID - Fix errors before using")
        return False

if __name__ == "__main__":
    valid = validate_easyeda_pro_format("out/picampcontrol_easyeda_pro.txt")
    exit(0 if valid else 1)
