# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import geometry_record


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
