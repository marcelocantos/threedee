# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

import json
import runpy
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("fuzzy_3mf.py")
AMS_LOAD = "M620 S[initial_no_support_extruder]A\n"


@pytest.mark.parametrize("include_ams", [True, False], ids=["included-ams", "missing-ams"])
def test_fuzzy_project_requires_and_preserves_ams_start(tmp_path, monkeypatch, include_ams):
    root = tmp_path / "presets"
    records = {
        "machine/base.json": {"name": "Base", "machine_start_gcode": "G28\n"},
        "machine/printer.json": {
            "name": "Bambu Lab X1 Carbon 0.4 nozzle",
            "inherits": "Base",
            "include": ["AMS"] if include_ams else [],
        },
        "process/standard.json": {
            "name": "0.20mm Standard @BBL X1C", "include": ["Process Defaults"],
        },
        "process/defaults.json": {"name": "Process Defaults", "layer_height": "0.2"},
        "filament/pla.json": {
            "name": "Bambu PLA Basic @BBL X1C", "include": ["Filament Defaults"],
        },
        "filament/ams.json": {"name": "AMS", "machine_start_gcode": AMS_LOAD},
        "filament/defaults.json": {"name": "Filament Defaults", "nozzle_temperature": ["220"]},
    }
    for relative, data in records.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    settings = {}

    def slicer(command, **kwargs):
        machine, process = command[command.index("--load-settings") + 1].split(";")
        filament = command[command.index("--load-filaments") + 1]
        for path in map(Path, (machine, process, filament)):
            settings[path.stem] = json.loads(path.read_text())
        assembled = command[command.index("--export-3mf") + 1]
        with zipfile.ZipFile(assembled, "w") as archive:
            archive.writestr("Metadata/project_settings.config", json.dumps(settings["machine"]))
            archive.writestr(
                "Metadata/model_settings.config",
                '<part id="2" subtype="normal_part">\n'
                '<metadata key="name" value="puzzle-tray-grip-modifier.stl"/></part>',
            )
            archive.writestr("Metadata/plate_1.gcode", "stale")

    out = tmp_path / "tray.3mf"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(subprocess, "run", slicer)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--presets", str(root), "--out", str(out)])

    if include_ams:
        runpy.run_path(str(SCRIPT), run_name="__main__")
        with zipfile.ZipFile(out) as archive:
            machine = json.loads(archive.read("Metadata/project_settings.config"))
            assert machine["machine_start_gcode"] == AMS_LOAD
            assert b'modifier_part' in archive.read("Metadata/model_settings.config")
            assert "Metadata/plate_1.gcode" not in archive.namelist()
        assert settings["process"]["layer_height"] == "0.2"
        assert settings["filament"]["nozzle_temperature"] == ["220"]
        for preset in settings.values():
            assert preset["from"] == "system"
            assert "inherits" not in preset and "include" not in preset
    else:
        with pytest.raises(SystemExit, match=r"machine_start_gcode has no M620 S\["):
            runpy.run_path(str(SCRIPT), run_name="__main__")
        assert not settings
        assert not out.exists()
