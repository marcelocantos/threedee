# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Rotary bearing jig — base plate with bearing holds and screw-hole pattern."""

from build123d import *
from math import sqrt

# Bearing dimensions
bearing_id = 4.72
bearing_od = 12.7
bearing_h = 8


def screw_holes(diam, dist, h):
    """Four screw holes at 45/135/225/315 degrees."""
    parts = []
    for a in [1, 3, 5, 7]:
        cone = Cone(
            bottom_radius=(diam + 0.1) / 2, top_radius=0, height=h,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        parts.append(Rot(0, 0, 45 * a) * Pos(-(dist + diam) / 2, 0, 0) * cone)
    result = parts[0]
    for p in parts[1:]:
        result = result + p
    return result


def bearing_holds(center_hole_diam, thickness, adjust):
    """Three bearing pin holders at 120-degree spacing."""
    parts = []
    for a in range(3):
        x = bearing_od / 2 - center_hole_diam / 2 - adjust
        pin = Cylinder(
            radius=(bearing_id + 0.1) / 2, height=bearing_h - 2,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        collar = Cylinder(
            radius=(bearing_id + bearing_od) / 4, height=1,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        parts.append(Rot(0, 0, 120 * a) * Pos(x, 0, thickness) * (pin + collar))
    result = parts[0]
    for p in parts[1:]:
        result = result + p
    return result


def base_plate(
    size, h, corner_radius, center_hole_diam, bearing_adjust,
    screw_hole_1_diam=0, screw_hole_1_dist=0,
    screw_hole_2_diam=0, screw_hole_2_dist=0,
    thickness=1.4, buffer=1,
    crosshairs=False, bearings=False,
):
    t = thickness
    hw = (size + 0.6) / 2 - corner_radius
    radius = sqrt(2) * hw + corner_radius

    # Main plate (3*thickness tall)
    plate = Cylinder(
        radius=radius + buffer, height=3 * t,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    # Recess — rounded rectangle cut from top
    with BuildPart() as recess_part:
        with BuildSketch(Plane.XY.offset(2 * t)):
            RectangleRounded(2 * hw + 2 * corner_radius, 2 * hw + 2 * corner_radius, corner_radius)
        extrude(amount=t + 0.01)

    # Cylindrical cuts at z=t
    cut_outer = Pos(0, 0, t) * Cylinder(
        radius=radius, height=t,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    cut_inner = Pos(0, 0, t) * Cylinder(
        radius=radius - 2 * buffer, height=2 * t,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    result = plate - recess_part.part - cut_outer - cut_inner

    # Screw holes type 1
    if screw_hole_1_diam > 0:
        result = result - screw_holes(screw_hole_1_diam, screw_hole_1_dist, t)

    # Crosshairs
    if crosshairs:
        with BuildPart() as xhair:
            with BuildSketch():
                Circle(radius=10)
                # Keep only two quarter-circles (quadrants 3 and 4)
                for angle in [0, 180]:
                    with Locations([Rot(0, 0, angle) * Pos(11 / 2, 11 / 2, 0)]):
                        Rectangle(11, 11, mode=Mode.SUBTRACT)
            extrude(amount=t / 4)
        result = result - xhair.part

    # Pins (screw holes type 2, protruding)
    if screw_hole_2_diam > 0:
        result = result + Pos(0, 0, t) * Rot(0, 0, -5) * screw_holes(screw_hole_2_diam, screw_hole_2_dist, 1)

    # Bearing holds
    if bearings:
        result = result + bearing_holds(center_hole_diam, t, bearing_adjust)

    return result


result = base_plate(
    size=153,
    h=9,
    corner_radius=5,
    center_hole_diam=120,
    bearing_adjust=0.35,
    screw_hole_2_diam=2,
    screw_hole_2_dist=184.8,
    buffer=2,
    bearings=True,
)

export_stl(result, "rotary-bearing.stl")
export_step(result, "rotary-bearing.step")

try:
    from ocp_vscode import show
    show(result)
except ImportError:
    pass
