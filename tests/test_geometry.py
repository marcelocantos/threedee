# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Geometry oracles: each part must be the part, not merely a script that ran.

`make` only checks that the interpreter exited 0, which every one of these
defects passes. These tests check the resulting solid instead.
"""

import pytest

import magnet_tube


def test_magnet_tube_barrier_sits_on_the_tube():
    # OpenSCAD's cylinder() is min-aligned in z, build123d's Cylinder is centred.
    # magnet-tube.scad places the tube at z=0..L and the barrier at z=50, so the
    # barrier must be part of the tube, not a ring floating above its top.
    result = magnet_tube.result
    assert len(result.solids()) == 1, "barrier is detached from the tube"

    bbox = result.bounding_box()
    assert bbox.min.Z == pytest.approx(0)
    assert bbox.max.Z == pytest.approx(magnet_tube.length)

    # The widest point of the part is the barrier's flare.
    assert bbox.max.X == pytest.approx(magnet_tube.flare_r)
    assert bbox.min.X == pytest.approx(-magnet_tube.flare_r)
