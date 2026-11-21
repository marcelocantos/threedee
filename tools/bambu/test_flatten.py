# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

import json
import subprocess
import sys
from pathlib import Path

import pytest

from flatten import load_index

FLATTENER = Path(__file__).with_name("flatten.py")
AMS_LOAD = "M620 S[initial_no_support_extruder]A"


@pytest.fixture
def preset_tree(tmp_path):
    root = tmp_path / "presets"
    records = {
        "machine/common.json": {
            "name": "Common", "layer": "base", "machine_start_gcode": "generic", "from_parent": "kept",
        },
        "machine/first.json": {"name": "First", "layer": "first", "override": "template", "from_first": "kept"},
        "machine/main.json": {
            "name": "Printer",
            "inherits": "Common",
            "include": ["First", "AMS"],
            "override": "printer",
        },
        "machine/shared.json": {"name": "Shared", "pick": "machine"},
        "process/shared.json": {"name": "Shared", "pick": "process"},
        "process/main.json": {"name": "Process", "include": ["Shared"]},
        "filament/templates/ams.json": {"name": "AMS", "layer": "last", "machine_start_gcode": AMS_LOAD},
        "filament/main.json": {"name": "Filament"},
    }
    for relative, data in records.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    return root


def _flatten(root, out):
    return subprocess.run(
        [
            sys.executable, str(FLATTENER), "--presets", str(root), "--out-dir", str(out),
            "--machine", "Printer", "--process", "Process", "--filament", "Filament",
            "--filament-map", "0", "--filament-colour", "#AABBCC",
        ],
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "metadata",
    [None, ["unrelated"], 5, {}, {"name": []}, {"name": {"nested": "object"}}, {"name": 50}],
    ids=["null", "array", "scalar", "unnamed", "empty-name-list", "object-name", "numeric-name"],
)
def test_offline_cli_ignores_unrelated_json(preset_tree, tmp_path, metadata):
    (preset_tree / "machine" / "metadata.json").write_text(json.dumps(metadata))
    out = tmp_path / "out"
    completed = _flatten(preset_tree, out)

    assert completed.returncode == 0, completed.stderr
    assert "M620_S[ True" in completed.stdout
    assert {path.name for path in out.iterdir()} == {"machine.json", "process.json", "filament.json"}
    assert json.loads((out / "machine.json").read_text()) == {
        "name": "Printer", "layer": "last", "machine_start_gcode": AMS_LOAD,
        "override": "printer", "printer_model_id": "BL-P001", "from_parent": "kept", "from_first": "kept",
    }
    assert json.loads((out / "process.json").read_text()) == {
        "name": "Process", "pick": "process", "filament_map": ["0"], "curr_bed_type": "Textured PEI Plate",
    }
    assert json.loads((out / "filament.json").read_text()) == {
        "name": "Filament", "filament_colour": ["#AABBCC"],
    }


def test_index_only_contains_named_presets(preset_tree):
    (preset_tree / "machine" / "metadata.json").write_text(json.dumps({"name": 50}))
    index, by_name = load_index(preset_tree)

    assert ("machine", 50) not in index
    assert 50 not in by_name
    assert ("machine", "Printer") in index


def test_offline_cli_refuses_an_include_inheritance_cycle(preset_tree, tmp_path):
    (preset_tree / "machine" / "common.json").write_text(json.dumps({"name": "Common", "include": ["Printer"]}))
    out = tmp_path / "out"
    completed = _flatten(preset_tree, out)

    assert completed.returncode == 1
    assert "cycle in preset inheritance/include: machine/Printer" in completed.stderr
    assert list(out.iterdir()) == []
