#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Flatten Bambu Studio system presets, resolving both inherits and include.

Merge precedence (lowest to highest), matching Studio:

  1. inherited parent, fully flattened (its own inherits + includes + keys)
  2. include templates, applied in list order (later includes override earlier)
     Includes act as defaults for this preset and override inherited values
     (this is how the X1C start-gcode templates replace fdm_machine_common).
  3. the preset's own keys (highest priority)

Templates are looked up by name in the same subtree first, then by name
across machine/process/filament.

Skipping `include` is what produced the first mixer-stand slice: a generic
start sequence with no AMS load, so the printer ran every move with an
empty toolhead. After flattening, `machine_start_gcode` must contain
`M620 S[initial_no_support_extruder]A` (and usually the matching `M621`
and `G1 E50`). Slicing turns that template into a real `M620 S0A`.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

DEFAULT_PRESETS = Path.home() / "Library/Application Support/BambuStudio/system/BBL"
DEFAULT_MACHINE = "Bambu Lab X1 Carbon 0.4 nozzle"
DEFAULT_PROCESS = "0.20mm Standard @BBL X1C"
DEFAULT_FILAMENT = "Bambu PLA Basic @BBL X1C"
MISSING_AMS_START = (
    "error: flattened machine_start_gcode has no M620 S[...]; "
    "include templates were probably not resolved"
)


def load_index(root: Path) -> tuple[dict, dict]:
    idx, by_name = {}, {}
    for sub in ("machine", "process", "filament"):
        for f in glob.glob(str(root / sub / "**" / "*.json"), recursive=True):
            try:
                data = json.loads(Path(f).read_text())
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            name = data.get("name")
            if not isinstance(name, str) or not name:
                continue
            idx[(sub, name)] = data
            by_name.setdefault(name, data)
    return idx, by_name


def resolve(idx, by_name, sub, name, seen=None):
    if seen is None:
        seen = set()
    key = (sub, name)
    if key in seen:
        raise SystemExit(f"cycle in preset inheritance/include: {sub}/{name}")
    data = idx.get(key) or by_name.get(name)
    if not data:
        raise SystemExit(f"missing preset {sub}/{name}")
    seen = seen | {key}
    out = {}
    if data.get("inherits"):
        out.update(resolve(idx, by_name, sub, data["inherits"], seen))
    for inc in data.get("include") or []:
        out.update(resolve(idx, by_name, sub, inc, seen))
    out.update(data)
    out.pop("inherits", None)
    out.pop("include", None)
    return out


def has_ams_start(data: dict) -> bool:
    start = data.get("machine_start_gcode", "")
    # Studio stores a template; slicing turns this into M620 S0A.
    return isinstance(start, str) and "M620 S[" in start


def flatten(idx, by_name, sub, name, dest: Path, extra=None) -> dict:
    data = resolve(idx, by_name, sub, name)
    if extra:
        data.update(extra)
    dest.write_text(json.dumps(data, indent=1) + "\n")
    start = data.get("machine_start_gcode", "")
    start_len = len(start) if isinstance(start, str) else None
    has_m621 = isinstance(start, str) and "M621 S[" in start
    has_e50 = isinstance(start, str) and "G1 E50" in start
    print(
        dest,
        "nkeys", len(data),
        "start_gcode", start_len,
        "M620_S[", has_ams_start(data),
        "M621_S[", has_m621,
        "E50", has_e50,
        "colour", data.get("filament_colour"),
        "printer_model", data.get("printer_model"),
        "printer_model_id", data.get("printer_model_id"),
        "nozzle_temperature", data.get("nozzle_temperature"),
        flush=True,
    )
    return data


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--presets", type=Path, default=DEFAULT_PRESETS)
    p.add_argument("--machine", default=DEFAULT_MACHINE)
    p.add_argument("--process", default=DEFAULT_PROCESS)
    p.add_argument("--filament", default=DEFAULT_FILAMENT)
    p.add_argument("--out-dir", type=Path, default=Path("."))
    p.add_argument(
        "--filament-map",
        default=None,
        help="0-based AMS tray id for sliced filament 0, e.g. 1 for slot 2",
    )
    p.add_argument("--filament-colour", default=None, help="e.g. #9D432C for PLA Basic Brown")
    p.add_argument("--bed-type", default="Textured PEI Plate")
    p.add_argument(
        "--printer-model-id",
        default="BL-P001",
        help="X1 Carbon model id; the Studio CLI often leaves this blank",
    )
    args = p.parse_args(argv)

    idx, by_name = load_index(args.presets)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    machine_extra = {}
    if args.printer_model_id:
        machine_extra["printer_model_id"] = args.printer_model_id
    process_extra = {}
    if args.filament_map is not None:
        process_extra["filament_map"] = [str(args.filament_map)]
    if args.bed_type:
        process_extra["curr_bed_type"] = args.bed_type
    filament_extra = {}
    if args.filament_colour:
        filament_extra["filament_colour"] = [args.filament_colour]

    machine = flatten(idx, by_name, "machine", args.machine, args.out_dir / "machine.json", machine_extra)
    flatten(idx, by_name, "process", args.process, args.out_dir / "process.json", process_extra)
    flatten(idx, by_name, "filament", args.filament, args.out_dir / "filament.json", filament_extra)

    if not has_ams_start(machine):
        print(MISSING_AMS_START, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
