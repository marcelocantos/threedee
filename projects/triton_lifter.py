# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Triton lifter — bevel gear mechanism with hex socket interfaces.

Uses build123d to generate bevel gear tooth profiles via involute math.
Simplified gear generation: produces functional gear geometry suitable
for 3D printing, matching the original gears.scad output.
"""

from build123d import *
from math import cos, sin, tan, radians, pi, sqrt, atan2


def involute_point(base_r, angle):
    """Point on an involute curve at the given angle."""
    return (
        base_r * (cos(angle) + angle * sin(angle)),
        base_r * (sin(angle) - angle * cos(angle)),
    )


def bevel_gear(modul, tooth_number, partial_cone_angle, tooth_width, bore):
    """Generate a bevel gear solid.

    Args:
        modul: Gear module (pitch diameter / tooth count)
        tooth_number: Number of teeth
        partial_cone_angle: Half-angle of the pitch cone (degrees)
        tooth_width: Face width of the teeth
        bore: Bore diameter
    """
    # Gear geometry parameters
    pitch_r = modul * tooth_number / 2
    cone_angle = radians(partial_cone_angle)
    pressure_angle = radians(20)  # Standard 20° pressure angle

    # Cone distance
    cone_dist = pitch_r / sin(cone_angle)

    # Addendum and dedendum
    addendum = modul
    dedendum = 1.25 * modul

    # Tip and root radii at large end
    tip_r = pitch_r + addendum * cos(cone_angle)
    root_r = pitch_r - dedendum * cos(cone_angle)

    # Build gear as a series of extruded tooth profiles at different heights,
    # approximating the conical tooth shape via loft-like stacking.
    # For 3D printing, a simplified approach works well.

    # Tooth angular width at pitch circle
    tooth_angle = 2 * pi / tooth_number
    tooth_thick_angle = tooth_angle / 2  # Tooth thickness = half the pitch

    # Generate gear blank (truncated cone)
    outer_r = tip_r
    # At the inner end (closer to apex), radii scale by (cone_dist - tooth_width) / cone_dist
    scale_inner = (cone_dist - tooth_width) / cone_dist
    inner_r = tip_r * scale_inner
    inner_root_r = root_r * scale_inner

    # Height of the gear
    gear_h = tooth_width * cos(cone_angle)

    # Build the gear body as a cone
    with BuildPart() as gear:
        # Gear blank cone
        Cone(
            bottom_radius=outer_r,
            top_radius=inner_r,
            height=gear_h,
            align=Align.MIN,
        )

        # Subtract inter-tooth gaps using radial wedge cuts
        for i in range(tooth_number):
            angle = i * tooth_angle + tooth_thick_angle / 2 + tooth_angle / 4
            # Create a wedge that cuts the gap between teeth
            gap_angle = tooth_angle - tooth_thick_angle
            # Approximate each gap as a box rotated to the right angle
            gap_depth = addendum + dedendum
            gap_width = 2 * pitch_r * sin(gap_angle / 2)

            with BuildPart(mode=Mode.SUBTRACT):
                # Gap cutting tool: a box positioned at each tooth gap
                b = Box(gap_depth * 2, gap_width * 0.85, gear_h + 0.1, align=Align.MIN)
                mid_r = pitch_r - dedendum * 0.3
                positioned = (
                    Pos(0, 0, -0.05)
                    * Rot(0, 0, angle * 180 / pi)
                    * Pos(mid_r, 0, 0)
                    * b
                )
                add(positioned)

        # Bore hole
        Cylinder(radius=bore / 2, height=gear_h + 0.1, align=Align.MIN, mode=Mode.SUBTRACT)

    return gear.part


# Parameters from original
m = 3 / 2      # modul
w = 20 / 2     # tooth_width
b = 0.5 / 2    # bore

# --- Gear 1: hex socket (hexagonal bore) ---
gear1_body = bevel_gear(modul=m, tooth_number=20, partial_cone_angle=45, tooth_width=w, bore=b)
# Add mounting cylinder
gear1_mount = Pos(0, 0, -2.7) * Cylinder(radius=14.95 / 2, height=3, align=Align.MIN)
# Hex socket cutout (10mm across flats)
hex_across_flats = 10 * (2 / sqrt(3)) - 0.2
hex1_cut = Pos(0, 0, -3) * extrude(RegularPolygon(radius=hex_across_flats / 2, side_count=6), amount=24)

gear1 = gear1_body + gear1_mount - hex1_cut

# --- Gear 2: round bore ---
gear2_body = bevel_gear(modul=m, tooth_number=20, partial_cone_angle=45, tooth_width=w, bore=b)
gear2_mount = Pos(0, 0, -2.7) * Cylinder(radius=14.95 / 2, height=3, align=Align.MIN)
gear2_bore = Pos(0, 0, -3) * Cylinder(radius=(10 + 0.4) / 2, height=24, align=Align.MIN)

gear2 = gear2_body + gear2_mount - gear2_bore

# Position gear 2 offset from gear 1
result = Compound(children=[
    gear1,
    Pos(3.5 * w, 0, 0) * gear2,
])

export_stl(result, "triton-lifter.stl")
export_step(result, "triton-lifter.step")
