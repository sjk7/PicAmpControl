"""Generate an editable KiCad schematic from the project circuit metadata."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import json
import tomllib
import re
import uuid


def configure_kicad_symbols(symbol_dir: Path) -> None:
    value = str(symbol_dir)
    footprint_value = str(symbol_dir.parent / "footprints")
    for variable in (
        "KICAD_SYMBOL_DIR",
        "KICAD6_SYMBOL_DIR",
        "KICAD7_SYMBOL_DIR",
        "KICAD8_SYMBOL_DIR",
        "KICAD9_SYMBOL_DIR",
        "KICAD10_SYMBOL_DIR",
    ):
        os.environ.setdefault(variable, value)
    for version in range(6, 11):
        os.environ.setdefault(f"KICAD{version}_FOOTPRINT_DIR", footprint_value)


def validate_with_kicad(schematic: Path) -> None:
    """Require KiCad CLI to parse and render the generated hierarchy."""
    cli = os.environ.get("KICAD_CLI") or shutil.which("kicad-cli")
    if cli is None and os.name == "nt":
        candidate = Path(r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe")
        if candidate.exists():
            cli = str(candidate)
    if cli is None:
        raise RuntimeError("KiCad CLI not found; set KICAD_CLI to validate the schematic")

    temporary_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    temporary_pdf.close()
    try:
        result = subprocess.run(
            [cli, "sch", "export", "pdf", str(schematic), "-o", temporary_pdf.name],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            details = (result.stderr or result.stdout).strip()
            raise RuntimeError(f"KiCad could not render {schematic}: {details}")
    finally:
        Path(temporary_pdf.name).unlink(missing_ok=True)

    erc_report = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    erc_report.close()
    try:
        result = subprocess.run(
            [
                cli,
                "sch",
                "erc",
                str(schematic),
                "--format",
                "json",
                "--output",
                erc_report.name,
                "--exit-code-violations",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        report = json.loads(Path(erc_report.name).read_text(encoding="utf-8"))
        allowed = {"lib_symbol_mismatch", "global_label_dangling", "endpoint_off_grid"}
        violations = []
        for sheet in report.get("sheets", []):
            for violation in sheet.get("violations", []):
                if violation.get("type") not in allowed:
                    violations.append(violation.get("type", "unknown"))
        if violations:
            details = ", ".join(sorted(set(violations)))
            raise RuntimeError(f"KiCad ERC found electrical violations in {schematic}: {details}")
    finally:
        Path(erc_report.name).unlink(missing_ok=True)


def structured_layout(output_dir: Path) -> int:
    """Place and route MCU-local components through the structured KiCad API."""
    from kicad_sch_api import load_schematic

    path = output_dir / "pic_amp_protection_mcu_control1.kicad_sch"
    schematic = load_schematic(str(path))
    moves = 0
    targets = {
        "U1": (140.0, 100.0),
        "R1": (95.0, 100.0),
        "C1": (115.0, 55.0),
        "C2": (130.0, 55.0),
        "C3": (145.0, 55.0),
        "RN1": (185.0, 85.0),
        "J3": (90.0, 135.0),
        "Q1": (190.0, 125.0),
        "FAN1": (220.0, 105.0),
    }
    for component in schematic.components:
        if component.reference in targets:
            component.move(*targets[component.reference])
            x, y = targets[component.reference]
            if "Reference" in component.properties:
                component.properties["Reference"]["at"] = [x, y - 5.0, 0]
            if "Value" in component.properties:
                component.properties["Value"]["at"] = [x, y + 5.0, 0]
            moves += 1
    # Avoid GUID-based wire cleanup here: the KiCad API can report stale UUIDs after
    # a file reload or partial rewrite, so the generator should prefer regenerating the
    # topology from source metadata instead of deleting wires by dead object IDs.
    connections = [
        ("U1", "26", "Q1", "G"),
        ("Q1", "D", "FAN1", "2"),
        ("Q1", "S", "#PWR002", "1"),
        ("FAN1", "1", "#PWR008", "1"),
        ("U1", "7", "RN1", "2"),
        ("RN1", "1", "#PWR001", "1"),
        ("U1", "15", "J3", "3"),
        ("U1", "14", "J3", "4"),
        ("J3", "1", "#PWR001", "1"),
        ("J3", "2", "#PWR002", "1"),
        ("U1", "20", "#PWR001", "1"),
        ("U1", "8", "#PWR002", "1"),
        ("U1", "19", "#PWR002", "1"),
        ("R1", "1", "#PWR001", "1"),
        ("R1", "2", "U1", "1"),
        ("C1", "1", "#PWR001", "1"),
        ("C1", "2", "#PWR004", "1"),
        ("C2", "1", "#PWR001", "1"),
        ("C2", "2", "#PWR005", "1"),
        ("C3", "1", "#PWR001", "1"),
        ("C3", "2", "#PWR006", "1"),
    ]
    for first_ref, first_pin, second_ref, second_pin in connections:
        schematic.auto_route_pins(
            first_ref,
            first_pin,
            second_ref,
            second_pin,
            routing_strategy="manhattan",
        )
    external_pins = {
        "1": "RESET",
        "2": "SWR1_FWD_ADC",
        "3": "SWR1_REF_ADC",
        "4": "SWR2_FWD_ADC",
        "5": "SWR2_REF_ADC",
        "6": "BAND_B0",
        "9": "BAND_B2",
        "10": "BAND_B1",
        "11": "PTT_IN",
        "12": "COMP_RESET",
        "13": "ENCODER_A",
        "14": "I2C_SCL",
        "15": "I2C_SDA",
        "16": "TX_OUT",
        "17": "TX_VCC",
        "18": "TX_BIAS",
        "21": "ENCODER_B",
        "22": "CURRENT_ADC",
        "23": "OVERDRIVE_ADC",
        "24": "DRAIN_PEAK_ADC",
        "25": "OVERCURRENT_FAULT",
        "26": "FAN_PWM",
        "27": "ENCODER_SWITCH",
        "28": "TRIP_STATUS",
    }
    u1 = next(component for component in schematic.components if component.reference == "U1")
    for pin_number, net_name in external_pins.items():
        position = schematic.get_component_pin_position("U1", pin_number)
        if position is None:
            continue
        if position.x < u1.position.x:
            endpoint = (position.x - 10.0, position.y)
        else:
            endpoint = (position.x + 10.0, position.y)
        schematic.add_wire_to_pin(endpoint, "U1", pin_number)
        schematic.add_global_label(net_name, endpoint, shape="bidirectional")
    if moves:
        schematic.save(str(path))
    return moves


def load_skidl():
    from skidl import Net, Part, POWER, generate_schematic, set_default_tool, subcircuit
    from skidl.net import NCNet
    from skidl import KICAD9

    set_default_tool(KICAD9)
    return NCNet, Net, Part, POWER, generate_schematic, subcircuit


SYMBOLS = {
    "PIC16F18855": ("MCU_Microchip_PIC16", "PIC16F18855-xSO"),
    "74HC4514": ("4xxx_IEEE", "4514"),
    "ULN2803A": ("Transistor_Array", "ULN2803A"),
    "R": ("Device", "R"),
    "C": ("Device", "C"),
    "D": ("Device", "D"),
    "Relay_SPST": ("Relay", "Relay_SPST-NO"),
    "NMOS_TO220": ("Device", "Q_NMOS"),
    "Fan": ("Motor", "Fan"),
    "NTC_10k": ("Device", "Thermistor_NTC"),
    "Button": ("Switch", "SW_Push"),
    "Conn_01x04": ("Connector_Generic", "Conn_01x04"),
}

FOOTPRINTS = {
    "PIC16F18855": "Package_SO:SOIC-28W_7.5x17.9mm_P1.27mm",
    "74HC4514": "Package_DIP:DIP-24_W7.62mm",
    "ULN2803A": "Package_DIP:DIP-18_W7.62mm",
    "R": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    "C": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "D": "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
    "Relay_SPST": "Relay_THT:Relay_1-Form-A_Schrack-RYII_RM5mm",
    "NMOS_TO220": "Package_TO_SOT_THT:TO-220-3_Vertical",
    "Fan": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "NTC_10k": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    "Button": "Button_Switch_THT:SW_PUSH_6mm_H4.3mm",
    "Conn_01x04": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
}

PIN_ALIASES = {
    "Vdd": "VDD",
    "Vss": "VSS",
    "IN1": "I1",
    "IN2": "I2",
    "IN3": "I3",
    "IN4": "I4",
    "IN5": "I5",
    "IN6": "I6",
    "IN7": "I7",
    "OUT1": "O1",
    "OUT2": "O2",
    "OUT3": "O3",
    "OUT4": "O4",
    "OUT5": "O5",
    "OUT6": "O6",
    "OUT7": "O7",
}


def resolve_pin(part, pin_spec):
    number = pin_spec.get("number")
    if number is not None:
        return part[str(number)]

    name = pin_spec["name"]
    candidates = [PIN_ALIASES.get(name, name)]
    if name in {"1", "2"} and part.name == "Relay_SPST-NO":
        candidates = [{"1": "A1", "2": "A2"}[name]]
    if name == "MCLR":
        candidates = ["RE3/~{MCLR}/VPP"]

    for candidate in candidates:
        try:
            return part[candidate]
        except (KeyError, IndexError, ValueError):
            continue
    raise ValueError(
        f"{part.ref}: cannot resolve pin {name!r}; "
        f"available pins are {[pin.name for pin in part.pins]}"
    )


GROUPS = {
    "mcu_control": {
        "U1",
        "R1",
        "C1",
        "C2",
        "C3",
        "Q1",
        "FAN1",
        "RN1",
        "J3",
    },
    "band_decoder": {"U2"},
    "relay_driver": {"U3"},
    "relay_bank": {*(f"K{i}" for i in range(1, 8)), *(f"D{i}" for i in range(1, 8))},
}


def build_part(item, nets, nc_net, Part):
    device = item["device"]
    if device not in SYMBOLS:
        raise ValueError(f"{item['ref']}: no KiCad symbol mapping for {device}")
    library, symbol = SYMBOLS[device]
    part = Part(library, symbol, ref=item["ref"])
    part.footprint = FOOTPRINTS[device]
    if "value" in item:
        part.value = item["value"]

    for pin_spec in item.get("pins", []):
        pin = resolve_pin(part, pin_spec)
        if pin_spec["net"] == "UNUSED_DECODER_OUTPUT":
            pin += nc_net
        else:
            pin += nets[pin_spec["net"]]

    for pin in part.pins:
        if pin.net is None:
            pin += nc_net
    return part


def build_circuit(metadata, NCNet, Net, Part, POWER, subcircuit):
    ref_groups = {
        ref: group_name
        for group_name, refs in GROUPS.items()
        for ref in refs
    }
    net_groups = {}
    for item in metadata["parts"]:
        group_name = ref_groups[item["ref"]]
        for pin_spec in item.get("pins", []):
            net_groups.setdefault(pin_spec["net"], set()).add(group_name)

    root_net_names = {power["name"] for power in metadata.get("power", [])}
    root_net_names.update(
        net_name for net_name, groups in net_groups.items() if len(groups) > 1
    )
    nets = {}
    parts = {}
    nc_net = NCNet()
    for power in metadata.get("power", []):
        nets[power["name"]] = Net(power["name"])
        nets[power["name"]].drive = POWER

    for net_name in root_net_names - set(nets):
        nets[net_name] = Net(net_name)

    grouped_refs = set()
    for group_name, refs in GROUPS.items():
        with subcircuit(group_name):
            local_nets = {
                net_name: Net(net_name)
                for net_name, groups in net_groups.items()
                if group_name in groups and net_name not in root_net_names
            }
            group_nets = {**nets, **local_nets}
            for item in metadata["parts"]:
                if item["ref"] in refs:
                    parts[item["ref"]] = build_part(item, group_nets, nc_net, Part)
                    grouped_refs.add(item["ref"])
            if group_name == "mcu_control":
                for index, power_name in enumerate(("+5V", "+12V", "GND"), start=1):
                    flag = Part("power", "PWR_FLAG", ref=f"#FLG{index:03d}")
                    flag[1] += nets[power_name]

    ungrouped = [item["ref"] for item in metadata["parts"] if item["ref"] not in grouped_refs]
    if ungrouped:
        raise ValueError(f"Ungrouped parts must be assigned to an electrical sheet: {ungrouped}")

    return parts


def space_global_labels(output_dir: Path) -> int:
    """Move labels onto collision-aware wire tails away from component pins."""
    label_pattern = re.compile(r"(?ms)^  \(global_label .*?(?=^  \(|\Z)")
    name_pattern = re.compile(r'^  \(global_label "([^"]+)"')
    at_pattern = re.compile(r"\(at (-?[0-9.]+) (-?[0-9.]+) (-?[0-9.]+)\)")
    symbol_pattern = re.compile(r"(?ms)^  \(symbol\n    \(lib_id \"([^\"]+)\".*?(?=^  \(symbol|\Z)")
    moved = 0
    for path in output_dir.glob("*.kicad_sch"):
        text = path.read_text(encoding="utf-8")
        blocks = list(label_pattern.finditer(text))
        if not blocks:
            continue
        envelopes = []
        for symbol in symbol_pattern.finditer(text):
            if not symbol.group(1).startswith(("MCU_Microchip_PIC16:", "4xxx_IEEE:", "Transistor_Array:")):
                continue
            symbol_at = at_pattern.search(symbol.group(0))
            if symbol_at is None:
                continue
            center_x, center_y = (float(value) for value in symbol_at.groups()[:2])
            radius_x, radius_y = (28.0, 40.0) if symbol.group(1).startswith("MCU_") else (24.0, 30.0)
            envelopes.append((center_x - radius_x, center_y - radius_y, center_x + radius_x, center_y + radius_y))
        additions = []
        used_boxes = []
        rewritten = []
        cursor = 0
        for index, match in enumerate(blocks):
            block = match.group(0)
            name = name_pattern.match(block)
            at = at_pattern.search(block)
            if at is None or name is None:
                continue
            x, y, angle = (float(value) for value in at.groups())
            horizontal = int(angle) % 180 == 0
            direction = -1 if int(angle) % 360 == 180 else 1
            label_width = max(6.0, len(name.group(1)) * 0.8)
            distance = 10.0 + label_width
            target_x = x + direction * distance if horizontal else x
            target_y = y if horizontal else y + direction * distance
            while any(left < target_x < right and top < target_y < bottom for left, top, right, bottom in envelopes):
                if horizontal:
                    target_x += direction * 2.54
                else:
                    target_y += direction * 2.54
            while True:
                box = (
                    target_x - label_width,
                    target_y - 1.5,
                    target_x + label_width,
                    target_y + 1.5,
                )
                overlaps = any(
                    box[0] < other[2]
                    and box[2] > other[0]
                    and box[1] < other[3]
                    and box[3] > other[1]
                    for other in used_boxes
                )
                if not overlaps:
                    used_boxes.append(box)
                    break
                if horizontal:
                    target_x += direction * 2.54
                else:
                    target_y += direction * 2.54
            replacement = f"(at {target_x:.3f} {target_y:.3f} {angle:g})"
            block = block[: at.start()] + replacement + block[at.end() :]
            rewritten.append(text[cursor : match.start()])
            rewritten.append(block)
            cursor = match.end()
            additions.append(
                "  (wire\n"
                "    (pts\n"
                f"      (xy {x:.3f} {y:.3f})\n"
                f"      (xy {target_x:.3f} {target_y:.3f}))\n"
                "    (stroke\n"
                "      (width 0)\n"
                "      (type default))\n"
                f"    (uuid {uuid.uuid4()}))\n"
            )
            moved += 1
        rewritten.append(text[cursor:])
        updated = "".join(rewritten)
        if additions:
            updated = updated.rstrip()[:-1] + "\n" + "".join(additions) + ")\n"
            path.write_text(updated, encoding="utf-8", newline="\n")
    return moved

def inline_local_labels(output_dir: Path, local_net_names: set[str]) -> int:
    """Replace same-sheet labels with orthogonal wires between their endpoints."""
    label_pattern = re.compile(r"(?ms)^  \(global_label .*?(?=^  \(|\Z)")
    name_pattern = re.compile(r'^  \(global_label "([^"]+)"')
    at_pattern = re.compile(r"\(at (-?[0-9.]+) (-?[0-9.]+) (-?[0-9.]+)\)")
    inlined = 0
    for path in output_dir.glob("*.kicad_sch"):
        text = path.read_text(encoding="utf-8")
        matches = list(label_pattern.finditer(text))
        grouped = {}
        for match in matches:
            name = name_pattern.match(match.group(0))
            at = at_pattern.search(match.group(0))
            if name and at and name.group(1) in local_net_names:
                grouped.setdefault(name.group(1), []).append((match, at))
        remove = set()
        additions = []
        for entries in grouped.values():
            if len(entries) < 2:
                continue
            points = []
            for match, at in entries:
                points.append(tuple(float(value) for value in at.groups()[:2]))
                remove.add((match.start(), match.end()))
            anchor_x, anchor_y = points[0]
            for point_x, point_y in points[1:]:
                corner_x = point_x
                corner_y = anchor_y
                for start, end in ((
                    (anchor_x, anchor_y),
                    (corner_x, corner_y),
                ), (
                    (corner_x, corner_y),
                    (point_x, point_y),
                )):
                    if start == end:
                        continue
                    additions.append(
                        "  (wire\n"
                        "    (pts\n"
                        f"      (xy {start[0]:.3f} {start[1]:.3f})\n"
                        f"      (xy {end[0]:.3f} {end[1]:.3f}))\n"
                        "    (stroke\n"
                        "      (width 0)\n"
                        "      (type default))\n"
                        f"    (uuid {uuid.uuid4()}))\n"
                    )
                anchor_x, anchor_y = point_x, point_y
            inlined += len(entries)
        if remove:
            updated = text
            for start, end in sorted(remove, reverse=True):
                updated = updated[:start] + updated[end:]
            updated = updated.rstrip()[:-1] + "\n" + "".join(additions) + ")\n"
            path.write_text(updated, encoding="utf-8", newline="\n")
    return inlined


def move_fan_branch(output_dir: Path) -> int:
    """Move the fan and MOSFET to the right of the MCU and carry nearby wires."""
    symbol_pattern = re.compile(r"(?ms)^  \(symbol\n    \(lib_id .*?(?=^  \(symbol|\Z)")
    reference_pattern = re.compile(r'property "Reference" "(Q1|FAN1)"')
    at_pattern = re.compile(r"\(at (-?[0-9.]+) (-?[0-9.]+) (-?[0-9.]+)\)")
    wire_pattern = re.compile(r"(?ms)^  \(wire\n.*?(?=^  \(|\Z)")
    point_pattern = re.compile(r"\(xy (-?[0-9.]+) (-?[0-9.]+)\)")
    targets = {"Q1": (178.0, 102.0), "FAN1": (178.0, 82.0)}
    moved = 0
    for path in output_dir.glob("*.kicad_sch"):
        text = path.read_text(encoding="utf-8")
        moves = {}
        replacements = []
        for symbol in symbol_pattern.finditer(text):
            reference = reference_pattern.search(symbol.group(0))
            at = at_pattern.search(symbol.group(0))
            if not reference or not at:
                continue
            ref = reference.group(1)
            old = tuple(float(value) for value in at.groups()[:2])
            target = targets[ref]
            moves[ref] = (old, target)
            block = symbol.group(0)
            replacement = f"(at {target[0]:.3f} {target[1]:.3f} {at.group(3)})"
            block = block[: at.start()] + replacement + block[at.end() :]
            replacements.append((symbol.start(), symbol.end(), block))
            moved += 1
        for start, end, replacement in reversed(replacements):
            text = text[:start] + replacement + text[end:]

        if not moves:
            continue
        for match in list(wire_pattern.finditer(text)):
            points = list(point_pattern.finditer(match.group(0)))
            changed = False
            block = match.group(0)
            for point in points:
                x, y = (float(value) for value in point.groups())
                for old, target in moves.values():
                    if (x - old[0]) ** 2 + (y - old[1]) ** 2 <= 12**2:
                        replacement = f"(xy {x + target[0] - old[0]:.3f} {y + target[1] - old[1]:.3f})"
                        block = block.replace(point.group(0), replacement, 1)
                        changed = True
                        break
            if changed:
                text = text.replace(match.group(0), block, 1)
        path.write_text(text, encoding="utf-8", newline="\n")
    return moved


def orthogonalize_wires(output_dir: Path) -> int:
    """Replace every diagonal wire with a collision-resistant Manhattan detour."""
    wire_pattern = re.compile(r"(?ms)^  \(wire\n.*?(?=^  \(|\Z)")
    point_pattern = re.compile(r"\(xy (-?[0-9.]+) (-?[0-9.]+)\)")
    changed = 0
    for path in output_dir.glob("*.kicad_sch"):
        text = path.read_text(encoding="utf-8")
        replacements = []
        for match in wire_pattern.finditer(text):
            points = list(point_pattern.finditer(match.group(0)))
            if len(points) != 2:
                continue
            x1, y1 = (float(value) for value in points[0].groups())
            x2, y2 = (float(value) for value in points[1].groups())
            if x1 == x2 or y1 == y2:
                continue
            left = min(x1, x2) - 10.0
            bottom = max(y1, y2) + 10.0
            route = [(x1, y1), (left, y1), (left, bottom), (x2, bottom), (x2, y2)]
            blocks = []
            for start, end in zip(route, route[1:]):
                blocks.append(
                    "  (wire\n"
                    "    (pts\n"
                    f"      (xy {start[0]:.3f} {start[1]:.3f})\n"
                    f"      (xy {end[0]:.3f} {end[1]:.3f}))\n"
                    "    (stroke\n"
                    "      (width 0)\n"
                    "      (type default))\n"
                    f"    (uuid {uuid.uuid4()}))"
                )
            replacements.append((match.start(), match.end(), "\n".join(blocks) + "\n"))
            changed += 1
        for start, end, replacement in reversed(replacements):
            text = text[:start] + replacement + text[end:]
        path.write_text(text, encoding="utf-8", newline="\n")
    return changed


def validate_visual_layout(output_dir: Path) -> None:
    """Reject layout defects that ERC and KiCad parsing do not detect."""
    symbol_pattern = re.compile(r"(?ms)^  \(symbol\n    \(lib_id \"([^\"]+)\".*?(?=^  \(symbol|\Z)")
    reference_pattern = re.compile(r'property "Reference" "([^\"]+)"')
    field_pattern = re.compile(r'property "(Reference|Value)" "([^\"]+)".*?\(at (-?[0-9.]+) (-?[0-9.]+)')
    at_pattern = re.compile(r"\(at (-?[0-9.]+) (-?[0-9.]+) [^\)]+\)")
    label_pattern = re.compile(r"(?ms)^  \(global_label .*?(?=^  \(|\Z)")
    label_name = re.compile(r'^  \(global_label "([^"]+)"')
    point_pattern = re.compile(r"\(xy (-?[0-9.]+) (-?[0-9.]+)\)")
    failures = []
    for path in output_dir.glob("*.kicad_sch"):
        text = path.read_text(encoding="utf-8")
        if re.search(r'property "Reference" "[^"#][^"?]*\?"', text):
            failures.append(f"{path.name}: unresolved component reference")

        envelopes = []
        for symbol in symbol_pattern.finditer(text):
            lib_id = symbol.group(1)
            if not lib_id.startswith(("MCU_Microchip_PIC16:", "4xxx_IEEE:", "Transistor_Array:")):
                continue
            at = at_pattern.search(symbol.group(0))
            if not at:
                continue
            center_x, center_y = (float(value) for value in at.groups()[:2])
            radius_x, radius_y = (28.0, 40.0) if lib_id.startswith("MCU_") else (24.0, 30.0)
            envelopes.append((center_x, center_y, radius_x, radius_y, symbol.group(0)))
            for field in field_pattern.finditer(symbol.group(0)):
                field_x, field_y = float(field.group(3)), float(field.group(4))
                inside = abs(field_x - center_x) <= radius_x and abs(field_y - center_y) <= radius_y
                above = field_y < center_y - radius_y and abs(field_x - center_x) <= radius_x
                if not inside and not above:
                    failures.append(f"{path.name}: {field.group(1)} field outside IC envelope")

        labels = []
        for label in label_pattern.finditer(text):
            name = label_name.match(label.group(0))
            at = at_pattern.search(label.group(0))
            if not name or not at:
                continue
            x, y = (float(value) for value in at.groups()[:2])
            width = max(6.0, len(name.group(1)) * 0.8)
            box = (x - width, y - 1.5, x + width, y + 1.5)
            labels.append((name.group(1), box))
            for center_x, center_y, radius_x, radius_y, _ in envelopes:
                if center_x - radius_x < x < center_x + radius_x and center_y - radius_y < y < center_y + radius_y:
                    failures.append(f"{path.name}: label {name.group(1)} inside IC envelope")
        for index, (left_name, left_box) in enumerate(labels):
            for right_name, right_box in labels[index + 1:]:
                if left_box[0] < right_box[2] and left_box[2] > right_box[0] and left_box[1] < right_box[3] and left_box[3] > right_box[1]:
                    failures.append(f"{path.name}: labels {left_name} and {right_name} overlap")

        for wire in re.finditer(r"(?ms)^  \(wire\n.*?(?=^  \(|\Z)", text):
            points = list(point_pattern.finditer(wire.group(0)))
            if len(points) >= 2:
                x1, y1 = (float(value) for value in points[0].groups())
                x2, y2 = (float(value) for value in points[1].groups())
                if x1 != x2 and y1 != y2:
                    failures.append(f"{path.name}: diagonal wire")
    if failures:
        raise RuntimeError("Visual schematic validation failed:\n" + "\n".join(sorted(set(failures))))


def protect_ic_envelopes(output_dir: Path) -> int:
    """Reroute wires that enter IC body/pin envelopes around their clear side."""
    symbol_pattern = re.compile(r"(?ms)^  \(symbol\n    \(lib_id \"([^\"]+)\".*?(?=^  \(symbol|\Z)")
    at_pattern = re.compile(r"\(at (-?[0-9.]+) (-?[0-9.]+) [^\)]+\)")
    wire_pattern = re.compile(r"(?ms)^  \(wire\n.*?(?=^  \(|\Z)")
    point_pattern = re.compile(r"\(xy (-?[0-9.]+) (-?[0-9.]+)\)")
    changed = 0
    for path in output_dir.glob("*.kicad_sch"):
        text = path.read_text(encoding="utf-8")
        envelopes = []
        for symbol in symbol_pattern.finditer(text):
            lib_id = symbol.group(1)
            if not lib_id.startswith(("MCU_Microchip_PIC16:", "4xxx_IEEE:", "Transistor_Array:")):
                continue
            at = at_pattern.search(symbol.group(0))
            if not at:
                continue
            x, y = (float(value) for value in at.groups())
            radius_x, radius_y = (28.0, 40.0) if lib_id.startswith("MCU_") else (24.0, 30.0)
            envelopes.append((x - radius_x, y - radius_y, x + radius_x, y + radius_y, x, y))
        replacements = []
        for match in wire_pattern.finditer(text):
            points = list(point_pattern.finditer(match.group(0)))
            if len(points) != 2:
                continue
            p1 = tuple(float(value) for value in points[0].groups())
            p2 = tuple(float(value) for value in points[1].groups())
            route = None
            for left, top, right, bottom, cx, cy in envelopes:
                intersects = not (
                    max(p1[0], p2[0]) < left
                    or min(p1[0], p2[0]) > right
                    or max(p1[1], p2[1]) < top
                    or min(p1[1], p2[1]) > bottom
                )
                if not intersects:
                    continue
                p1_inside = left <= p1[0] <= right and top <= p1[1] <= bottom
                p2_inside = left <= p2[0] <= right and top <= p2[1] <= bottom
                if p1_inside and not p2_inside:
                    side_x = right + 5.0 if p2[0] >= cx else left - 5.0
                    route = [p1, (side_x, p1[1]), (side_x, p2[1]), p2]
                elif p2_inside and not p1_inside:
                    side_x = right + 5.0 if p1[0] >= cx else left - 5.0
                    route = [p1, (side_x, p1[1]), (side_x, p2[1]), p2]
                elif not p1_inside and not p2_inside:
                    clear_y = bottom + 5.0
                    route = [p1, (p1[0], clear_y), (p2[0], clear_y), p2]
                if route:
                    break
            if route:
                blocks = []
                for start, end in zip(route, route[1:]):
                    if start == end:
                        continue
                    blocks.append(
                        "  (wire\n"
                        "    (pts\n"
                        f"      (xy {start[0]:.3f} {start[1]:.3f})\n"
                        f"      (xy {end[0]:.3f} {end[1]:.3f}))\n"
                        "    (stroke\n"
                        "      (width 0)\n"
                        "      (type default))\n"
                        f"    (uuid {uuid.uuid4()}))"
                    )
                replacements.append((match.start(), match.end(), "\n".join(blocks) + "\n"))
                changed += 1
        for start, end, replacement in reversed(replacements):
            text = text[:start] + replacement + text[end:]
        path.write_text(text, encoding="utf-8", newline="\n")
    return changed


def move_ic_fields(output_dir: Path) -> int:
    """Put placed IC reference/value fields well left of their symbol bodies."""
    symbol_pattern = re.compile(
        r"(?ms)^  \(symbol\n    \(lib_id \"([^\"]+)\".*?(?=^  \(symbol|\Z)"
    )
    field_pattern = re.compile(
        r"(?ms)^    \(property \"(Reference|Value)\" .*?(?=^    \(property |^  \(symbol|\Z)"
    )
    at_pattern = re.compile(r"\(at (-?[0-9.]+) (-?[0-9.]+) (-?[0-9.]+)\)")
    moved = 0
    ic_libraries = ("MCU_Microchip_PIC16:", "4xxx_IEEE:", "Transistor_Array:")
    for path in output_dir.glob("*.kicad_sch"):
        text = path.read_text(encoding="utf-8")
        replacements = []
        for symbol in symbol_pattern.finditer(text):
            if not symbol.group(1).startswith(ic_libraries):
                continue
            symbol_at = at_pattern.search(symbol.group(0))
            if symbol_at is None:
                continue
            center_x, center_y, _ = (float(value) for value in symbol_at.groups())
            for field in field_pattern.finditer(symbol.group(0)):
                field_at = at_pattern.search(field.group(0))
                if field_at is None:
                    continue
                y = center_y + (-2.54 if field.group(1) == "Reference" else 2.54)
                x = center_x - (3.0 if field.group(1) == "Reference" else 10.0)
                replacement = f"(at {x:.3f} {y:.3f} 0)"
                field_text = field.group(0)
                field_text = field_text[: field_at.start()] + replacement + field_text[field_at.end() :]
                field_text = field_text.replace("\n        (justify left)", "")
                field_text = field_text.replace("\n        (justify right)", "")
                start = symbol.start() + field.start()
                end = symbol.start() + field.end()
                replacements.append((start, end, field_text))
                moved += 1
        for start, end, replacement in reversed(replacements):
            text = text[:start] + replacement + text[end:]
        path.write_text(text, encoding="utf-8", newline="\n")
    return moved


def hide_ic_pin_names(output_dir: Path) -> int:
    """Hide library pin-name annotations so IC bodies show only ref/value text."""
    pattern = re.compile(r"(?ms)(^    \(symbol \"(?:MCU_Microchip_PIC16|4xxx_IEEE|Transistor_Array):.*?)(?=^    \(symbol |\Z)")
    pin_names = re.compile(r"\(pin_names\n        \(offset ([^\)]+)\)\)")
    changed = 0
    for path in output_dir.glob("*.kicad_sch"):
        text = path.read_text(encoding="utf-8")

        def replace_symbol(match):
            nonlocal changed
            block = match.group(0)
            updated, count = pin_names.subn(
                r"(pin_names\n        (offset \1)\n        (hide yes))",
                block,
            )
            changed += count
            return updated

        updated = pattern.sub(replace_symbol, text)
        path.write_text(updated, encoding="utf-8", newline="\n")
    return changed


def snap_geometry(output_dir: Path) -> int:
    """Snap generated coordinates to KiCad's 1.27 mm connection grid."""
    coordinate = re.compile(r"\((xy|at) (-?[0-9.]+) (-?[0-9.]+)([^\)]*)\)")
    block_pattern = re.compile(r"(?ms)^  \((?:wire|global_label|label) .*?(?=^  \(|\Z)")
    changed = 0
    for path in output_dir.glob("*.kicad_sch"):
        text = path.read_text(encoding="utf-8")

        def snap(match):
            nonlocal changed
            x, y = (float(value) for value in match.groups()[1:3])
            snapped_x = round(x / 1.27) * 1.27
            snapped_y = round(y / 1.27) * 1.27
            if abs(snapped_x - x) > 0.0001 or abs(snapped_y - y) > 0.0001:
                changed += 1
            return f"({match.group(1)} {snapped_x:.3f} {snapped_y:.3f}{match.group(4)})"

        def snap_block(match):
            return coordinate.sub(snap, match.group(0))

        path.write_text(block_pattern.sub(snap_block, text), encoding="utf-8", newline="\n")
    return changed


def normalize_singleton_labels(output_dir: Path) -> int:
    """Use local labels for one-ended external signals to avoid dangling globals."""
    label_pattern = re.compile(r"(?ms)^  \(global_label \"([^\"]+)\".*?(?=^  \(|\Z)")
    occurrences = {}
    files = list(output_dir.glob("*.kicad_sch"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        for match in label_pattern.finditer(text):
            occurrences[match.group(1)] = occurrences.get(match.group(1), 0) + 1
    changed = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        for name, count in occurrences.items():
            if count != 1:
                continue
            pattern = re.compile(rf'(?m)^  \(global_label "{re.escape(name)}"')
            text, replacements = pattern.subn(f'  (label "{name}"', text)
            changed += replacements
        path.write_text(text, encoding="utf-8", newline="\n")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("docs/hardware/project_schematic_package/project_schematic.asg.toml"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/hardware/project_schematic_package/generated"),
    )
    parser.add_argument(
        "--symbols",
        type=Path,
        default=Path(r"C:\Program Files\KiCad\9.0\share\kicad\symbols"),
    )
    args = parser.parse_args()

    configure_kicad_symbols(args.symbols.resolve())
    NCNet, Net, Part, POWER, generate_schematic, subcircuit = load_skidl()
    metadata = tomllib.loads(args.input.read_text(encoding="utf-8"))
    build_circuit(metadata, NCNet, Net, Part, POWER, subcircuit)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    generate_schematic(
        filepath=str(args.output_dir.resolve()),
        top_name="pic_amp_protection",
        title=metadata["board"],
        flatness=0.0,
        auto_stub=True,
        retries=1,
        auto_stub_fallback="labels",
        auto_stub_fanout=100,
        auto_stub_max_wire_pins=100,
        auto_stub_max_wire_dist=100000,
    )
    structured_moves = structured_layout(args.output_dir)
    if os.environ.get("SCHEMATIC_POSTPROCESS") != "1":
        validate_with_kicad(args.output_dir / "pic_amp_protection.kicad_sch")
        print(f"Moved {structured_moves} components with KiCad API")
        print("Electrically safe structured schematic validation passed")
        return
    ref_groups = {
        ref: group_name for group_name, refs in GROUPS.items() for ref in refs
    }
    net_groups = {}
    for item in metadata["parts"]:
        for pin_spec in item.get("pins", []):
            net_groups.setdefault(pin_spec["net"], set()).add(ref_groups[item["ref"]])
    local_net_names = {
        net_name for net_name, groups in net_groups.items() if len(groups) == 1
    }

    moved_labels = space_global_labels(args.output_dir)
    moved_fields = move_ic_fields(args.output_dir)
    hidden_pin_names = 0
    inlined_labels = 0
    orthogonal_wires = orthogonalize_wires(args.output_dir)
    singleton_labels = normalize_singleton_labels(args.output_dir)
    snapped_coordinates = snap_geometry(args.output_dir)
    validate_visual_layout(args.output_dir)
    validate_with_kicad(args.output_dir / "pic_amp_protection.kicad_sch")
    print(f"Moved {moved_labels} global labels onto spaced wire tails")
    print(f"Moved {moved_fields} IC reference/value fields left of their bodies")
    print(f"Hidden {hidden_pin_names} IC pin-name annotations")
    print(f"Inlined {inlined_labels} same-sheet labels as wires")
    print(f"Orthogonalized {orthogonal_wires} diagonal wire segments")
    print(f"Normalized {singleton_labels} singleton labels")
    print(f"Snapped {snapped_coordinates} coordinates to the KiCad grid")
    print("Visual layout and KiCad CLI validation passed")


if __name__ == "__main__":
    main()
