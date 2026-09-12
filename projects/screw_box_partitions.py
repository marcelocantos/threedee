# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Screw box partitions — trapezoid-shaped dividers with chamfered edges and drain holes."""

from build123d import *

h = 41
w = 49
r = 0.5

# Sketch + extrude stay in BuildPart; located solids are algebra so Pos*Rot
# is actually applied (add() of a rotated shape was dropping the rotation).
with BuildPart() as partition:
    pts = [
        (0, 0),
        (h - 2 * r, 0.5),
        (h - 2 * r, w - 0.5),
        (0, w),
    ]
    with BuildSketch():
        Polygon(pts)
    extrude(amount=1.4)

    inner_pts = [
        (0, 0),
        (h - 5, 0.5),
        (h - 5, w - 4 - 0.5),
        (0, w - 4),
    ]
    with BuildSketch(Plane.XY.offset(0.8)):
        Polygon(inner_pts)
    extrude(amount=1.4, mode=Mode.SUBTRACT)

result = partition.part

r2 = 0.7
result = result + Pos(r2, 0, r2) * Rot(-90, 0, 0) * Cylinder(
    radius=r2, height=w, align=Align.MIN,
)

c = 5
result = result - Pos(h, r, 0) * Rot(0, 0, 45) * Box(c, c, 4)
result = result - Pos(h, w - r, 0) * Rot(0, 0, 45) * Box(c, c, 4)

for ix in range(-4, 5):
    for iy in range(-5, 6):
        result = result - Pos(h / 2 + ix * 4, w / 2 + iy * 4, 0) * Cylinder(
            radius=1.25, height=1, align=Align.MIN,
        )

export_stl(result, "screw-box-partitions.stl")
export_step(result, "screw-box-partitions.step")

try:
    from ocp_vscode import show
    show(result)
except ImportError:
    pass
