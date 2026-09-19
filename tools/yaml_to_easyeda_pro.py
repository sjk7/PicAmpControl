#!/usr/bin/env python3
"""
Convert YAML circuit to EasyEDA Pro line-based format (DOCHEAD + CANVAS + primitives)
Following: https://github.com/easyeda/easyeda-pro-format-skill
"""

import yaml
import json
import uuid
import time
from pathlib import Path
from datetime import datetime

class YAMLToEasyEDAProConverter:
    def __init__(self, yaml_file):
        with open(yaml_file) as f:
            self.spec = yaml.safe_load(f)
        
        # Client and document IDs (16-bit hex)
        self.client_id = "1f0f511a4641034c"
        self.doc_uuid = "81ace96648894616"
        self.update_time = int(time.time() * 1000)
        self.version = str(self.update_time)
        self.ticket_counter = 1
    
    def _next_id(self):
        """Generate random 16-char hex ID"""
        return uuid.uuid4().hex[:16]
    
    def _next_ticket(self):
        """Increment ticket counter"""
        self.ticket_counter += 1
        return self.ticket_counter
    
    def _format_line(self, line_type, line_id, data):
        """Format as: {type, id, ticket}||{data}"""
        if line_type == "DOCHEAD":
            # DOCHEAD has no id/ticket
            return json.dumps({"type": "DOCHEAD"}) + "||" + json.dumps(data)
        else:
            ticket = self._next_ticket()
            header = json.dumps({"type": line_type, "id": line_id, "ticket": ticket})
            return header + "||" + json.dumps(data)
    
    def convert(self):
        """Generate EasyEDA Pro format (line-based text)"""
        lines = []
        
        # 1. DOCHEAD (required, first line)
        dochead_data = {
            "docType": "SCH_PAGE",
            "client": self.client_id,
            "uuid": self.doc_uuid,
            "updateTime": self.update_time,
            "version": self.version
        }
        lines.append(self._format_line("DOCHEAD", None, dochead_data))
        
        # 2. CANVAS (required for SCH_PAGE, second line, ticket=1, id=CANVAS)
        self.ticket_counter = 1  # Reset for CANVAS
        canvas_data = {"originX": 0, "originY": 0}
        lines.append(json.dumps({"type": "CANVAS", "id": "CANVAS", "ticket": 1}) + "||" + json.dumps(canvas_data))
        self.ticket_counter = 1  # Continue from here
        
        # 3. Generate COMPONENT primitives for each instance
        components_data = self.spec.get("instances", {})
        component_positions = {}
        x_pos, y_pos = 100, 100
        
        for ref, comp_info in components_data.items():
            comp_id = self._next_id()
            component_positions[ref] = {"x": x_pos, "y": y_pos, "id": comp_id}
            
            # TMSchComponent format (all required fields per official schema)
            comp_data = {
                "groupId": "",
                "locked": False,
                "zIndex": 0,
                "partId": "",
                "x": x_pos,
                "y": y_pos,
                "rotation": 0,
                "isMirror": False,
                "attrs": {
                    "DeviceName": json.dumps({"uuid": "", "name": ref, "source": ""}),
                    "Devices": json.dumps([]),
                    "FootprintName": json.dumps({"uuid": "", "name": comp_info.get("package", ""), "source": ""}),
                    "Footprints": json.dumps([]),
                    "SymbolName": json.dumps({"uuid": "", "name": comp_info.get("value", ""), "source": ""}),
                    "Symbols": json.dumps([])
                }
            }
            
            lines.append(self._format_line("COMPONENT", comp_id, comp_data))
            
            # Add ATTR child element for component reference
            attr_id = self._next_id()
            attr_data = {
                "x": x_pos,
                "y": y_pos - 50,
                "rotation": 0,
                "color": None,
                "fontFamily": None,
                "fontSize": None,
                "fontWeight": None,
                "italic": None,
                "underline": None,
                "align": "LEFT_BOTTOM",
                "value": ref,
                "keyVisible": False,
                "valueVisible": True,
                "key": "REF",
                "fillColor": None,
                "parentId": comp_id,
                "zIndex": 1,
                "groupId": "",
                "locked": False,
                "strikeout": None
            }
            lines.append(self._format_line("ATTR", attr_id, attr_data))
            
            x_pos += 150  # Space components horizontally
            if x_pos > 1000:
                x_pos = 100
                y_pos += 200
        
        # 4. Generate WIRE primitives for each net connection
        nets_data = self.spec.get("connections", [])
        
        for net_obj in nets_data:
            net_name = net_obj.get("net")
            endpoints = net_obj.get("endpoints", [])
            
            # Parse endpoints (format: "REFDES.PIN")
            pins_by_ref = {}
            for endpoint_str in endpoints:
                parts = endpoint_str.split(".")
                if len(parts) == 2:
                    ref, pin = parts
                    if ref not in pins_by_ref:
                        pins_by_ref[ref] = []
                    pins_by_ref[ref].append(pin)
            
            # Create wires between pins in same net
            refs_in_net = list(pins_by_ref.keys())
            for i in range(len(refs_in_net) - 1):
                from_ref = refs_in_net[i]
                to_ref = refs_in_net[i + 1]
                
                if from_ref in component_positions and to_ref in component_positions:
                    from_pos = component_positions[from_ref]
                    to_pos = component_positions[to_ref]
                    
                    wire_group_id = self._next_id()  # Each net gets a group
                    wire_data = {
                        "lineGroup": wire_group_id,
                        "startX": from_pos["x"],
                        "startY": from_pos["y"],
                        "endX": to_pos["x"],
                        "endY": to_pos["y"],
                        "strokeColor": None,
                        "strokeStyle": None,
                        "fillColor": None,
                        "strokeWidth": None,
                        "fillStyle": None
                    }
                    
                    lines.append(self._format_line("LINE", wire_group_id, wire_data))
        
        # Join with line separator (| at end of each line except last)
        result = ""
        for i, line in enumerate(lines):
            if i < len(lines) - 1:
                result += line + "|\n"
            else:
                result += line  # No | on last line
        
        return result
    
    def save(self, output_file):
        """Save format to file"""
        content = self.convert()
        Path(output_file).write_text(content)
        print(f"✓ Generated: {output_file}")
        print(f"✓ Lines: {len(content.splitlines())}")
        return output_file

if __name__ == "__main__":
    converter = YAMLToEasyEDAProConverter("pic_amp_control_full.yaml")
    output = converter.save("out/picampcontrol_easyeda_pro.txt")
    print(f"\nNext: Import this format into EasyEDA Pro")
    print(f"Or: Insert into .epro database documents.dataStr column")
