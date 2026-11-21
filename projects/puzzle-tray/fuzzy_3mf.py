# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Build a Bambu Studio project with fuzzy skin on the grip channels only.

Run from export/ after puzzle_tray.py. It flattens the installed Bambu
system presets (X1 Carbon 0.4 nozzle, 0.20mm Standard, Bambu PLA Basic),
has the Bambu Studio command line assemble the tray and the grip modifier
into one object and slice it once (so the project is complete), then marks
the second part as a modifier with fuzzy skin on outer walls and drops the
stale slice. Open the result in Bambu Studio, pick the filament, and slice.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.bambu.flatten import (  # noqa: E402
    DEFAULT_FILAMENT,
    DEFAULT_MACHINE,
    DEFAULT_PRESETS,
    DEFAULT_PROCESS,
    MISSING_AMS_START,
    has_ams_start,
    load_index,
    resolve,
)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--studio", default="/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
parser.add_argument("--presets", type=Path, default=DEFAULT_PRESETS)
parser.add_argument("--thickness", default="0.3", help="Fuzzy skin thickness (mm)")
parser.add_argument("--point-distance", default="0.8", help="Fuzzy skin point distance (mm)")
parser.add_argument("--out", default="puzzle-tray-fuzzy-grips.3mf")
args = parser.parse_args()

TRAY, MOD = "puzzle-tray.stl", "puzzle-tray-grip-modifier.stl"
PRESETS = [("machine", DEFAULT_MACHINE), ("process", DEFAULT_PROCESS), ("filament", DEFAULT_FILAMENT)]
index, by_name = load_index(args.presets)

with tempfile.TemporaryDirectory() as tmp:
    files = []
    for kind, name in PRESETS:
        d = resolve(index, by_name, kind, name)
        if kind == "machine" and not has_ams_start(d):
            raise SystemExit(MISSING_AMS_START)
        d["from"] = "system"
        path = Path(tmp) / f"{kind}.json"
        path.write_text(json.dumps(d))
        files.append(path)
    assembled = os.path.join(tmp, "assembled.3mf")
    subprocess.run([args.studio, "--debug", "1", "--arrange", "0", "--assemble", "--slice", "0",
                    "--load-settings", f"{files[0]};{files[1]}", "--load-filaments", str(files[2]),
                    "--export-3mf", assembled, os.path.abspath(TRAY), os.path.abspath(MOD)],
                   check=True, capture_output=True)
    if not os.path.exists(assembled):
        raise SystemExit("Bambu Studio CLI did not write the project")

    zin = zipfile.ZipFile(assembled)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if re.match(r"Metadata/(plate_\d+\.gcode(\.md5)?|slice_info\.config|plate_\d+\.json)$", item.filename):
                continue  # stale slice of the unmodified assembly
            data = zin.read(item.filename)
            if item.filename == "Metadata/model_settings.config":
                s = data.decode()
                pat = (r'<part id="(\d+)" subtype="normal_part"( uuid="[^"]*")?>\s*'
                       rf'<metadata key="name" value="{re.escape(MOD)}"/>')
                m = re.search(pat, s)
                if not m:
                    raise SystemExit("Modifier part not found in the assembled project")
                s = (s[:m.start()]
                     + f'<part id="{m.group(1)}" subtype="modifier_part"{m.group(2) or ""}>\n'
                     + f'      <metadata key="name" value="{MOD}"/>\n'
                     + '      <metadata key="fuzzy_skin" value="external"/>\n'
                     + f'      <metadata key="fuzzy_skin_thickness" value="{args.thickness}"/>\n'
                     + f'      <metadata key="fuzzy_skin_point_distance" value="{args.point_distance}"/>'
                     + s[m.end():])
                s = re.sub(r'\s*<metadata key="gcode_file" value="[^"]*"/>', "", s)
                data = s.encode()
            zout.writestr(item, data)
print(f"wrote {args.out}: fuzzy skin (outer walls, {args.thickness} mm, {args.point_distance} mm) on the grip modifier")
