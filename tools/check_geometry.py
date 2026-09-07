# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Fail the build when an exported part is empty, degenerate or misplaced.

Every project script exits 0 as long as build123d can serialise *something*,
so a clean build has never been evidence that the geometry is right. This
compares each exported STL against `expectations.yaml`, whose numbers come
from rendering the OpenSCAD original — not from the build123d output they
gate. Parts with no faithful OpenSCAD counterpart are marked as such in the
expectations file and are ratcheted against their own recorded baseline.
"""

import struct
import sys
from pathlib import Path

import numpy as np
import yaml

BINARY_HEADER_BYTES = 84
MIN_TRIANGLES = 4  # fewer cannot bound a volume
MIN_VOLUME_MM3 = 1e-6


def load_stl(path):
    """Return an (n, 3, 3) array of triangle vertices from an ASCII or binary STL."""
    blob = path.read_bytes()
    if blob[:5] == b"solid" and b"facet normal" in blob[:2048]:
        verts = [
            [float(x) for x in line.split()[1:4]]
            for line in blob.decode("utf-8", "replace").splitlines()
            if line.split()[:1] == ["vertex"]
        ]
        return np.array(verts, dtype=float).reshape(-1, 3, 3)
    if len(blob) < BINARY_HEADER_BYTES:
        return np.empty((0, 3, 3))
    (count,) = struct.unpack("<I", blob[80:84])
    dtype = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])
    recs = np.frombuffer(blob, dtype=dtype, count=count, offset=BINARY_HEADER_BYTES)
    return recs["v"].astype(float)


def measure(tris):
    """Signed-tetrahedron volume and bounding box of a closed mesh."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    volume = np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0
    flat = tris.reshape(-1, 3)
    return volume, flat.min(axis=0), flat.max(axis=0)


def check(name, path, expected, volume_fraction, bbox_mm):
    """Yield one failure message per way this part's geometry is wrong."""
    if not path.exists():
        yield f"{name}: {path} was not exported"
        return
    tris = load_stl(path)
    if len(tris) < MIN_TRIANGLES:
        yield f"{name}: {len(tris)} triangles — the mesh is empty or degenerate"
        return

    volume, lo, hi = measure(tris)
    if volume <= MIN_VOLUME_MM3:
        yield f"{name}: volume {volume:.6g} mm^3 — empty, or the mesh is inside out"
        return

    want_volume = expected["volume"]
    drift = abs(volume - want_volume) / want_volume
    if drift > volume_fraction:
        yield (
            f"{name}: volume {volume:.3f} mm^3, expected {want_volume:.3f} "
            f"({drift:.2%} off, limit {volume_fraction:.2%})"
        )

    want_lo, want_hi = (np.array(v, dtype=float) for v in expected["bbox"])
    slip = max(np.abs(lo - want_lo).max(), np.abs(hi - want_hi).max())
    if slip > bbox_mm:
        yield (
            f"{name}: bounding box {np.round(lo, 3)}..{np.round(hi, 3)}, expected "
            f"{want_lo}..{want_hi} ({slip:.3f} mm out, limit {bbox_mm} mm)"
        )


def main():
    export_dir = Path(sys.argv[1])
    spec = yaml.safe_load(Path(sys.argv[2]).read_text())
    tolerance = spec["tolerance"]

    failures = []
    for name, expected in sorted(spec["parts"].items()):
        failures.extend(
            check(
                name,
                export_dir / f"{name}.stl",
                expected,
                expected.get("volume_fraction", tolerance["volume_fraction"]),
                expected.get("bbox_mm", tolerance["bbox_mm"]),
            )
        )

    if failures:
        print("Geometry check FAILED:", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        sys.exit(1)
    print(f"Geometry check passed: {len(spec['parts'])} parts.")


if __name__ == "__main__":
    main()
