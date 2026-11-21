# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

import contextlib
import copy
import io
import json
import math
import random
import struct
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import geometry_record


def _binary_stl(facets, header=b"test mesh"):
    records = (
        struct.pack("<12fH", 0, 0, 0, *(component for point in triangle for component in point), 0)
        for triangle in facets
    )
    return header.ljust(80, b"\0") + struct.pack("<I", len(facets)) + b"".join(records)


def _gram_area(triangle):
    a, b, c = [[Fraction(component) for component in point] for point in triangle]
    u = [end - start for start, end in zip(a, b)]
    v = [end - start for start, end in zip(a, c)]
    determinant = sum(x * x for x in u) * sum(y * y for y in v) - sum(x * y for x, y in zip(u, v)) ** 2
    return math.sqrt(determinant) / 2


class MeshIdentityTests(unittest.TestCase):
    def test_area_bounds_and_hashes_on_seeded_binary_stls(self):
        rng = random.Random(51381)
        origin = (0, 0, 0)
        collinear = [origin, (1, 1, 1), (2, 2, 2)]
        zero_edge = [origin, origin, (-1, 2, -3)]
        thin = [origin, (1, 1, 0), (2, 2 + 2**-20, 0)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shape.stl"
            for sample in range(48):
                with self.subTest(sample=sample):
                    facets = [collinear, zero_edge, thin]
                    for _ in range(8):
                        facets.append([tuple(rng.randrange(-128, 129) / 8 for _ in range(3)) for _ in range(3)])
                    expected_area = math.fsum(_gram_area(triangle) for triangle in facets)
                    coordinates = list(zip(*(point for triangle in facets for point in triangle)))
                    path.write_bytes(_binary_stl(facets))
                    measured = geometry_record.mesh_identity(path)
                    path.write_bytes(_binary_stl(list(reversed(facets)), header=b"different header"))
                    reordered = geometry_record.mesh_identity(path)

                    self.assertEqual(measured["triangles"], len(facets))
                    self.assertEqual(measured["mesh_sha256"], reordered["mesh_sha256"])
                    self.assertEqual(measured["occupancy_sha256"], reordered["occupancy_sha256"])
                    self.assertNotEqual(measured["raw_sha256"], reordered["raw_sha256"])
                    for result in (measured, reordered):
                        self.assertEqual(list(map(float, result["mesh_bbox_min"])), [min(axis) for axis in coordinates])
                        self.assertEqual(list(map(float, result["mesh_bbox_max"])), [max(axis) for axis in coordinates])
                        # 1e-10 mm² allows floating sums of eleven facets with
                        # |coordinate| <= 16 mm. The Gram determinant is exact.
                        self.assertAlmostEqual(float(result["mesh_area"]), expected_area, delta=1e-10)

    def test_rejects_unusable_binary_stls(self):
        origin = (0, 0, 0)
        unit_triangle = [origin, (1, 0, 0), (0, 1, 0)]
        files = {
            "empty": (_binary_stl([]), "no triangles"),
            "all-degenerate": (_binary_stl([[origin, (1, 1, 1), (2, 2, 2)]]), "no positive-area triangles"),
            "nan": (_binary_stl([[origin, (math.nan, 0, 0), (0, 1, 0)]]), "non-finite vertex"),
            "infinite": (_binary_stl([[origin, (math.inf, 0, 0), (0, 1, 0)]]), "non-finite vertex"),
            "truncated": (_binary_stl([unit_triangle])[:-1], "binary STL length"),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.stl"
            for case, (payload, diagnostic) in files.items():
                with self.subTest(case=case), self.assertRaisesRegex(SystemExit, f"invalid.stl.*{diagnostic}"):
                    path.write_bytes(payload)
                    geometry_record.mesh_identity(path)


class GeometryToleranceTests(unittest.TestCase):
    def test_step_noise_applies_only_to_the_artifact_that_showed_it(self):
        unstable_script = "projects/scale-rails/scale_rails.py"
        unstable_file = "scale-rails-plate.step"
        stable_script = "projects/led_stumps.py"
        stable_file = "led-stumps.step"
        noise = 0.125
        step = {
            "volume": "8",
            "bbox_min": ["0", "0", "0"],
            "bbox_max": ["2", "2", "2"],
            "center_of_mass": ["1", "1", "1"],
            "face_count": 6,
        }
        baseline = {
            "build123d": "test",
            "parts": {
                unstable_script: {unstable_file: dict(step)},
                stable_script: {stable_file: dict(step)},
            },
            "noise": {
                "max_abs_volume": noise,
                "step_tolerances": {f"{unstable_script}:{unstable_file}": {"volume": noise}},
            },
        }
        fresh = copy.deepcopy(baseline)
        fresh["parts"][unstable_script][unstable_file]["volume"] = str(8 + noise / 2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            path.write_text(json.dumps(baseline))
            with patch.object(geometry_record, "measure", return_value=fresh):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(geometry_record.check(path), 0)
                fresh["parts"][stable_script][stable_file]["volume"] = str(8 + noise / 2)
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(geometry_record.check(path), 1)
                self.assertIn(stable_file + " volume", output.getvalue())
                self.assertNotIn(unstable_file + " volume", output.getvalue())


if __name__ == "__main__":
    unittest.main()
