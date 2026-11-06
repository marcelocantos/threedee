# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Dudeney's four-piece dissection of an equilateral triangle into a square.

Citation
--------
Henry Ernest Dudeney, *The Canterbury Puzzles* (1907), puzzle 26,
"The Haberdasher's Puzzle", solution. Project Gutenberg eBook 27635:
https://www.gutenberg.org/files/27635/27635-h/27635-h.htm

    Bisect AB in D and BC in E; produce the line AE to F making EF equal
    to EB; bisect AF in G and describe the arc AHF; produce EB to H, and
    EH is the length of the side of the required square; from E with
    distance EH, describe the arc HJ, and make JK equal to BE; now, from
    the points D and K drop perpendiculars on EJ at L and M.

The four pieces are the quadrilaterals ADLJ, BDLE and ECKM and the
triangle JMK (the lettering of that solution). Dudeney also describes
the brass-hinged chain that swings from the triangle to the square
without turning a piece over. The chain used here is ADLJ —D— BDLE
—E— ECKM —K— JMK. Each hinge swings clockwise by the same angle.
A clockwise swing is the one whose intermediate poses stay
interior-disjoint; the opposite swing collides. Both endpoints are
proved in exact arithmetic. The open path is checked numerically.

Side length is 1. Dudeney's figure is the same construction at any
scale; dividing his side-2 diagram by 2 does not change the cuts.
"""

from __future__ import annotations

import json
from pathlib import Path

import sympy as sp

# Nested radical that appears in the cut. h = sqrt(4*sqrt(3) - 3).
H_RAD = sp.sqrt(4 * sp.sqrt(3) - 3)

PIECE_ORDER = ("red", "blue", "orange", "green")
# Clockwise. +1 collides on the way; -1 does not.
SWING = -1
HINGES = ("D", "E", "K")

COLORS = {
    "red": "#e10600",
    "blue": "#0047ff",
    "orange": "#ff9f1a",
    "green": "#00b140",
}

# Print parameters (millimetres). Kerf is an inset of every tile edge,
# so a tile lies strictly inside either pocket. Containment, not a
# zero gap, is the fit condition.
SIDE_MM = 80
KERF_MM = 0.35
TILE_MM = 6
POCKET_DEPTH_MM = 4
FLOOR_MM = 2.5
WALL_MM = 7
POCKET_GAP_MM = 14

CITATION = (
    "Henry Ernest Dudeney, The Canterbury Puzzles (1907), puzzle 26, "
    "solution. https://www.gutenberg.org/files/27635/27635-h/27635-h.htm"
)


def _pt(x, y) -> sp.Point:
    return sp.Point(sp.simplify(x), sp.simplify(y))


def _unit(dx, dy):
    length = sp.sqrt(sp.simplify(dx * dx + dy * dy))
    return sp.simplify(dx / length), sp.simplify(dy / length), length


def _foot(p: sp.Point, a: sp.Point, b: sp.Point) -> sp.Point:
    vx, vy = b.x - a.x, b.y - a.y
    t = ((p.x - a.x) * vx + (p.y - a.y) * vy) / (vx * vx + vy * vy)
    t = sp.simplify(t)
    return _pt(a.x + t * vx, a.y + t * vy)


def _cross(a, b, c):
    return sp.simplify((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x))


def _on_circle_line(center: sp.Point, radius, origin: sp.Point, direction) -> list[tuple[sp.Expr, sp.Point]]:
    """Intersections of a circle with the line origin + t * direction."""
    dx, dy = direction
    # |origin + t d - center|^2 = radius^2
    ox, oy = origin.x - center.x, origin.y - center.y
    qa = sp.simplify(dx * dx + dy * dy)
    qb = sp.simplify(2 * (ox * dx + oy * dy))
    qc = sp.simplify(ox * ox + oy * oy - radius * radius)
    disc = sp.simplify(qb * qb - 4 * qa * qc)
    root = sp.sqrt(disc)
    out = []
    for t in (sp.simplify((-qb - root) / (2 * qa)), sp.simplify((-qb + root) / (2 * qa))):
        out.append((t, _pt(origin.x + t * dx, origin.y + t * dy)))
    return out


def construct(side: sp.Expr | int = 1) -> dict:
    """Run Dudeney's compass construction. `side` is the triangle's edge."""
    side = sp.sympify(side)
    sq3 = sp.sqrt(3)
    a = _pt(0, 0)
    b = _pt(side, 0)
    c = _pt(side / 2, side * sq3 / 2)
    d = _pt(side / 2, 0)  # midpoint of AB
    e = _pt((b.x + c.x) / 2, (b.y + c.y) / 2)  # midpoint of BC

    eb = sp.simplify(e.distance(b))
    ux, uy, _ = _unit(e.x - a.x, e.y - a.y)
    f = _pt(e.x + ux * eb, e.y + uy * eb)  # AE produced so EF = EB
    g = _pt((a.x + f.x) / 2, (a.y + f.y) / 2)
    radius = sp.simplify(g.distance(a))

    # Arc AHF, centre G. H is EB produced beyond B.
    hits = _on_circle_line(g, radius, e, (b.x - e.x, b.y - e.y))
    beyond = [hit for hit in hits if sp.simplify(hit[0] - 1) > 0]
    if len(beyond) != 1:
        raise RuntimeError(f"expected one point H beyond B, got {len(beyond)}")
    h_pt = beyond[0][1]
    eh = sp.simplify(h_pt.distance(e))
    # Triangle area is side**2 * sqrt(3)/4, so the equal square has side
    # side * 3**(1/4) / 2.
    square_side = sp.simplify(side * sp.sqrt(sp.sqrt(3)) / 2)
    if sp.simplify(eh - square_side) != 0:
        raise RuntimeError("EH is not the side of the equal-area square")

    # Arc centre E, radius EH, meeting AC. J is the hit on segment AC.
    ac_hits = _on_circle_line(e, eh, a, (c.x - a.x, c.y - a.y))
    on_ac = []
    for t, p in ac_hits:
        # Param t is along A + t*(C-A); C is at t=1 because C-A is the direction vector.
        if sp.simplify(t) >= 0 and sp.simplify(t) <= 1:
            on_ac.append(p)
    if len(on_ac) != 1:
        raise RuntimeError(f"expected one J on AC, got {len(on_ac)}")
    j = on_ac[0]

    kx, ky, ac_len = _unit(c.x - a.x, c.y - a.y)
    if sp.simplify(ac_len - side) != 0:
        raise RuntimeError("unit step along AC should be the side")
    k = _pt(j.x + kx * eb, j.y + ky * eb)  # JK = BE, toward C
    # K stays on AC: its parameter is between 0 and 1.
    k_t = sp.simplify(k.x / c.x)  # C.x != 0, and K is on the ray AC
    if not (sp.simplify(k_t) >= 0 and sp.simplify(k_t) <= 1):
        raise RuntimeError("K fell off side AC")

    l_pt = _foot(d, e, j)
    m_pt = _foot(k, e, j)

    points = {
        "A": a, "B": b, "C": c, "D": d, "E": e, "F": f, "G": g,
        "H": h_pt, "J": j, "K": k, "L": l_pt, "M": m_pt,
    }
    # CCW polygons. BDLE comes out clockwise from the letter order.
    pieces = {
        "red": ("A", "D", "L", "J"),       # ADLJ
        "blue": ("B", "E", "L", "D"),      # BDLE, reversed to CCW
        "orange": ("E", "C", "K", "M"),    # ECKM
        "green": ("J", "M", "K"),          # JMK
    }
    return {
        "side": side,
        "square_side": square_side,
        "points": points,
        "pieces": pieces,
        "triangle": ("A", "B", "C"),
    }


def _xy(p: sp.Point) -> tuple[sp.Expr, sp.Expr]:
    return p.x, p.y


def rot(pivot: sp.Point, phi, x: sp.Point) -> sp.Point:
    c, s = sp.cos(phi), sp.sin(phi)
    dx, dy = x.x - pivot.x, x.y - pivot.y
    return _pt(pivot.x + c * dx - s * dy, pivot.y + s * dx + c * dy)


def pose_vertices(model: dict, phi) -> dict[str, list[sp.Point]]:
    """Place each piece at hinge angle `phi` (0 triangle, -pi square)."""
    pts = model["points"]
    pieces = model["pieces"]
    d, e, k = pts["D"], pts["E"], pts["K"]

    def apply_blue(x):
        return rot(d, phi, x)

    e_img = apply_blue(e)

    def apply_orange(x):
        return rot(e_img, phi, apply_blue(x))

    k_img = apply_orange(k)

    def apply_green(x):
        return rot(k_img, phi, apply_orange(x))

    fns = {
        "red": lambda x: x,
        "blue": apply_blue,
        "orange": apply_orange,
        "green": apply_green,
    }
    out = {}
    for name, verts in pieces.items():
        out[name] = [fns[name](pts[v]) for v in verts]
    return out


def polygon_area(verts: list) -> sp.Expr:
    acc = 0
    n = len(verts)
    for i in range(n):
        p, q = verts[i], verts[(i + 1) % n]
        acc += p.x * q.y - q.x * p.y
    return sp.simplify(sp.Abs(acc) / 2)


def _turn_sign(verts: list) -> sp.Expr:
    """+1 if CCW, -1 if CW. Raises if a piece is not strictly convex."""
    sign = None
    n = len(verts)
    for i in range(n):
        cr = _cross(verts[i], verts[(i + 1) % n], verts[(i + 2) % n])
        s = sp.sign(cr)
        if s == 0:
            raise RuntimeError("piece is not strictly convex")
        if sign is None:
            sign = s
        elif s != sign:
            raise RuntimeError("piece is not convex")
    return sign


def _strictly_inside(poly: list, p, ) -> bool:
    n = len(poly)
    for i in range(n):
        if _cross(poly[i], poly[(i + 1) % n], p) <= 0:
            return False
    return True


def _proper_crossing(a, b, c, d) -> bool:
    c1 = _cross(a, b, c)
    c2 = _cross(a, b, d)
    c3 = _cross(c, d, a)
    c4 = _cross(c, d, b)
    if c1 == 0 or c2 == 0 or c3 == 0 or c4 == 0:
        return False
    return sp.sign(c1) != sp.sign(c2) and sp.sign(c3) != sp.sign(c4)


def interior_disjoint(polys: list[list]) -> bool:
    """Exact predicate for strictly convex polygons. Shared boundary is allowed."""
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            a, b = polys[i], polys[j]
            for p in a:
                if _strictly_inside(b, p):
                    return False
            for p in b:
                if _strictly_inside(a, p):
                    return False
            for i1 in range(len(a)):
                for j1 in range(len(b)):
                    if _proper_crossing(a[i1], a[(i1 + 1) % len(a)], b[j1], b[(j1 + 1) % len(b)]):
                        return False
    return True


def _inside_convex(container: list, polys: list[list]) -> bool:
    for poly in polys:
        for p in poly:
            n = len(container)
            for i in range(n):
                if _cross(container[i], container[(i + 1) % n], p) < 0:
                    return False
    return True


def chirality(src: list, dst: list) -> sp.Expr:
    """Sign of the linear part sending src's first corner frame to dst's.

    Vertex i of src corresponds to vertex i of dst. +1 is a direct isometry
    (rotation/translation). -1 is a flip.
    """
    if len(src) < 3 or len(src) != len(dst):
        raise RuntimeError("chirality needs matching polygons")
    sx, sy = src[1].x - src[0].x, src[1].y - src[0].y
    tx, ty = src[2].x - src[0].x, src[2].y - src[0].y
    ux, uy = dst[1].x - dst[0].x, dst[1].y - dst[0].y
    vx, vy = dst[2].x - dst[0].x, dst[2].y - dst[0].y
    # [u v] = [s t] * M, det M = det(u v) / det(s t)
    det_src = sp.simplify(sx * ty - sy * tx)
    det_dst = sp.simplify(ux * vy - uy * vx)
    if det_src == 0:
        raise RuntimeError("degenerate source corner")
    return sp.sign(det_dst / det_src)


def convex_hull(points: list[sp.Point]) -> list[sp.Point]:
    uniq: list[sp.Point] = []
    seen = set()
    for p in points:
        key = (sp.simplify(p.x), sp.simplify(p.y))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(_pt(key[0], key[1]))
    uniq.sort(key=lambda p: (p.x, p.y))

    def build(seq):
        chain: list[sp.Point] = []
        for p in seq:
            while len(chain) >= 2 and _cross(chain[-2], chain[-1], p) <= 0:
                chain.pop()
            chain.append(p)
        return chain

    lower = build(uniq)
    upper = build(reversed(uniq))
    return lower[:-1] + upper[:-1]


def _is_square(poly: list[sp.Point]) -> bool:
    if len(poly) != 4:
        return False
    sides = []
    for i in range(4):
        a, b = poly[i], poly[(i + 1) % 4]
        sides.append(sp.simplify(a.distance(b) ** 2))
    if any(sp.simplify(s - sides[0]) != 0 for s in sides):
        return False
    for i in range(4):
        a, b, c = poly[i], poly[(i + 1) % 4], poly[(i + 2) % 4]
        dot = sp.simplify((b.x - a.x) * (c.x - b.x) + (b.y - a.y) * (c.y - b.y))
        if dot != 0:
            return False
    return True


def prove(model: dict | None = None) -> dict:
    """Exact endpoint proof. Returns the posed square vertices and the hull."""
    model = model or construct(1)
    tri = [model["points"][v] for v in model["triangle"]]
    tri_area = polygon_area(tri)
    placed0 = pose_vertices(model, 0)
    polys0 = [placed0[name] for name in PIECE_ORDER]
    for name in PIECE_ORDER:
        if _turn_sign(placed0[name]) != 1:
            raise RuntimeError(f"{name} is not CCW")
    areas = {name: polygon_area(placed0[name]) for name in PIECE_ORDER}
    if sp.simplify(sum(areas.values()) - tri_area) != 0:
        raise RuntimeError("piece areas do not sum to the triangle")
    if not _inside_convex(tri, polys0):
        raise RuntimeError("a triangle-pose vertex lies outside the triangle")
    if not interior_disjoint(polys0):
        raise RuntimeError("triangle pose is not interior-disjoint")

    phi = SWING * sp.pi
    placed1 = pose_vertices(model, phi)
    polys1 = [placed1[name] for name in PIECE_ORDER]
    for name in PIECE_ORDER:
        if chirality(placed0[name], placed1[name]) != 1:
            raise RuntimeError(f"{name} flipped on the way to the square")
        if sp.simplify(polygon_area(placed1[name]) - areas[name]) != 0:
            raise RuntimeError(f"{name} changed area")
    hull = convex_hull([p for poly in polys1 for p in poly])
    if not _is_square(hull):
        raise RuntimeError("square pose hull is not a square")
    square_area = polygon_area(hull)
    if sp.simplify(square_area - tri_area) != 0:
        raise RuntimeError("square area differs from the triangle")
    if not _inside_convex(hull, polys1):
        raise RuntimeError("a square-pose vertex lies outside the square")
    if not interior_disjoint(polys1):
        raise RuntimeError("square pose is not interior-disjoint")
    # Deliberate overlap must fail, or the predicate is not biting.
    shifted = [sp.Point(p.x + model["side"] / 20, p.y + model["side"] / 20) for p in placed0["green"]]
    if interior_disjoint([placed0["red"], placed0["blue"], placed0["orange"], shifted]):
        raise RuntimeError("overlapping fixture did not fail")
    flipped = [sp.Point(p.x, -p.y) for p in placed1["green"]]
    if chirality(placed0["green"], flipped) != -1:
        raise RuntimeError("flipped fixture did not fail")
    return {
        "model": model,
        "areas": areas,
        "triangle_area": tri_area,
        "triangle_pose": placed0,
        "square_pose": placed1,
        "square": hull,
    }


def _expr(e) -> str:
    return str(sp.simplify(e))


def _nonnegative(e: sp.Expr) -> bool:
    real = complex(sp.N(e)).real
    return real >= -1e-10


def _fmt(e: sp.Expr) -> str:
    """Print an exact real expression with non-negative radicands.

    Sympy orders ``4*sqrt(3) - 3`` as ``-3 + 4*sqrt(3)``, so ``str`` on a
    square root shows a negative radicand. The value is unchanged; only
    the term order inside each radical is rewritten.
    """
    e = sp.simplify(e)
    if e.is_Integer:
        return str(int(e))
    if e.is_Rational:
        return f"{e.p}/{e.q}"
    if e.func is sp.Pow and e.exp == sp.Rational(1, 2):
        return f"sqrt({_fmt(e.base)})"
    if e.func is sp.Add:
        pos = [t for t in e.args if _nonnegative(t)]
        neg = [t for t in e.args if not _nonnegative(t)]
        pos.sort(key=lambda t: -abs(complex(sp.N(t)).real))
        neg.sort(key=lambda t: -abs(complex(sp.N(t)).real))
        parts: list[str] = []
        for term in pos:
            parts.append(_fmt(term) if not parts else f" + {_fmt(term)}")
        for term in neg:
            shown = _fmt(sp.simplify(-term))
            parts.append(shown if not parts else f" - {shown}")
            if parts and parts[-1] == shown and len(parts) == 1:
                parts[-1] = f"-{shown}"
        return "".join(parts)
    if e.func is sp.Mul:
        sign = 1
        factors: list[sp.Expr] = []
        for factor in e.args:
            if factor.is_Number and factor < 0:
                sign *= -1
                factor = sp.simplify(-factor)
            if factor != 1:
                factors.append(factor)
        rationals = [factor for factor in factors if factor.is_Rational]
        others = [factor for factor in factors if not factor.is_Rational]
        bits: list[str] = []
        if rationals:
            coeff = sp.Mul(*rationals)
            if coeff != 1:
                bits.append(_fmt(coeff))
        for factor in others:
            bits.append(f"({_fmt(factor)})" if factor.func is sp.Add else _fmt(factor))
        body = "*".join(bits) if bits else "1"
        return f"-{body}" if sign < 0 else body
    return str(e)


def _share_radical(expr: sp.Expr) -> sp.Expr:
    """Write sqrt(12*sqrt(3)-9) as sqrt(3)*sqrt(4*sqrt(3)-3) and collect."""
    shared = sp.sqrt(4 * sp.sqrt(3) - 3)
    wider = sp.sqrt(12 * sp.sqrt(3) - 9)
    rewritten = expr.xreplace({wider: sp.sqrt(3) * shared})
    return sp.collect(sp.expand(rewritten), shared)


def canonical_area(expr: sp.Expr) -> str:
    """Closed form whose ``sympify`` equals ``expr`` and whose radicands lead non-negative."""
    e = sp.simplify(expr)
    num, den = sp.fraction(sp.together(_share_radical(e)))
    num, den = sp.simplify(num), sp.simplify(den)
    body = _fmt(num)
    if den == 1:
        text = body
    else:
        if num.func is sp.Add or (isinstance(body, str) and body.startswith("-")):
            body = f"({body})"
        text = f"{body}/{_fmt(den)}"
    if sp.simplify(sp.sympify(text) - e) != 0:
        raise RuntimeError(f"canonical area does not round-trip: {text}")
    if "sqrt(-" in text.replace(" ", ""):
        raise RuntimeError(f"negative radicand in canonical area: {text}")
    return text


def _num(e) -> float:
    return float(e)


def _point_record(p: sp.Point) -> dict:
    return {"exact": [_expr(p.x), _expr(p.y)], "xy": [_num(p.x), _num(p.y)]}


def cabinet_document(proof: dict | None = None) -> dict:
    proof = proof or prove()
    model = proof["model"]
    pieces = []
    for name in PIECE_ORDER:
        tri = proof["triangle_pose"][name]
        sq = proof["square_pose"][name]
        pieces.append({
            "id": name,
            "color": COLORS[name],
            "letters": "".join(model["pieces"][name]),
            "vertices": list(model["pieces"][name]),
            "triangle": [_point_record(p)["xy"] for p in tri],
            "square": [_point_record(p)["xy"] for p in sq],
            "area": {"exact": canonical_area(proof["areas"][name]), "float": _num(proof["areas"][name])},
        })
    return {
        "schema": "dissection-cabinet/1",
        "dissections": [
            {
                "id": "haberdasher",
                "title": "Haberdasher",
                "citation": CITATION,
                "triangle_side": 1,
                "swing": SWING,
                "hinges": list(HINGES),
                "chain": list(PIECE_ORDER),
                "triangle_area": {
                    "exact": _expr(proof["triangle_area"]),
                    "float": _num(proof["triangle_area"]),
                },
                "square_side": {
                    "exact": _expr(model["square_side"]),
                    "float": _num(model["square_side"]),
                },
                "points": {name: _point_record(p) for name, p in model["points"].items()},
                "triangle": list(model["triangle"]),
                "square": [_point_record(p)["xy"] for p in proof["square"]],
                "pieces": pieces,
                "print": {
                    "side_mm": SIDE_MM,
                    "kerf_mm": KERF_MM,
                    "tile_mm": TILE_MM,
                    "pocket_depth_mm": POCKET_DEPTH_MM,
                    "floor_mm": FLOOR_MM,
                    "wall_mm": WALL_MM,
                    "pocket_gap_mm": POCKET_GAP_MM,
                },
            }
        ],
    }


def write_json(path: Path, doc: dict | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc or cabinet_document(), indent=2) + "\n")


def inset_polygon(poly: list[tuple[float, float]], distance: float) -> list[tuple[float, float]]:
    """Mitered inward offset of a CCW convex polygon."""
    if distance < 0:
        raise ValueError("distance must be non-negative")
    n = len(poly)
    lines = []
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            raise ValueError("degenerate edge")
        nx, ny = -dy / length, dx / length  # left of the edge: inward for CCW
        lines.append((x0 + nx * distance, y0 + ny * distance, dx, dy))

    def meet(i, j):
        x0, y0, dx0, dy0 = lines[i]
        x1, y1, dx1, dy1 = lines[j]
        den = dx0 * dy1 - dy0 * dx1
        if abs(den) < 1e-15:
            raise ValueError("parallel inset edges")
        t = ((x1 - x0) * dy1 - (y1 - y0) * dx1) / den
        return (x0 + t * dx0, y0 + t * dy0)

    return [meet(i, (i + 1) % n) for i in range(n)]


def signed_distance(container: list[tuple[float, float]], point: tuple[float, float]) -> float:
    """Minimum distance to the boundary, positive when inside a CCW polygon."""
    px, py = point
    best = float("inf")
    n = len(container)
    inside = True
    for i in range(n):
        x0, y0 = container[i]
        x1, y1 = container[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        length = (dx * dx + dy * dy) ** 0.5
        cross = dx * (py - y0) - dy * (px - x0)
        if cross < 0:
            inside = False
        best = min(best, cross / length)
    return best if inside else -abs(best)


def tiles_fit(dissection: dict, kerf_mm: float, side_mm: float) -> bool:
    """Each kerfed tile footprint lies inside both pocket polygons."""
    scale = side_mm  # model side is 1
    triangle = [(scale * dissection["points"][name]["xy"][0], scale * dissection["points"][name]["xy"][1])
                for name in dissection["triangle"]]
    square = [(scale * x, scale * y) for x, y in dissection["square"]]
    for piece in dissection["pieces"]:
        for key, pocket in (("triangle", triangle), ("square", square)):
            raw = [(scale * x, scale * y) for x, y in piece[key]]
            tile = inset_polygon(raw, kerf_mm)
            for vertex in tile:
                if signed_distance(pocket, vertex) < kerf_mm * 0.98:
                    return False
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="append", default=[], help="Write cabinet JSON to this path (repeatable)")
    args = parser.parse_args()
    proof = prove()
    doc = cabinet_document(proof)
    print(
        f"haberdasher proved: triangle area {proof['triangle_area']} "
        f"= square, four pieces, both poses interior-disjoint, no flips"
    )
    for path in args.write:
        write_json(Path(path), doc)
        print(f"wrote {path}")
