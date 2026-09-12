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


def load_until(script_name, marker):
    """Exec a project script up to `marker` and return the namespace."""
    source = (PROJECTS / script_name).read_text()
    assert marker in source, f"{script_name} has no {marker!r}"
    namespace = {"__name__": "__test__"}
    exec(compile(source[: source.index(marker)], script_name, "exec"), namespace)
    return namespace


def build(script_name):
    """Run a project script up to (not including) its first export, and
    return its `result` solid. Exports are skipped so tests write no files."""
    return load_until(script_name, "export_stl(")["result"]


def test_starlock_holder_bbox():
    """Pos * Shape inside BuildPart drops the location: stems and tabs land
    at the origin. holder(175, range(0,2), [10,-10]) currently boxes at
    z -12.5..29.2 (centered tab + one stem) instead of walking the rail."""
    holder = load_until("starlock_holders.py", "parts = []")["holder"]
    result = holder(175, range(0, 2), [10, -10])
    bbox = result.bounding_box()

    assert bbox.min.Z >= -2.0, (
        f"rail-mounted stem/tab should not sit below the rail: min.Z={bbox.min.Z}"
    )
    assert bbox.max.Z > 20, (
        f"stems should rise above the rail: max.Z={bbox.max.Z}"
    )

    # The rail is 175 mm, so a stem at x=0 vs x=76.2 does not move the
    # bounding-box centre. Volume does: a coincident union is ~one stem.
    one = holder(175, [0], [])
    two = holder(175, [0, 1], [])
    assert two.volume > one.volume + 500, (
        f"second stem did not add volume (one={one.volume}, two={two.volume})"
    )


def test_screw_box_partitions_bbox():
    """Dropped-location cylinder is extruded along Z for the full height=w,
    giving bbox size (40, 49, 49) instead of a thin partition plate."""
    result = build("screw_box_partitions.py")
    bbox = result.bounding_box()
    z_span = bbox.max.Z - bbox.min.Z
    assert z_span < 10, f"partition should be a thin plate, not z_span={z_span}"


def test_router_bit_rack_bbox():
    """Dropped-location ribs collapse to a single cell (volume 6228);
    a real lattice is an order of magnitude larger."""
    result = build("router_bit_rack.py")
    assert result.volume > 20000, (
        f"rack volume {result.volume} is ribs-only / dropped-location scale"
    )


def test_magnet_tube_bbox():
    """SCAD cylinder is min-aligned (z in 0..65 plus the barrier lip).
    Default build123d Cylinder is centered, so today's bbox is z -32.5..60.5
    with the barrier floating off the tube."""
    result = build("magnet_tube.py")
    bbox = result.bounding_box()
    assert bbox.min.Z == pytest.approx(0, abs=1.0)
    assert bbox.max.Z == pytest.approx(65, abs=1.5)


# bbox (min, max) + volume, from the post-ENT-002/003/004 geometry.
# bosch_adapter.py is omitted: build() raises "Cannot move an empty shape".
GOLDENS = {
    "baby_gate_latch.py": ((0, 0, 0), (100, 40, 10), 6466.26),
    "catflap_rpi.py": ((-26, 0, 0), (90.1, 61.5, 30), 48693.20),
    "led_stumps.py": ((-5, -5, -10), (17, 77, 10), 17537.94),
    "machinist_square_mount.py": ((0, 15, 0), (100, 65, 35), 152018.74),
    "magnet_tube.py": ((0, 0, 0), (24, 24, 65), 3880.98),
    "nailgun_tip.py": ((-4.25, -4.25, 0), (4.25, 4.25, 5), 161.13),
    "rotary_bearing.py": ((-108.54, -108.54, 0), (108.54, 108.54, 7.4), 59554.44),
    "router_bit_rack.py": ((-2, -2, -1.32), (236, 243.65, 18), 583545.87),
    "screw_box_partitions.py": ((0, 0, -0.7), (40, 49, 1.4), 1376.40),
    "starlock_holders.py": ((-125.6, -6.3, -1.75), (125.6, 83.5, 29.2), 64271.32),
    "triton_lifter.py": ((-16.37, -16.37, -1.04), (51.37, 16.37, 9.69), 9318.24),
}


@pytest.mark.parametrize("script", sorted(GOLDENS))
def test_part_golden(script):
    (min_xyz, max_xyz, volume) = GOLDENS[script]
    result = build(script)
    bbox = result.bounding_box()
    assert bbox.min.X == pytest.approx(min_xyz[0], abs=0.5)
    assert bbox.min.Y == pytest.approx(min_xyz[1], abs=0.5)
    assert bbox.min.Z == pytest.approx(min_xyz[2], abs=0.5)
    assert bbox.max.X == pytest.approx(max_xyz[0], abs=0.5)
    assert bbox.max.Y == pytest.approx(max_xyz[1], abs=0.5)
    assert bbox.max.Z == pytest.approx(max_xyz[2], abs=0.5)
    assert result.volume == pytest.approx(volume, rel=0.05)


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
