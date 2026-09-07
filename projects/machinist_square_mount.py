# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Machinist square mount — swept body with square slots and screw holes.

The original uses BOSL2's offset_sweep with os_circle for rounded top edges.
In build123d, we extrude and fillet the top edges instead.
"""

from build123d import *

h = 50
fillet_r = 6

# Square dimensions (3 squares with different sizes)
t1 = 9.44
t2 = 9.57
t3 = 11.54

# OpenSCAD's cylinder()/cone() sit on the z=0 plane but are centred in x and y;
# build123d defaults to centring all three axes and a bare Align.MIN shifts all three.
BASE_AT_Z0 = (Align.CENTER, Align.CENTER, Align.MIN)


def square_slot(lh, wh, th, lb, wb, tb, xb, zb, g):
    """A machinist square slot — L-shaped cavity."""
    g2 = 2 * g
    # Vertical part
    vert = Pos(0, 0, zb + g) * Box(th + g2, wh + g2, lh + g2, align=Align.MIN)
    # Horizontal part
    horiz = Pos(xb, 0, 0) * Box(tb + g2, lb + g2, wb + g2, align=Align.MIN)
    return vert + horiz


def squares(g):
    """All three square slots."""
    x0 = 15
    z = 5
    s1 = Pos(x0, 0, z) * square_slot(45.14, 18.8, t1, 71.6, 18.81, 1.96, 3.98, 5.09, g)
    x1 = x0 + 20 + (t1 + t2) / 2
    s2 = Pos(x1, 0, z) * square_slot(69.81, 19.30, t2, 121.31, 18.85, 2.06, 3.57, 4.97, g)
    x2 = x1 + 20 + (t2 + t3) / 2
    s3 = Pos(x2, 0, z) * square_slot(100.43, 25.07, t3, 178.40, 24.06, 1.81, 4.49, 5.55, g)
    return Compound(children=[s1, s2, s3])


with BuildPart() as mount:
    # Main body: rounded rectangle extruded, then top edges filleted
    with BuildSketch():
        RectangleRounded(100, h, fillet_r)
    extrude(amount=35)

    # Fillet top edges for the os_circle(r=6) effect
    top_face = mount.faces().sort_by(Axis.Z)[-1]
    fillet(top_face.edges(), radius=fillet_r)

# Position to match original's translate([50, 25+15, 0])
body = Pos(100 / 2, h / 2 + 15, 0) * mount.part

# Subtract square slots (with 0.3mm gap)
body = body - squares(0.3)

# Subtract screw holes
hole_d = 5
hole_offset_x = 32
hole_spacing = 35

for i in range(2):
    x = hole_offset_x + i * hole_spacing
    body = body - Pos(x, 25 + 15, 0) * Cylinder(radius=hole_d / 2, height=h, align=BASE_AT_Z0)
    body = body - Pos(x, 25 + 15, 5) * Cylinder(radius=6, height=h, align=BASE_AT_Z0)

result = body

export_stl(result, "machinist-square-mount.stl")
export_step(result, "machinist-square-mount.step")

try:
    from ocp_vscode import show
    show(result)
except ImportError:
    pass
