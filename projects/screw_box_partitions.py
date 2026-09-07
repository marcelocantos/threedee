# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Screw box partitions — trapezoid-shaped dividers with chamfered edges and drain holes."""

from build123d import *

# OpenSCAD's cylinder() sits on the z=0 plane but is centred in x and y;
# build123d centres all three axes by default and a bare Align.MIN shifts all three.
BASE_AT_Z0 = (Align.CENTER, Align.CENTER, Align.MIN)

h = 41
w = 49
r = 0.5

# The original shrinks the trapezoid by the rib radius at each end and shifts it
# right by r, so the rib sits flush with x=0.
hb = h - 2 * r

# Main trapezoid body
body = Pos(r, 0, 0) * extrude(
    Plane.XY * Polygon((0, 0), (hb, 0.5), (hb, w - 0.5), (0, w), align=None),
    amount=1.4,
)

# Rounded edge (rib along the bottom-left, lying along +y)
r2 = 0.7
body += Pos(r2, 0, r2) * Rot(-90, 0, 0) * Cylinder(radius=r2, height=w, align=BASE_AT_Z0)

# Chamfer cuts at the two right-hand corners
c = 5
body -= Pos(h, r, 0) * Rot(0, 0, 45) * Box(c, c, 4)
body -= Pos(h, w - r, 0) * Rot(0, 0, 45) * Box(c, c, 4)

# Recessed area. The original re-binds h inside this block from the outer h (41),
# not from the shrunk hb, so the recess runs 1mm further than the body outline suggests.
inner_h = h - 5
inner_w = w - 4
body -= Pos(2.5, 2, 0.8) * extrude(
    Plane.XY
    * Polygon(
        (0, 0), (inner_h, 0.5), (inner_h, inner_w - 0.5), (0, inner_w), align=None
    ),
    amount=1.4,
)

# Drain holes grid (9x11 at 4mm spacing, centred on the untrimmed h x w rectangle)
for ix in range(-4, 5):
    for iy in range(-5, 6):
        body -= Pos(h / 2 + ix * 4, w / 2 + iy * 4, 0) * Cylinder(
            radius=1.25, height=1, align=BASE_AT_Z0,
        )

result = body

export_stl(result, "screw-box-partitions.stl")
export_step(result, "screw-box-partitions.step")

try:
    from ocp_vscode import show
    show(result)
except ImportError:
    pass
