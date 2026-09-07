# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Geometry oracles for the build123d parts.

`make` only checks that the interpreter did not throw, which every defect so
far has passed. These tests build a part and assert where it actually is in
space, so a part that silently moves fails the gate.
"""

import pathlib

import pytest

PROJECTS = pathlib.Path(__file__).resolve().parent.parent / "projects"

# Positional tolerance in mm: tight enough to catch a misplaced feature,
# loose enough for OCCT's tessellation of the filleted edges.
TOLERANCE = 0.05


def build(script_name):
    """Run a project script up to (not including) its first export, and
    return its `result` solid. Exports are skipped so tests write no files."""
    source = (PROJECTS / script_name).read_text()
    marker = "export_stl("
    assert marker in source, f"{script_name} has no export_stl call"
    namespace = {"__name__": "__test__"}
    exec(compile(source[: source.index(marker)], script_name, "exec"), namespace)
    return namespace["result"]


@pytest.fixture(scope="module")
def catflap():
    return build("catflap_rpi.py")


def test_catflap_shell_sits_in_the_scad_frame(catflap):
    """catflap-rpi.scad puts the shell at x in [-cam, box_l - 0.5],
    y in [0, box_w], z in [0, box_h]. The Python port applied the -cam shift
    twice (and never shifted y off centre), putting the shell at
    x in [-110.05, 6.05], y in [-30.75, 30.75]."""
    cam, box_l, box_w, box_h = 26, 90.6, 61.5, 30
    bbox = catflap.bounding_box()

    assert bbox.min.X == pytest.approx(-cam, abs=TOLERANCE)
    assert bbox.max.X == pytest.approx(box_l - 0.5, abs=TOLERANCE)
    assert bbox.min.Y == pytest.approx(0, abs=TOLERANCE)
    assert bbox.max.Y == pytest.approx(box_w, abs=TOLERANCE)
    assert bbox.min.Z == pytest.approx(0, abs=TOLERANCE)
    assert bbox.max.Z == pytest.approx(box_h, abs=TOLERANCE)
