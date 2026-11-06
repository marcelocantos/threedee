# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Dissection cabinet: exact pieces, a rigid-motion path, and both arrangements.

Haberdasher's hinged proof stays in ``projects/haberdasher``. The three
dissections added here are rational. Overlap is decided by triangulating
each piece and applying the convex interior test to triangles from
different pieces, in exact rational arithmetic. A half-turn is allowed
only when the disk it sweeps misses every other piece, which makes every
intermediate angle disjoint, not only the samples.

Perigal is not a hinge. Two quadrilaterals turn by a half-turn in a clear
disk; the other pieces translate.
"""

from __future__ import annotations

import json
import sys
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
HABERDASHER = HERE.parent / "haberdasher"
sys.path.insert(0, str(HABERDASHER))

import geometry  # noqa: E402

PRINT = {
    "kerf_mm": 0.35,
    "tile_mm": 6.0,
    "pocket_depth_mm": 4.0,
    "floor_mm": 2.5,
    "wall_mm": 7.0,
    "pocket_gap_mm": 14.0,
}

PERIGAL_CITE = (
    "Henry Perigal, “On geometric dissections and transformations”, "
    "Messenger of Mathematics 2 (1873), pp. 103–106. Cuts through the centre "
    "of the square on the longer leg run parallel and perpendicular to the "
    "hypotenuse; the square on the shorter leg translates to the centre of "
    "the square on the hypotenuse. Exposition: Bill Casselman, “On the "
    "dissecting table”, Plus Magazine issue 16 (2001), "
    "https://plus.maths.org/content/dissecting-table. "
    "Two quadrilaterals turn by a half-turn and the others translate. "
    "This is a rigid-motion path, not a hinge."
)

GREEK_CITE = (
    "Henry Ernest Dudeney, Amusements in Mathematics (1917), Greek Cross "
    "Puzzles. The side of the square is the distance from an outer corner "
    "of one arm to an outer corner of the next, and the square stays at "
    "that angle while it slides. Gutenberg eBook 16713, "
    "https://www.gutenberg.org/files/16713/16713-h/16713-h.htm. "
    "The corner used here is the re-entrant point (1/2, 1/2) and one side "
    "is the vector (2, 1), so the side is sqrt(5). The four pieces are the "
    "intersections of the cross with the lattice of that square; they are "
    "unequal, which this solution allows."
)

RECT_CITE = (
    "Henry Ernest Dudeney, Amusements in Mathematics (1917), solution 153, "
    "“A Cutting-Out Puzzle”: if the length-to-breadth ratio is greater than "
    "1 and at most 4, and the rectangle is not an n-by-n tiling of the "
    "square, three pieces suffice. Gutenberg eBook 16713, "
    "https://www.gutenberg.org/files/16713/16713-h/16713-h.htm. "
    "The 9 by 4 rectangle has ratio 9/4, which is in that range, and the "
    "square has side 6. This is the parallel-cut case of that solution: "
    "one cut at x = 6 and one cut of the remaining 3 by 4 rectangle at y = 2."
)


def _f(n, d=1):
    return F(n, d)


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _area(ring) -> F:
    acc = F(0)
    for i in range(len(ring)):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % len(ring)]
        acc += F(x0) * F(y1) - F(x1) * F(y0)
    return acc / 2


def _blocks(tri, p) -> bool:
    return all(_cross(tri[i], tri[(i + 1) % 3], p) >= 0 for i in range(3))


def _strict(poly, p) -> bool:
    return all(_cross(poly[i], poly[(i + 1) % len(poly)], p) > 0 for i in range(len(poly)))


def _proper(a, b, c, d) -> bool:
    c1, c2 = _cross(a, b, c), _cross(a, b, d)
    c3, c4 = _cross(c, d, a), _cross(c, d, b)
    if 0 in (c1, c2, c3, c4):
        return False
    return (c1 > 0) != (c2 > 0) and (c3 > 0) != (c4 > 0)


def _triangulate(ring):
    poly = list(ring)
    tris = []
    guard = 0
    while len(poly) > 3:
        guard += 1
        if guard > 80:
            raise RuntimeError("ear clip stuck")
        n = len(poly)
        clipped = False
        for i in range(n):
            a, b, c = poly[(i - 1) % n], poly[i], poly[(i + 1) % n]
            turn = _cross(a, b, c)
            if turn < 0:
                continue
            if turn == 0:
                del poly[i]
                clipped = True
                break
            if any(_blocks((a, b, c), p) for p in poly if p not in (a, b, c)):
                continue
            tris.append((a, b, c))
            del poly[i]
            clipped = True
            break
        if not clipped:
            raise RuntimeError(f"no ear in {poly}")
    if len(poly) == 3 and _cross(*poly) != 0:
        tris.append(tuple(poly))
    return tris


def _overlaps(rings) -> bool:
    groups = [_triangulate(ring) for ring in rings]
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            for tri in groups[i]:
                for other in groups[j]:
                    if any(_strict(other, p) for p in tri) or any(_strict(tri, p) for p in other):
                        return True
                    for a in range(3):
                        for b in range(3):
                            if _proper(tri[a], tri[(a + 1) % 3], other[b], other[(b + 1) % 3]):
                                return True
    return False


def _on_segment(a, b, p) -> bool:
    if _cross(a, b, p) != 0:
        return False
    dot = (p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])
    if dot < 0:
        return False
    length2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
    return dot <= length2


def _covers(outline, ring) -> bool:
    """Boundary counts as inside. The outline may be non-convex."""
    n = len(outline)
    for point in ring:
        if any(_on_segment(outline[i], outline[(i + 1) % n], point) for i in range(n)):
            continue
        inside = False
        for i in range(n):
            x0, y0 = outline[i]
            x1, y1 = outline[(i + 1) % n]
            if (y0 > point[1]) != (y1 > point[1]):
                xhit = (x1 - x0) * (point[1] - y0) / (y1 - y0) + x0
                if point[0] < xhit:
                    inside = not inside
        if not inside:
            return False
    return True


def _apply(ring, dx, dy, quarter):
    """Rotate ``quarter`` right angles about the first vertex, then translate."""
    ax, ay = ring[0]
    out = []
    for x, y in ring:
        vx, vy = x - ax, y - ay
        for _ in range(quarter % 4):
            vx, vy = -vy, vx
        out.append((ax + vx + dx, ay + vy + dy))
    return tuple(out)


def _disk_clears(ring, obstacles) -> bool:
    """The closed disk about ring[0] through the other vertices misses ``obstacles``."""
    pivot = ring[0]
    rad2 = max((x - pivot[0]) ** 2 + (y - pivot[1]) ** 2 for x, y in ring)
    for obs in obstacles:
        if not _strict_outside(obs, pivot):
            return False
        for i in range(len(obs)):
            if _dist2(pivot, obs[i], obs[(i + 1) % len(obs)]) <= rad2:
                return False
    return True


def _strict_outside(poly, p) -> bool:
    return any(_cross(poly[i], poly[(i + 1) % len(poly)], p) < 0 for i in range(len(poly)))


def _dist2(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    length2 = vx * vx + vy * vy
    t = ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / length2
    if t < 0:
        t = 0
    elif t > 1:
        t = 1
    qx, qy = a[0] + t * vx, a[1] + t * vy
    return (p[0] - qx) ** 2 + (p[1] - qy) ** 2


def _lerp(a, b, u):
    return tuple((x0 + u * (x1 - x0), y0 + u * (y1 - y0)) for (x0, y0), (x1, y1) in zip(a, b))


def _segment_clear(a, b, turn, obstacles) -> None:
    if turn == 0:
        for k in range(9):
            if _overlaps([_lerp(a, b, _f(k, 8)), *obstacles]):
                raise RuntimeError(f"translation overlaps at {k}/8")
        return
    if turn != 1:
        raise RuntimeError(f"unsupported turn {turn}")
    # A half-turn whose disk misses every obstacle is disjoint at every angle.
    if not _disk_clears(a, obstacles):
        raise RuntimeError("half-turn disk is not clear")
    if _overlaps([b, *obstacles]):
        raise RuntimeError("half-turn lands on another piece")


def _schedule(home, moves):
    """Turn a list of (name, states) into per-piece stop rings.

    ``states`` are (dx, dy, quarter) poses of that piece. Only one piece
    moves in each segment. ``turn`` on a stop is 1 for a half-turn and 0
    for a translation, in units of pi, applied on the way to the next stop.
    """
    state = {name: (0, 0, 0) for name in home}
    frames = [dict(state)]
    movers = []
    for name, path in moves:
        if path[0] != state[name]:
            raise RuntimeError(f"{name} path does not start at its current pose")
        for nxt in path[1:]:
            movers.append((name, state[name][2], nxt[2]))
            state = dict(state)
            state[name] = nxt
            frames.append(state)
    n = len(frames)
    stops = {name: [] for name in home}
    for index, frame in enumerate(frames):
        turn = 0
        if index < n - 1:
            who, q0, q1 = movers[index]
            if q1 != q0:
                if (q1 - q0) % 4 != 2:
                    raise RuntimeError(f"{who} turn is not a half-turn")
                turn = 1
        t = _f(index, n - 1)
        for name in home:
            dx, dy, quarter = frame[name]
            stops[name].append({
                "t": t,
                "ring": _apply(home[name], dx, dy, quarter),
                "turn": turn if index < n - 1 and movers[index][0] == name else 0,
            })
    # Replay every segment against the pieces that are holding still.
    for index, (who, _q0, _q1) in enumerate(movers):
        obstacles = [stops[name][index]["ring"] for name in home if name != who]
        _segment_clear(
            stops[who][index]["ring"],
            stops[who][index + 1]["ring"],
            stops[who][index]["turn"],
            obstacles,
        )
    return stops


def _endpoints(stops, outlines, name):
    for label, outline, which in (
        (outlines[0][0], outlines[0][1], 0),
        (outlines[1][0], outlines[1][1], -1),
    ):
        posed = [stops[piece][which]["ring"] for piece in stops]
        if _overlaps(posed):
            raise RuntimeError(f"{name} overlaps at {label}")
        if not all(_covers(outline, ring) for ring in posed):
            raise RuntimeError(f"{name} leaves {label}")
        if sum(_area(ring) for ring in posed) != _area(outline):
            raise RuntimeError(f"{name} does not fill {label}")
    ids = list(stops)
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"{name} repeats an id")
    shifted = tuple((x + _f(1, 5), y) for x, y in stops[ids[0]][0]["ring"])
    if not _overlaps([shifted, *[stops[piece][0]["ring"] for piece in ids[1:]]]):
        raise RuntimeError(f"{name} overlap fixture did not fail")


def _num_ring(ring):
    return [[float(x), float(y)] for x, y in ring]


def _exact_ring(ring):
    return [[str(x), str(y)] for x, y in ring]


def _publish(spec, stops):
    order = list(stops)
    pieces = []
    for name in order:
        ring0 = stops[name][0]["ring"]
        pieces.append({
            "id": name,
            "color": spec["colors"][name],
            "area": {"exact": str(_area(ring0)), "float": float(_area(ring0))},
            "turn": "pi" if any(stop["turn"] for stop in stops[name]) else "0",
            "start": _num_ring(ring0),
            "end": _num_ring(stops[name][-1]["ring"]),
            "start_exact": _exact_ring(ring0),
            "end_exact": _exact_ring(stops[name][-1]["ring"]),
            "stops": [
                {
                    "t": float(stop["t"]),
                    "turn": "pi" if stop["turn"] else "0",
                    "ring": _num_ring(stop["ring"]),
                }
                for stop in stops[name]
            ],
        })
    return {
        "id": spec["id"],
        "title": spec["title"],
        "citation": spec["citation"],
        "slider": list(spec["slider"]),
        "motion": {"type": "rigid"},
        "area": {"exact": str(_area(spec["outlines"][0][1])), "float": float(_area(spec["outlines"][0][1]))},
        "arrangements": [
            {"id": key, "title": title, "outline": _num_ring(ring)}
            for (key, ring), title in zip(spec["outlines"], spec["slider"])
        ],
        "pieces": pieces,
        "samples": [float(stop["t"]) for stop in stops[order[0]]],
        "print": {"side_mm": spec["side_mm"], **PRINT},
    }


def _perigal_home():
    return {
        "q1": ((0, _f(7, 2)), (2, 2), (_f(7, 2), 4), (0, 4)),
        "q2": ((2, 2), (4, _f(1, 2)), (4, 4), (_f(7, 2), 4)),
        "q3": ((2, 2), (_f(1, 2), 0), (4, 0), (4, _f(1, 2))),
        "q4": ((2, 2), (0, _f(7, 2)), (0, 0), (_f(1, 2), 0)),
        "small": ((4, 0), (7, 0), (7, 3), (4, 3)),
    }


# (dx, dy, quarter-turns). Found by a grid search and checked continuously
# below: translations at every eighth of the segment, half-turns by a
# disk that misses the other pieces.
_PERIGAL_MOVES = [
    ("q3", [(0, 0, 0), (0, -3, 0), (-6, -3, 0), (-6, 5, 0), (1, 5, 0)]),
    ("small", [(0, 0, 0), (3, 0, 0)]),
    ("q4", [(0, 0, 0), (0, -3, 0)]),
    ("q1", [(0, 0, 0), (-2, 0, 0), (-2, 3, 0), (-1, 3, 0), (-1, 4, 0), (0, 4, 0), (0, 5, 0)]),
    ("q2", [(0, 0, 0), (3, 0, 0), (3, 3, 0), (6, 3, 0), (6, 5, 0), (6, 5, 2), (5, 5, 2), (5, 2, 2)]),
    ("small", [(3, 0, 0), (3, -1, 0), (-2, -1, 0), (-2, 2, 0)]),
    ("q1", [(0, 5, 0), (7, 5, 0), (7, -2, 0), (2, -2, 0)]),
    ("q4", [(0, -3, 0), (-2, -3, 0), (-2, -3, 2), (-2, 1, 2)]),
]


def perigal():
    home = _perigal_home()
    outlines = [
        ("legs", ((0, 0), (7, 0), (7, 3), (4, 3), (4, 4), (0, 4))),
        ("hypotenuse", ((4, 0), (7, 4), (3, 7), (0, 3))),
    ]
    stops = _schedule(home, _PERIGAL_MOVES)
    _endpoints(stops, outlines, "perigal")
    return _publish({
        "id": "perigal",
        "title": "Perigal: 3–4–5",
        "citation": PERIGAL_CITE,
        "slider": ["Squares on the legs", "Square on the hypotenuse"],
        "colors": {
            "q1": "#e10600", "q2": "#0047ff", "q3": "#ff9f1a", "q4": "#00b140", "small": "#9b5de5",
        },
        "outlines": outlines,
        "side_mm": 8.0,
    }, stops)


def _shift(ring, dx, dy):
    return tuple((x + dx, y + dy) for x, y in ring)


def greek_cross():
    home = {
        "wide": (
            (_f(1, 2), _f(1, 2)), (_f(-3, 2), _f(-1, 2)), (_f(-1, 2), _f(-1, 2)),
            (_f(-1, 2), _f(-3, 2)), (_f(1, 2), _f(-3, 2)), (_f(1, 2), _f(-1, 2)),
            (1, _f(-1, 2)),
        ),
        "long": (
            (_f(1, 2), _f(1, 2)), (0, _f(3, 2)), (_f(-1, 2), _f(3, 2)),
            (_f(-1, 2), _f(1, 2)), (_f(-3, 2), _f(1, 2)), (_f(-3, 2), _f(-1, 2)),
        ),
        "bar": (
            (_f(1, 2), _f(1, 2)), (1, _f(-1, 2)), (_f(3, 2), _f(-1, 2)), (_f(3, 2), _f(1, 2)),
        ),
        "tip": ((_f(1, 2), _f(3, 2)), (0, _f(3, 2)), (_f(1, 2), _f(1, 2))),
    }
    moves = [
        ("bar", [(0, 0, 0), (0, 2, 0), (-1, 2, 0)]),
        ("wide", [(0, 0, 0), (2, 0, 0), (2, 3, 0), (1, 3, 0)]),
        ("long", [(0, 0, 0), (0, -1, 0), (2, -1, 0), (2, 1, 0)]),
    ]
    outlines = [
        ("cross", (
            (_f(1, 2), _f(3, 2)), (_f(-1, 2), _f(3, 2)), (_f(-1, 2), _f(1, 2)),
            (_f(-3, 2), _f(1, 2)), (_f(-3, 2), _f(-1, 2)), (_f(-1, 2), _f(-1, 2)),
            (_f(-1, 2), _f(-3, 2)), (_f(1, 2), _f(-3, 2)), (_f(1, 2), _f(-1, 2)),
            (_f(3, 2), _f(-1, 2)), (_f(3, 2), _f(1, 2)), (_f(1, 2), _f(1, 2)),
        )),
        ("square", (
            (_f(1, 2), _f(1, 2)), (_f(5, 2), _f(3, 2)), (_f(3, 2), _f(7, 2)), (_f(-1, 2), _f(5, 2)),
        )),
    ]
    stops = _schedule(home, moves)
    _endpoints(stops, outlines, "greek-cross")
    # The square's side is the length of (2, 1).
    side2 = _f(2) ** 2 + _f(1) ** 2
    if _area(outlines[1][1]) != side2 / 2 * 2 and _area(outlines[1][1]) != 5:
        raise RuntimeError("greek-cross square is not area 5")
    return _publish({
        "id": "greek-cross",
        "title": "Greek cross to square",
        "citation": GREEK_CITE,
        "slider": ["Greek cross", "Square"],
        "colors": {"wide": "#e10600", "long": "#0047ff", "bar": "#ff9f1a", "tip": "#00b140"},
        "outlines": outlines,
        "side_mm": 28.0,
    }, stops)


def rectangle_square():
    base = ((0, 0), (6, 0), (6, 4), (0, 4))
    low0 = ((6, 0), (9, 0), (9, 2), (6, 2))
    low_up = ((6, 4), (9, 4), (9, 6), (6, 6))
    low1 = ((0, 4), (3, 4), (3, 6), (0, 6))
    high0 = ((6, 2), (9, 2), (9, 4), (6, 4))
    high_up = ((6, 4), (9, 4), (9, 6), (6, 6))
    high1 = ((3, 4), (6, 4), (6, 6), (3, 6))
    home = {"base": base, "low": low0, "high": high0}
    # Absolute translation offsets of each piece's start ring.
    # high parks to the right first. low then rises in the vacated
    # column and slides left into the square. high follows, above the
    # base, and stops against low. A direct lift of both pieces overlaps.
    moves = [
        ("high", [(0, 0, 0), (3, 0, 0)]),
        ("low", [(0, 0, 0), (0, 4, 0), (-6, 4, 0)]),
        ("high", [(3, 0, 0), (3, 2, 0), (-3, 2, 0)]),
    ]
    outlines = [
        ("rectangle", ((0, 0), (9, 0), (9, 4), (0, 4))),
        ("square", ((0, 0), (6, 0), (6, 6), (0, 6))),
    ]
    # The staged offsets above are the composed translation from the start,
    # which matches low_up = low0+(0,4) and low1 = low0+(-6,4), and the
    # same for high. Check that before scheduling.
    if _shift(low0, 0, 4) != low_up or _shift(low0, -6, 4) != low1:
        raise RuntimeError("low piece offsets drifted")
    if _shift(high0, 0, 2) != high_up or _shift(high0, -3, 2) != high1:
        raise RuntimeError("high piece offsets drifted")
    stops = _schedule(home, moves)
    _endpoints(stops, outlines, "rectangle-square")
    return _publish({
        "id": "rectangle-square",
        "title": "9×4 rectangle to square",
        "citation": RECT_CITE,
        "slider": ["9×4 rectangle", "Square"],
        "colors": {"base": "#e10600", "low": "#0047ff", "high": "#00b140"},
        "outlines": outlines,
        "side_mm": 8.0,
    }, stops)


def _point_in_polygon(poly, x, y, eps=1e-8) -> bool:
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        if abs(dx * (y - y0) - dy * (x - x0)) <= eps * (abs(dx) + abs(dy) + 1):
            dot = (x - x0) * dx + (y - y0) * dy
            if -eps <= dot <= dx * dx + dy * dy + eps:
                return True
    inside = False
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xhit = (x1 - x0) * (y - y0) / (y1 - y0) + x0
            if x < xhit:
                inside = not inside
    return inside


def _edge_distance(poly, x, y) -> float:
    best = float("inf")
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        dx, dy = x1 - x0, y1 - y0
        length2 = dx * dx + dy * dy
        if length2 == 0:
            continue
        t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / length2))
        best = min(best, ((x - (x0 + t * dx)) ** 2 + (y - (y0 + t * dy)) ** 2) ** 0.5)
    return best


def _simple(poly) -> bool:
    n = len(poly)
    if n < 3 or _area([(F(x).limit_denominator(10**6), F(y).limit_denominator(10**6)) for x, y in poly]) <= 0:
        # Float rings from the inset. A positive shoelace in floats is enough
        # here; the exact constructions are already proved CCW.
        acc = 0.0
        for i in range(n):
            acc += poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1]
        if acc / 2 <= 0:
            return False
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        for j in range(i + 1, n):
            if (j + 1) % n == i or (i + 1) % n == j:
                continue
            c, d = poly[j], poly[(j + 1) % n]
            c1 = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            c2 = (b[0] - a[0]) * (d[1] - a[1]) - (b[1] - a[1]) * (d[0] - a[0])
            c3 = (d[0] - c[0]) * (a[1] - c[1]) - (d[1] - c[1]) * (a[0] - c[0])
            c4 = (d[0] - c[0]) * (b[1] - c[1]) - (d[1] - c[1]) * (b[0] - c[0])
            eps = 1e-8
            if abs(c1) <= eps or abs(c2) <= eps or abs(c3) <= eps or abs(c4) <= eps:
                continue
            if (c1 > 0) != (c2 > 0) and (c3 > 0) != (c4 > 0):
                return False
    return True


def _scale(ring, side):
    return [(side * x, side * y) for x, y in ring]


def tiles_fit(dissection: dict, kerf_mm: float, side_mm: float) -> bool:
    """Kerfed tile of every piece lies inside both arrangement outlines.

    Containment is a ray cast, so a reflex pocket is allowed. The
    haberdasher keeps its own convex check.
    """
    outlines = [_scale(item["outline"], side_mm) for item in dissection["arrangements"]]
    for piece in dissection["pieces"]:
        for key, outline in zip(("start", "end"), outlines):
            try:
                tile = geometry.inset_polygon(_scale(piece[key], side_mm), kerf_mm)
            except ValueError:
                return False
            if not _simple(tile):
                return False
            for x, y in tile:
                if not _point_in_polygon(outline, x, y):
                    return False
                if _edge_distance(outline, x, y) < kerf_mm * 0.98:
                    return False
    return True


def haberdasher_document() -> dict:
    return json.loads((HABERDASHER / "pieces.json").read_text())


def build_document() -> dict:
    base = haberdasher_document()
    base["dissections"].extend([perigal(), greek_cross(), rectangle_square()])
    return base


def write_json(path: Path, doc: dict | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc or build_document(), indent=2) + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="append", default=[])
    args = parser.parse_args()
    document = build_document()
    print("cabinet:", ", ".join(item["id"] for item in document["dissections"]))
    for item in document["dissections"]:
        if item["id"] == "haberdasher":
            continue
        fitted = tiles_fit(item, item["print"]["kerf_mm"], item["print"]["side_mm"])
        print(f"  {item['id']}: area {item['area']['exact']}, {len(item['pieces'])} pieces, fit={fitted}")
    for dest in args.write:
        write_json(Path(dest), document)
        print(f"wrote {dest}")
