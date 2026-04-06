# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Baby gate latch — parametric latch with countersunk screw holes."""

from build123d import *
from math import sqrt

# Screw hole dimensions
r1 = 4.5 / 2  # shaft radius
r2 = 9 / 2    # countersink radius
width = 10

# Base dimensions
base_thickness = 10
base_length = 40


def countersink_hole(shaft_r, sink_r, depth):
    """Countersunk screw hole from cylinder + cone."""
    bevel_h = sink_r - shaft_r
    shaft = Cylinder(radius=shaft_r, height=depth, align=Align.MIN)
    bevel = Pos(0, 0, depth - bevel_h) * Cone(
        bottom_radius=shaft_r, top_radius=sink_r, height=bevel_h,
        align=Align.MIN,
    )
    return shaft + bevel


def baby_gate_latch(span):
    margin = 2
    span = span + margin

    # Arrow/stem dimensions
    arrowhead_width = 8
    arrowhead_length = 11.5
    tip = 0.5
    arrow_bevel = 1
    thickness = 3
    inner = span
    outer = span + arrowhead_length

    # --- Base ---
    base = Box(base_thickness, base_length, width, align=(Align.MIN, Align.MIN, Align.MIN))

    # Screw holes at positions 2/7 and 5/7 along the base
    holes = Compound(children=[
        Pos(0, 2 + i * base_length / 7, width / 2) * Rot(0, 90, 0) * countersink_hole(r1, r2, base_thickness)
        for i in [2, 5]
    ])
    base = base - holes

    # --- Stem and arrow ---
    stem_profile = Polygon([
        (0, 0),
        (outer, 0),
        (outer, tip),
        (outer - arrow_bevel, tip + arrow_bevel),
        (inner, arrowhead_width),
        (inner, thickness),
        (0, thickness),
    ])

    with BuildPart() as stem_part:
        with BuildSketch():
            add(stem_profile)
        extrude(amount=width)

    # Clip: intersection with box + end cylinder for rounded tip
    clip_box = Box(
        outer - width / 2, arrowhead_width, base_thickness,
        align=(Align.MIN, Align.MIN, Align.MIN),
    )
    clip_cyl = Pos(outer - width / 2, 0, width / 2) * Rot(-90, 0, 0) * Cylinder(
        radius=width / 2, height=arrowhead_width,
    )
    clip = clip_box + clip_cyl

    stem = stem_part.part & clip

    return base + stem


result = baby_gate_latch(span=86.5)
result2 = Pos(0, 60, 0) * baby_gate_latch(span=100)
final = Compound(children=[result, result2])

export_stl(final, "baby-gate-latch.stl")
export_step(final, "baby-gate-latch.step")

try:
    from ocp_vscode import show
    show(final)
except ImportError:
    pass
