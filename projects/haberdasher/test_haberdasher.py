# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Exact area oracle and tray-fit check for the haberdasher."""

import json
import math
import random
import unittest
from pathlib import Path

import sympy as sp

import geometry

ROOT = Path(__file__).resolve().parent
JSON_PATH = ROOT / "pieces.json"


class HaberdasherOverlapTests(unittest.TestCase):
    def test_rectangles_match_an_exact_interval_reference(self):
        first = (0, 0, 3, 2)
        tiny = sp.Rational(1, 10**15)
        cases = [
            (first, first),
            (first, (1, 0, 4, 2)),  # Positive area with all vertices on the edges or outside.
            (first, (3, 0, 4, 2)),  # Shared edge.
            (first, (3, 2, 4, 3)),  # Point contact.
            (first, (3 - tiny, 0, 4, 2)),
            (first, (3 + tiny, 0, 4, 2)),
            (first, (1, 0, 1, 2)),  # Zero area through the interior.
            (first, (1, 1, 1, 1)),
        ]
        rng = random.Random(51483)

        def sample_box():
            x0, x1 = sorted(sp.Rational(rng.randrange(-8, 9), 2) for _ in range(2))
            y0, y1 = sorted(sp.Rational(rng.randrange(-8, 9), 2) for _ in range(2))
            return x0, y0, x1, y1

        def shear(box):
            x0, y0, x1, y1 = box
            skew = sp.Rational(2, 7)
            return [sp.Point(x + skew * y, y) for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]]

        cases.extend((sample_box(), sample_box()) for _ in range(128))
        for a, b in cases:
            with self.subTest(a=a, b=b):
                # The shear is invertible. The sign of intersection area
                # follows directly from the two original interval lengths.
                separated = min(a[2], b[2]) <= max(a[0], b[0]) or min(a[3], b[3]) <= max(a[1], b[1])
                self.assertEqual(geometry.interior_disjoint([shear(a), shear(b)]), bool(separated))
        self.assertTrue(geometry.interior_disjoint([]))
        self.assertTrue(geometry.interior_disjoint([shear(first), []]))

    def test_symbolic_near_parallel_gap_and_overlap(self):
        h, tiny = sp.sqrt(2), sp.Rational(1, 10**15)
        left = [sp.Point(0, 0), sp.Point(1, 0), sp.Point(0, h)]
        gap = [sp.Point(0, h + tiny), sp.Point(1, 0), sp.Point(1, h)]
        overlap = [sp.Point(0, h - tiny), sp.Point(1, 0), sp.Point(1, h)]
        self.assertTrue(geometry.interior_disjoint([left, gap]))
        self.assertFalse(geometry.interior_disjoint([left, overlap]))


class InsetPolygonTests(unittest.TestCase):
    def test_rectangles_match_analytic_insets(self):
        rng = random.Random(4972)
        for i in range(128):
            width, height = rng.randrange(1, 41), rng.randrange(1, 41)
            tx, ty = rng.randrange(-20, 21), rng.randrange(-20, 21)
            quarter = i % 4

            def transform(x, y):
                x, y = ((x, y), (-y, x), (-x, -y), (y, -x))[quarter]
                return (x + tx, y + ty)

            ring = [transform(0, 0), transform(width, 0), transform(width, height), transform(0, height)]
            limit = min(width, height) / 2
            for distance in (0, limit / 4, limit - 2**-20, limit, limit + 0.25, max(width, height)):
                with self.subTest(i=i, distance=distance):
                    if distance >= limit:
                        with self.assertRaises(ValueError):
                            geometry.inset_polygon(ring, distance)
                        continue
                    x0 = y0 = distance
                    x1, y1 = width - distance, height - distance
                    expected = {transform(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))}
                    actual = geometry.inset_polygon(ring, distance)
                    self.assertEqual(len(actual), 4)
                    # 1e-12 mm covers the line division and multiplication
                    # roundoff for coordinates under 64 mm.
                    for corner in expected:
                        self.assertLessEqual(min(math.dist(corner, point) for point in actual), 1e-12)

    def test_degenerate_edges_and_distances(self):
        square = [(0, 0), (2, 0), (2, 2), (0, 2)]
        for ring in ([], square[:1], square[:2], [square[0], *square], [(0, 0), (1, 0), *square[1:]]):
            with self.subTest(ring=ring), self.assertRaises(ValueError):
                geometry.inset_polygon(ring, 0)
        for distance in (-1, math.inf, -math.inf, math.nan):
            with self.subTest(distance=distance), self.assertRaises(ValueError):
                geometry.inset_polygon(square, distance)

    def test_small_positive_turn_still_produces_a_miter(self):
        # Symmetric bevel: its apex moves down by d * hypot(1, h).
        h, distance = 2**-20, 0.25
        inset = geometry.inset_polygon([(-1, -1), (1, -1), (1, 0), (0, h), (-1, 0)], distance)
        # Adjacent-line intersection divides by a small determinant. Check at
        # 1e-10 mm, far below the kerf and above roundoff at this slope.
        self.assertAlmostEqual(inset[2][0], 0, delta=1e-10)
        self.assertAlmostEqual(inset[2][1], h - distance * math.hypot(1, h), delta=1e-10)


class HaberdasherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = geometry.prove()
        cls.doc = geometry.cabinet_document(cls.proof)
        cls.dissection = cls.doc["dissections"][0]
        cls.stored = json.loads(JSON_PATH.read_text())["dissections"][0]

    def test_committed_json_matches_the_proof(self):
        self.assertEqual(self.stored["citation"], geometry.CITATION)
        self.assertEqual(self.stored["swing"], -1)
        self.assertEqual(self.stored["hinges"], ["D", "E", "K"])
        self.assertEqual(
            [p["id"] for p in self.stored["pieces"]],
            ["red", "blue", "orange", "green"],
        )
        self.assertEqual(self.stored["triangle_area"]["exact"], "sqrt(3)/4")
        self.assertEqual(self.stored["square_side"]["exact"], "3**(1/4)/2")
        for name, rec in self.stored["points"].items():
            fresh = self.doc["dissections"][0]["points"][name]
            self.assertEqual(rec["exact"], fresh["exact"])
            self.assertAlmostEqual(rec["xy"][0], fresh["xy"][0], places=12)
            self.assertAlmostEqual(rec["xy"][1], fresh["xy"][1], places=12)
        for stored, fresh in zip(self.stored["pieces"], self.dissection["pieces"]):
            self.assertEqual(stored["area"]["exact"], fresh["area"]["exact"])
            self.assertEqual(len(stored["vertices"]), len(set(stored["vertices"])))

    def test_tiles_fit_both_pockets_after_kerf(self):
        spec = self.stored["print"]
        self.assertTrue(geometry.tiles_fit(self.stored, spec["kerf_mm"], spec["side_mm"]))

    def test_oversized_kerf_does_not_fit(self):
        # Past the smallest piece's inradius the inset leaves a pocket.
        self.assertFalse(geometry.tiles_fit(self.stored, 12.0, self.stored["print"]["side_mm"]))


if __name__ == "__main__":
    unittest.main()
