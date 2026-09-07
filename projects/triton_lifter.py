# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Triton lifter — bevel gear mechanism with hex socket interfaces.

Uses py_gearworks for proper involute bevel gear generation.
"""

from build123d import *
from math import radians, sqrt
from py_gearworks import BevelGear

# OpenSCAD's cylinder() sits on the z=0 plane but is centred in x and y;
# build123d centres all three axes by default and a bare Align.MIN shifts all three.
BASE_AT_Z0 = (Align.CENTER, Align.CENTER, Align.MIN)

# Parameters from original gears.scad invocation
m = 3 / 2       # module
w = 20 / 2      # tooth width (face width)
b = 0.5 / 2     # bore (original, overridden by socket cutouts)

# Generate bevel gear
gear_def = BevelGear(
    number_of_teeth=20,
    module=m,
    cone_angle=radians(45),
    height=w,
)

gear_solid = gear_def.build_part()

# Mounting cylinder, shared by both gears.
boss = Pos(0, 0, -2.7) * Cylinder(radius=14.95 / 2, height=3, align=BASE_AT_Z0)

# --- Gear 1: hex socket ---
hex_r = (10 * (2 / sqrt(3)) - 0.2) / 2
hex_socket = Pos(0, 0, -3) * extrude(
    Plane.XY * RegularPolygon(radius=hex_r, side_count=6), amount=24
)
gear1 = (Part() + gear_solid + boss) - hex_socket

# --- Gear 2: round bore ---
round_bore = Pos(0, 0, -3) * Cylinder(radius=(10 + 0.4) / 2, height=24, align=BASE_AT_Z0)
gear2 = (Part() + gear_solid + boss) - round_bore

# Position gear 2 offset from gear 1
result = Compound(children=[
    gear1,
    Pos(3.5 * w, 0, 0) * gear2,
])

export_stl(result, "triton-lifter.stl")
export_step(result, "triton-lifter.step")

try:
    from ocp_vscode import show
    show(result)
except ImportError:
    pass
