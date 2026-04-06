# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Screw box partitions — trapezoid-shaped dividers with chamfered edges and drain holes."""

from build123d import *

h = 41
w = 49
r = 0.5

with BuildPart() as partition:
    # Main trapezoid body
    pts = [
        (0, 0),
        (h - 2 * r, 0.5),
        (h - 2 * r, w - 0.5),
        (0, w),
    ]
    with BuildSketch():
        Polygon(pts)
    extrude(amount=1.4)

    # Rounded edge (rib along bottom-left)
    r2 = 0.7
    Pos(r2, 0, r2) * Rot(-90, 0, 0) * Cylinder(radius=r2, height=w, align=Align.MIN)

    # Chamfer cuts at top corners
    c = 5
    Pos(h, r, 0) * Rot(0, 0, 45) * Box(c, c, 4, mode=Mode.SUBTRACT)
    Pos(h, w - r, 0) * Rot(0, 0, 45) * Box(c, c, 4, mode=Mode.SUBTRACT)

    # Recessed area
    inner_pts = [
        (0, 0),
        (h - 5, 0.5),
        (h - 5, w - 4 - 0.5),
        (0, w - 4),
    ]
    with BuildSketch(Plane.XY.offset(0.8)):
        Polygon(inner_pts)
    extrude(amount=1.4, mode=Mode.SUBTRACT)

    # Drain holes grid (9x11 at 4mm spacing, centered)
    for ix in range(-4, 5):
        for iy in range(-5, 6):
            Pos(h / 2 + ix * 4, w / 2 + iy * 4, 0) * Cylinder(
                radius=1.25, height=1, align=Align.MIN, mode=Mode.SUBTRACT,
            )

result = partition.part

export_stl(result, "screw-box-partitions.stl")
export_step(result, "screw-box-partitions.step")
