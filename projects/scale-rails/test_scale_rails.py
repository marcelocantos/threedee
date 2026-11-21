# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
import struct
import subprocess
import sys


def test_fresh_builds_have_the_same_triangle_counts(tmp_path):
    script = Path(__file__).with_name("scale_rails.py")
    meshes = ("scale-rails-installed.stl", "scale-rails-plate.stl")
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    samples = []
    for run in range(2):
        output = tmp_path / str(run)
        output.mkdir()
        subprocess.run(
            [sys.executable, str(script), "--no-preview"], cwd=output, env=env, check=True
        )
        counts = {}
        for name in meshes:
            with (output / name).open("rb") as mesh:
                mesh.seek(80)  # The triangle count follows the binary STL header.
                counts[name], = struct.unpack("<I", mesh.read(4))
        samples.append(counts)

    assert samples[0] == samples[1]
