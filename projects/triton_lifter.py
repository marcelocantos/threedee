# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Triton lifter — bevel gear mechanism with hex socket interfaces.

Uses py_gearworks for proper involute bevel gear generation.
"""

from build123d import *
from math import radians, sqrt
from py_gearworks import BevelGear

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

# --- Gear 1: hex socket ---
with BuildPart() as gear1:
    add(gear_solid)
    # Mounting cylinder
    Pos(0, 0, -2.7) * Cylinder(radius=14.95 / 2, height=3, align=Align.MIN)
    # Hex socket cutout (10mm across flats, hexagonal)
    hex_r = (10 * (2 / sqrt(3)) - 0.2) / 2
    with BuildSketch(Plane.XY.offset(-3)):
        RegularPolygon(radius=hex_r, side_count=6)
    extrude(amount=24, mode=Mode.SUBTRACT)

# --- Gear 2: round bore ---
with BuildPart() as gear2:
    add(gear_solid)
    # Mounting cylinder
    Pos(0, 0, -2.7) * Cylinder(radius=14.95 / 2, height=3, align=Align.MIN)
    # Round bore
    Pos(0, 0, -3) * Cylinder(radius=(10 + 0.4) / 2, height=24, align=Align.MIN, mode=Mode.SUBTRACT)

# Position gear 2 offset from gear 1
result = Compound(children=[
    gear1.part,
    Pos(3.5 * w, 0, 0) * gear2.part,
])

export_stl(result, "triton-lifter.stl")
export_step(result, "triton-lifter.step")
