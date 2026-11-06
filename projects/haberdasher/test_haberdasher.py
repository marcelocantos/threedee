# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Exact area oracle and tray-fit check for the haberdasher."""

import json
import unittest
from pathlib import Path

import geometry

ROOT = Path(__file__).resolve().parent
JSON_PATH = ROOT / "pieces.json"


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
