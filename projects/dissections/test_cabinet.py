# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Oracle for the dissection cabinet: exact areas, both arrangements, tray fit."""

import json
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
