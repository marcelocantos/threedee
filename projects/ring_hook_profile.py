# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""2D profile of the ring hook — straight edges and circular arcs only (mm, Y down)."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin

# Photo-calibrated dimensions (mm)
RING_R = 7.0
RING_CY = 7.0
RING_R_IN = 4.0

Y_RING_BOT = 14.0
Y_NECK_END = 31.0
Y_BASE_FLAT = 33.0
Y_BOTTOM = 42.3


def base_radius() -> float:
    return Y_BOTTOM - Y_BASE_FLAT  # 9 mm

NECK_X_TOP = 5.5
NECK_X_END = 5.0

TRI_HALF_TOP = 5.2
TRI_APEX_Y = 31.5

BASE_CUT_TOP = 35.0
BASE_CUT_HALF = 5.0
BASE_CUT_R = 5.0


@dataclass(frozen=True)
class Line:
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True)
class Arc:
    cx: float
    cy: float
    r: float
    a0: float
    a1: float


def arc_pts(arc: Arc, n: int = 32, skip_first: bool = False) -> list[tuple[float, float]]:
    pts = [
        (arc.cx + arc.r * sin(a), arc.cy - arc.r * cos(a))
        for a in (arc.a0 + (arc.a1 - arc.a0) * i / n for i in range(n + 1))
    ]
    return pts[1:] if skip_first else pts


def line_pts(line: Line) -> list[tuple[float, float]]:
    return [(line.x0, line.y0), (line.x1, line.y1)]


def chain(*segments) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for seg in segments:
        s = list(seg)
        if out and s and s[0] == out[-1]:
            out.extend(s[1:])
        else:
            out.extend(s)
    return out


def outer_boundary() -> list[tuple[float, float]]:
    """Outer silhouette: 4 lines + 3 circular arcs."""
    return chain(
        arc_pts(Arc(0, RING_CY, RING_R, 0, pi)),
        line_pts(Line(0, Y_RING_BOT, NECK_X_TOP, Y_RING_BOT + 1.5)),
        line_pts(Line(NECK_X_TOP, Y_RING_BOT + 1.5, NECK_X_END, Y_NECK_END)),
        line_pts(Line(NECK_X_END, Y_NECK_END, base_radius(), Y_BASE_FLAT)),
        arc_pts(Arc(0, Y_BASE_FLAT, base_radius(), pi / 2, 3 * pi / 2), skip_first=True),
        line_pts(Line(-base_radius(), Y_BASE_FLAT, -NECK_X_END, Y_NECK_END)),
        line_pts(Line(-NECK_X_END, Y_NECK_END, -NECK_X_TOP, Y_RING_BOT + 1.5)),
        line_pts(Line(-NECK_X_TOP, Y_RING_BOT + 1.5, 0, Y_RING_BOT)),
        arc_pts(Arc(0, RING_CY, RING_R, pi, 2 * pi), skip_first=True),
    )


def ring_hole() -> list[tuple[float, float]]:
    return arc_pts(Arc(0, RING_CY, RING_R_IN, 0, 2 * pi), n=48)


def neck_triangle() -> list[tuple[float, float]]:
    return [(0, TRI_APEX_Y), (-TRI_HALF_TOP, Y_RING_BOT), (TRI_HALF_TOP, Y_RING_BOT)]


def base_cutout() -> list[tuple[float, float]]:
    return chain(
        [(-BASE_CUT_HALF, BASE_CUT_TOP), (BASE_CUT_HALF, BASE_CUT_TOP)],
        arc_pts(Arc(0, BASE_CUT_TOP, BASE_CUT_R, pi / 2, 3 * pi / 2), skip_first=True),
    )


def profile_loops() -> dict[str, list[tuple[float, float]]]:
    return {
        "outer": outer_boundary(),
        "ring_hole": ring_hole(),
        "triangle": neck_triangle(),
        "base_cutout": base_cutout(),
    }


def profile_elements() -> list[str]:
    """Human-readable boundary inventory."""
    return [
        f"Arc ring outer: centre (0,{RING_CY}) r={RING_R}, top→bottom via right",
        f"Line neck right upper: (0,{Y_RING_BOT})→({NECK_X_TOP},{Y_RING_BOT + 1.5})",
        f"Line neck right: ({NECK_X_TOP},{Y_RING_BOT + 1.5})→({NECK_X_END},{Y_NECK_END})",
        f"Line base flare right: ({NECK_X_END},{Y_NECK_END})→({base_radius()},{Y_BASE_FLAT})",
        f"Arc base outer: centre (0,{Y_BASE_FLAT}) r={base_radius()}, semicircle bottom",
        "(left side mirrored)",
        f"Arc ring hole: centre (0,{RING_CY}) r={RING_R_IN}",
        f"Triangle void: apex (0,{TRI_APEX_Y}), base y={Y_RING_BOT} ±{TRI_HALF_TOP}",
        f"Base slot: line y={BASE_CUT_TOP} ±{BASE_CUT_HALF} + arc r={BASE_CUT_R}",
    ]
