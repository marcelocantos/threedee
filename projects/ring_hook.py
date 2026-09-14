# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Ring hook — flat profile with top ring, tapered neck, and semicircular base."""

from build123d import *
from math import cos, pi, sin

# Measured from reference (mm). Y increases downward; extruded in Z.
THICKNESS = 2.5

RING_OD = 14
RING_ID = 8
RING_R = RING_OD / 2
RING_R_INNER = RING_ID / 2
RING_CY = RING_R  # ring center y; top flush at y=0

Y_RING_BOTTOM = RING_OD
Y_NECK_END = 28
Y_BASE_CENTER = 32
BASE_R = 13

NECK_HALF_W_TOP = 5.5
NECK_HALF_W_BASE = 6.5

TRI_APEX_Y = 30
TRI_HALF_W = 3

BASE_CUT_HALF_W = 9
BASE_CUT_TOP_Y = 31


def arc_points(cx: float, cy: float, r: float, a0: float, a1: float, n: int = 16, skip_first: bool = False):
    """Sample an arc; angles use y-down coordinates (0 at top of circle)."""
    pts = [
        (cx + r * sin(a), cy - r * cos(a))
        for a in (a0 + (a1 - a0) * i / n for i in range(n + 1))
    ]
    return pts[1:] if skip_first else pts


def chain(*segments):
    """Concatenate point lists, dropping duplicate junctions."""
    out = []
    for seg in segments:
        if out and seg and seg[0] == out[-1]:
            out.extend(seg[1:])
        else:
            out.extend(seg)
    return out


def outer_profile_points():
    """Closed outer silhouette: ring + neck + semicircular base."""
    return chain(
        arc_points(0, RING_CY, RING_R, pi / 2, -pi / 2),
        [(NECK_HALF_W_TOP, Y_RING_BOTTOM + 1), (NECK_HALF_W_BASE, Y_NECK_END), (BASE_R, Y_BASE_CENTER)],
        arc_points(0, Y_BASE_CENTER, BASE_R, 0, pi, n=24, skip_first=True),
        [(-NECK_HALF_W_BASE, Y_NECK_END), (-NECK_HALF_W_TOP, Y_RING_BOTTOM + 1), (0, Y_RING_BOTTOM)],
        arc_points(0, RING_CY, RING_R, -pi / 2, pi / 2, skip_first=True),
    )


def base_cutout_points():
    """D-shaped cutout in the base."""
    return chain(
        [(-BASE_CUT_HALF_W, BASE_CUT_TOP_Y), (BASE_CUT_HALF_W, BASE_CUT_TOP_Y)],
        arc_points(0, BASE_CUT_TOP_Y, BASE_CUT_HALF_W, 0, pi, n=16, skip_first=True),
    )


def extrude_profile(draw):
    with BuildPart() as part:
        with BuildSketch():
            draw()
        extrude(amount=THICKNESS)
    return part.part


outer = extrude_profile(lambda: Polygon(outer_profile_points()))
ring_hole = Pos(0, RING_CY, 0) * extrude_profile(lambda: Circle(RING_R_INNER))
triangle = extrude_profile(
    lambda: Polygon([(0, TRI_APEX_Y), (-TRI_HALF_W, Y_RING_BOTTOM), (TRI_HALF_W, Y_RING_BOTTOM)])
)
base_cutout = extrude_profile(lambda: Polygon(base_cutout_points()))

result = outer - ring_hole - triangle - base_cutout

export_stl(result, "ring-hook.stl")
export_step(result, "ring-hook.step")

try:
    from ocp_vscode import show
    show(result)
except ImportError:
    pass
