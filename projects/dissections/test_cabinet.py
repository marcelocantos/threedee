# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Oracle for the dissection cabinet: exact areas, both arrangements, tray fit."""

import json
import random
import unittest
from fractions import Fraction as F
from pathlib import Path

import cabinet

ROOT = Path(__file__).resolve().parent
JSON_PATH = ROOT / "pieces.json"

CANONICAL = {
    "green": "sqrt(4*sqrt(3) - 3)/32",
    "blue": "(2*sqrt(3) + sqrt(4*sqrt(3) - 3))/32",
    "orange": "(sqrt(3) + sqrt(4*sqrt(3) - 3)*(sqrt(3) - 1))/32",
    "red": "(5*sqrt(3) - sqrt(4*sqrt(3) - 3)*(sqrt(3) + 1))/32",
}


def _ring(pairs):
    return tuple((F(x), F(y)) for x, y in pairs)


def _twice_area(ring):
    return sum(x * v - y * u for (x, y), (u, v) in zip(ring, ring[1:] + ring[:1]))


def _intersection_area(a, b):
    """Clip the subject against the convex clip ring, using exact rationals."""
    if _twice_area(a) == 0 or _twice_area(b) == 0:
        return F(0)
    subject = list(a)
    for (x, y), (u, v) in zip(b, b[1:] + b[:1]):
        if not subject:
            return F(0)
        clipped = []
        previous = subject[-1]
        before = (u - x) * (previous[1] - y) - (v - y) * (previous[0] - x)
        for current in subject:
            after = (u - x) * (current[1] - y) - (v - y) * (current[0] - x)
            if (before < 0) != (after < 0):
                ratio = before / (before - after)
                clipped.append(tuple(p + ratio * (q - p) for p, q in zip(previous, current)))
            if after >= 0:
                clipped.append(current)
            previous, before = current, after
        subject = clipped
    return _twice_area(subject) / 2


def _gift_wrap(points):
    """Walk supporting edges of a small exact point set, starting at the leftmost point."""
    points = set(points)
    if len(points) < 3:
        return list(points)
    first = min(points)
    ring = [first]
    while True:
        x, y = ring[-1]
        rays = [(u - x, v - y) for u, v in points if (u, v) != (x, y)]
        dx, dy = rays[0]
        for u, v in rays[1:]:
            if u * dy - v * dx > 0 or (u * dy == v * dx and u * u + v * v > dx * dx + dy * dy):
                dx, dy = u, v
        next_point = (x + dx, y + dy)
        if next_point == first:
            return ring
        ring.append(next_point)


class CabinetOverlapTests(unittest.TestCase):
    def test_exact_overlap_matches_clipping(self):
        triangle = _ring([(0, 0), (3, 0), (0, 3)])
        square = _ring([(0, 0), (3, 0), (3, 3), (0, 3)])
        tiny = F(1, 10**15)
        cases = [
            ("coincident", triangle, triangle),
            ("coincident squares, different diagonals", square, square[1:] + square[:1]),
            ("partial overlap along the same base", triangle, _ring([(1, 0), (4, 0), (1, 2)])),
            ("shared edge", triangle, _ring([(3, 0), (0, 3), (3, 3)])),
            ("point contact", triangle, _ring([(3, 0), (4, 0), (3, 1)])),
            ("nearly parallel overlap", triangle, _ring([(0, 3 - tiny), (3, 0), (3, 3)])),
            ("nearly parallel gap", triangle, _ring([(0, 3 + tiny), (3, 0), (3, 3)])),
            ("zero edge", _ring([(0, 0), (0, 0), (3, 0), (0, 3)]), triangle),
            ("collinear", _ring([(0, 0), (1, 1), (2, 2)]), square),
            ("empty ring", (), square),
        ]
        rng = random.Random(26931)

        def sample_triangle():
            ring = tuple((F(rng.randrange(-24, 25), 4), F(rng.randrange(-24, 25), 4)) for _ in range(3))
            return ring if _twice_area(ring) >= 0 else ring[::-1]

        cases.extend((i, sample_triangle(), sample_triangle()) for i in range(512))
        self.assertFalse(cabinet._overlaps([]))
        self.assertFalse(cabinet._overlaps([triangle]))
        for name, a, b in cases:
            with self.subTest(name=name, a=a, b=b):
                # Area zero is exact. Even a 10^-15 rational gap or sliver survives.
                expected = _intersection_area(a, b) > 0
                self.assertEqual(cabinet._overlaps([a, b]), expected)
                self.assertEqual(cabinet._overlaps([b, a]), expected)


class CabinetTranslationTests(unittest.TestCase):
    def test_translation_matches_the_exact_swept_area(self):
        square = _ring([(0, 0), (1, 0), (1, 1), (0, 1)])
        thin = F(1, 10**15)
        cases = [
            ("between samples", square, (32, 0), _ring([(2, 0), (3, 0), (3, 1), (2, 1)])),
            ("edge contact", square, (32, 0), _ring([(2, 1), (3, 1), (3, 2), (2, 2)])),
            ("point contact at finish", square, (1, 0), _ring([(2, 1), (3, 1), (3, 2), (2, 2)])),
            ("nearly parallel collision", square, (32, thin), _ring([(2, 1), (3, 1), (3, 2), (2, 2)])),
            ("nearly parallel clearance", square, (32, -thin), _ring([(2, 1), (3, 1), (3, 2), (2, 2)])),
            ("zero motion, coincident", square, (0, 0), square),
            ("zero motion, degenerate obstacle", square, (0, 0), _ring([(0, 0)] * 3)),
            ("zero edge", (square[0], *square), (3, 0), square),
            ("empty moving piece", (), (3, 0), square),
            ("empty obstacle", square, (3, 0), ()),
        ]
        rng = random.Random(8164)
        for i in range(192):
            a, b = (
                _gift_wrap(_ring([(rng.randrange(-8, 9), rng.randrange(-8, 9)) for _ in range(6)]))
                for _ in range(2)
            )
            cases.append((i, a, (F(rng.randrange(-32, 33), 3), F(rng.randrange(-32, 33), 3)), b))
        for name, before, (dx, dy), obstacle in cases:
            with self.subTest(name=name):
                after = [(x + dx, y + dy) for x, y in before]
                swept = _gift_wrap([*before, *after])
                # The reference compares rational areas with zero tolerance.
                if _twice_area(before) > 0 and _intersection_area(swept, obstacle) > 0:
                    with self.assertRaisesRegex(RuntimeError, "translation overlaps"):
                        cabinet._segment_clear(before, after, 0, [obstacle])
                else:
                    cabinet._segment_clear(before, after, 0, [obstacle])

    def test_concave_piece_does_not_fill_its_notch_when_translated(self):
        # A U-shaped piece shifts right by 1 while the square stays in its notch.
        before = _ring([(0, 0), (6, 0), (6, 6), (5, 6), (5, 1), (1, 1), (1, 6), (0, 6)])
        after = [(x + 1, y) for x, y in before]
        obstacle = _ring([(3, 2), (4, 2), (4, 3), (3, 3)])
        cabinet._segment_clear(before, after, 0, [obstacle])


class CabinetKerfTests(unittest.TestCase):
    def test_impossible_inset_cannot_fit_a_large_pocket(self):
        inner = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        pocket = [(-5, -5), (5, -5), (5, 5), (-5, 5)]
        triangle = [(-10, -5), (10, -5), (0, 10)]
        dissection = {
            "arrangements": [{"outline": pocket}, {"outline": pocket}],
            "pieces": [{"start": inner, "end": inner}],
        }
        haberdasher = {
            "triangle": ["A", "B", "C"],
            "points": {name: {"xy": point} for name, point in zip("ABC", triangle)},
            "square": pocket,
            "pieces": [{"triangle": inner, "square": inner}],
        }
        for fit, spec in ((cabinet.tiles_fit, dissection), (cabinet.geometry.tiles_fit, haberdasher)):
            with self.subTest(fit=fit.__module__):
                self.assertTrue(fit(spec, 0.25, 1))
                self.assertFalse(fit(spec, 1.25, 1))


class CabinetContainmentTests(unittest.TestCase):
    # A 10×10 pocket with a notch from x=4 to x=6 above y=4.
    outline = _ring([(0, 0), (10, 0), (10, 10), (6, 10), (6, 4), (4, 4), (4, 10), (0, 10)])

    def test_rectangles_match_exact_notched_pocket_reference(self):
        rng = random.Random(15873)
        cases = [
            (1, 6, 9, 8),  # Every corner is in the pocket, but the top and bottom cross the notch.
            (1, 2, 9, 4),  # Touches the floor of the notch.
            (4, 4, 4, 10),  # A degenerate ring along the wall of the notch.
            (5, 6, 5, 6),  # A degenerate ring in the notch.
        ]
        for _ in range(384):
            x0, x1 = sorted(F(rng.randrange(-2, 23), 2) for _ in range(2))
            y0, y1 = sorted(F(rng.randrange(-2, 23), 2) for _ in range(2))
            cases.append((x0, y0, x1, y1))
        for x0, y0, x1, y1 in cases:
            with self.subTest(rectangle=(x0, y0, x1, y1)):
                ring = _ring([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
                in_outer_box = 0 <= x0 <= x1 <= 10 and 0 <= y0 <= y1 <= 10
                enters_notch = x0 < 6 and x1 > 4 and y1 > 4
                self.assertEqual(cabinet._covers(self.outline, ring), in_outer_box and not enters_notch)

    def test_near_tangent_edge(self):
        # The diagonal through (4, 4) just touches the reflex corner. A
        # parallel shift of 1e-15 enters the notch with both endpoints inside.
        tiny = F(1, 10**15)
        self.assertTrue(cabinet._covers(self.outline, _ring([(3, 5), (5, 3)])))
        self.assertFalse(cabinet._covers(self.outline, _ring([(3, 5 + tiny), (5, 3 + tiny)])))

    def test_empty_rings_and_repeated_vertices(self):
        duplicate = (self.outline[0], *self.outline)
        self.assertTrue(cabinet._covers(duplicate, _ring([(0, 0), (0, 0)])))
        self.assertFalse(cabinet._covers(duplicate, _ring([(20, 20), (20, 20)])))
        self.assertFalse(cabinet._covers((), _ring([(0, 0)])))
        self.assertTrue(cabinet._covers(self.outline, ()))


class CabinetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fresh = cabinet.build_document()
        cls.stored = json.loads(JSON_PATH.read_text())

    def test_ids_and_committed_document(self):
        ids = [item["id"] for item in self.stored["dissections"]]
        self.assertEqual(ids, ["haberdasher", "perigal", "greek-cross", "rectangle-square"])
        self.assertEqual([item["id"] for item in self.fresh["dissections"]], ids)
        for stored, fresh in zip(self.stored["dissections"], self.fresh["dissections"]):
            self.assertEqual(stored["citation"], fresh["citation"])
            self.assertEqual(
                [piece["id"] for piece in stored["pieces"]],
                [piece["id"] for piece in fresh["pieces"]],
            )
            for a, b in zip(stored["pieces"], fresh["pieces"]):
                self.assertEqual(a["area"]["exact"], b["area"]["exact"])
                if "start_exact" in a:
                    self.assertEqual(a["start_exact"], b["start_exact"])
                    self.assertEqual(a["end_exact"], b["end_exact"])

    def test_haberdasher_areas_stay_canonical(self):
        haber = self.stored["dissections"][0]
        self.assertEqual(haber["triangle_area"]["exact"], "sqrt(3)/4")
        got = {piece["id"]: piece["area"]["exact"] for piece in haber["pieces"]}
        self.assertEqual(got, CANONICAL)
        for exact in got.values():
            self.assertNotIn("sqrt(-", exact.replace(" ", ""))

    def test_new_dissections_are_rigid_and_partition_both_ends(self):
        for item in self.stored["dissections"]:
            if item["id"] == "haberdasher":
                continue
            self.assertEqual(item["motion"]["type"], "rigid")
            self.assertIn(0, item["samples"])
            self.assertIn(1, item["samples"])
            ids = [piece["id"] for piece in item["pieces"]]
            self.assertEqual(len(ids), len(set(ids)))
            total = F(item["area"]["exact"])
            for key in ("start_exact", "end_exact"):
                rings = [_ring(piece[key]) for piece in item["pieces"]]
                self.assertFalse(cabinet._overlaps(rings), item["id"] + " " + key)
                self.assertEqual(sum(cabinet._area(ring) for ring in rings), total)
            shifted = tuple((x + F(1, 5), y) for x, y in _ring(item["pieces"][0]["start_exact"]))
            others = [_ring(piece["start_exact"]) for piece in item["pieces"][1:]]
            self.assertTrue(cabinet._overlaps([shifted, *others]))

    def test_tiles_fit_and_an_oversized_kerf_does_not(self):
        for item in self.stored["dissections"]:
            if item["id"] == "haberdasher":
                continue
            spec = item["print"]
            self.assertTrue(cabinet.tiles_fit(item, spec["kerf_mm"], spec["side_mm"]))
            self.assertFalse(cabinet.tiles_fit(item, 12.0, spec["side_mm"]))


if __name__ == "__main__":
    unittest.main()
