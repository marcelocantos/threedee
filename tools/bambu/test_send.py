# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

SENDER = Path(__file__).with_name("send.py")


def _check(path):
    # Isolated mode excludes the sibling credential loader and site packages.
    return subprocess.run(
        [sys.executable, "-I", "-S", str(SENDER), str(path), "--ams-tray", "0", "--check"],
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "gcode, expected",
    [
        ("M620 S0A\n", 0),
        ("  M620\tS0A  ; load AMS\n", 0),
        ("; M620 S0A\nG90 ; M620 S0A\n", 1),
        ("M117 M620 S0A\n", 1),
        ("M620 S0AA\n", 1),
    ],
    ids=["real-command", "spacing", "comment", "different-command", "argument-lookalike"],
)
def test_offline_check_requires_an_actual_ams_load(tmp_path, gcode, expected):
    path = tmp_path / "part.gcode"
    path.write_text(gcode)

    completed = _check(path)

    assert completed.returncode == expected, completed.stderr
    assert ("found" if expected == 0 else "MISSING") + " M620 S0A in plate gcode" in completed.stdout


@pytest.mark.parametrize("plate_one_has_load", [False, True])
def test_offline_zip_check_chooses_plate_one(tmp_path, plate_one_has_load):
    path = tmp_path / "part.gcode.3mf"
    load = "M620 S0A\n"
    missing = "G90\n"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Metadata/plate_2.gcode", missing if plate_one_has_load else load)
        archive.writestr("Metadata/plate_1.gcode", load if plate_one_has_load else missing)

    completed = _check(path)

    assert completed.returncode == (0 if plate_one_has_load else 1), completed.stderr
    assert ("found" if plate_one_has_load else "MISSING") + " M620 S0A in plate gcode" in completed.stdout
