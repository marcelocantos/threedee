# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Port oracle: compare each OpenSCAD part with its build123d port.

For every ``<name>.scad`` in the repo root (libraries excluded) this renders
the reference with OpenSCAD to ``export/ref/<name>.stl`` (cached on mtime),
loads the port's ``export/<name>.stl`` (built by ``make``), and computes:

- volume of each and their ratio,
- bounding-box deltas,
- symmetric-difference volume as a fraction of the reference volume, both
  as exported and after aligning centroids (so a pure translation of the
  whole part is reported separately from a shape mismatch).

Mesh booleans are exact (manifold3d). Circles in OpenSCAD are polygons, so
the reference is rendered with ``$fn=120`` to keep facet error well under
0.1 % of volume; per-call ``$fn`` (hex sockets etc.) is unaffected.

References are rendered as OFF, not STL: OpenSCAD 2021's ASCII STL writes
each facet's vertices at limited precision, and on large meshes enough of
them fail to merge that the mesh comes back with hundreds of open edges.
OFF keeps index-based topology, so the reference is manifold by
construction. A pre-existing ``.stl`` reference is still accepted.

Usage: ``python tools/port_oracle.py [name ...] [--diff-stl] [--threshold F]``
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import Manifold, Mesh

ROOT = Path(__file__).resolve().parent.parent
EXPORT = ROOT / "export"
# Reference renders are slow (BOSL2 parts take minutes); a worktree can point
# PORT_ORACLE_REF_DIR at the main checkout's export/ref to reuse them.
REF_DIR = Path(os.environ.get("PORT_ORACLE_REF_DIR", EXPORT / "ref"))
DIFF_DIR = EXPORT / "diff"
LIBRARIES = {"gears.scad"}
REF_FN = 120
MERGE_DIGITS = 4  # merge vertices within 1e-4 mm: CGAL emits near-duplicate pairs


@dataclass
class Report:
    name: str
    status: str                 # ok | no-export | stale-export | not-watertight | render-failed
    ref_volume: float = 0.0
    port_volume: float = 0.0
    ref_bbox: list | None = None
    port_bbox: list | None = None
    symdiff: float = float("nan")          # (Vr + Vp - 2 Vi) / Vr as exported
    symdiff_aligned: float = float("nan")  # same after matching centroids
    centroid_offset: float = float("nan")  # |centroid_port - centroid_ref| in mm


def render_reference(scad: Path) -> Path:
    REF_DIR.mkdir(parents=True, exist_ok=True)
    for ext in (".off", ".stl"):
        cached = REF_DIR / (scad.stem + ext)
        if cached.exists() and cached.stat().st_mtime >= scad.stat().st_mtime:
            return cached
    out = REF_DIR / (scad.stem + ".off")
    subprocess.run(
        ["openscad", "-o", str(out), "-D", f"$fn={REF_FN}", str(scad)],
        check=True, capture_output=True, text=True, cwd=ROOT,
    )
    return out


def load_manifold(path: Path) -> tuple[trimesh.Trimesh, Manifold | None]:
    """Load an STL as a trimesh (for bbox/centroid) and an exact Manifold.

    OCC's STL export leaves duplicated seam vertices and the odd degenerate
    triangle; merging vertices and dropping degenerate faces, then letting
    manifold3d merge open edges within tolerance, closes them. Anything
    still open is reported as not watertight rather than guessed at.
    """
    mesh = trimesh.load(path, force="mesh")
    mesh.merge_vertices(digits_vertex=MERGE_DIGITS)
    mesh.update_faces(mesh.nondegenerate_faces())
    if mesh.volume < 0:
        mesh.invert()
    raw = Mesh(np.asarray(mesh.vertices, np.float32), np.asarray(mesh.faces, np.uint32))
    raw.merge()
    man = Manifold(raw)
    if man.status() != man.status().__class__.NoError:
        return mesh, None
    return mesh, man


def symmetric_difference(ref: Manifold, port: Manifold) -> float:
    inter = (ref ^ port).volume()
    return (ref.volume() + port.volume() - 2 * inter) / ref.volume()


def compare(name: str, diff_stl: bool) -> Report:
    scad = ROOT / f"{name}.scad"
    port_stl = EXPORT / f"{name}.stl"
    if not port_stl.exists():
        return Report(name, "no-export")
    # make touches export/.<module>.stamp only after a successful build; an
    # STL older than its script is a leftover from an earlier build.
    stamp = EXPORT / f".{name.replace('-', '_')}.stamp"
    script = ROOT / "projects" / f"{name.replace('-', '_')}.py"
    if not stamp.exists() or stamp.stat().st_mtime < script.stat().st_mtime:
        return Report(name, "stale-export")
    try:
        ref_stl = render_reference(scad)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(e.stderr[-2000:])
        return Report(name, "render-failed")

    ref_mesh, ref = load_manifold(ref_stl)
    port_mesh, port = load_manifold(port_stl)
    rep = Report(
        name, "ok",
        ref_volume=float(ref_mesh.volume), port_volume=float(port_mesh.volume),
        ref_bbox=np.round(ref_mesh.bounds, 2).tolist(),
        port_bbox=np.round(port_mesh.bounds, 2).tolist(),
    )
    if ref is None or port is None:
        rep.status = "not-watertight"
        return rep

    offset = port_mesh.center_mass - ref_mesh.center_mass
    rep.centroid_offset = float(np.linalg.norm(offset))
    rep.symdiff = symmetric_difference(ref, port)
    rep.symdiff_aligned = symmetric_difference(ref, port.translate(-offset))

    if diff_stl:
        DIFF_DIR.mkdir(parents=True, exist_ok=True)
        for label, man in (("missing", ref - port), ("extra", port - ref)):
            m = man.to_mesh()
            trimesh.Trimesh(m.vert_properties[:, :3], m.tri_verts).export(DIFF_DIR / f"{name}-{label}.stl")
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help="part names (default: every .scad in the repo root)")
    ap.add_argument("--diff-stl", action="store_true", help="write export/diff/<name>-{missing,extra}.stl")
    ap.add_argument("--threshold", type=float, default=None,
                    help="exit 1 if any part's aligned symmetric difference exceeds this fraction")
    ap.add_argument("--json", type=Path, default=None, help="also write reports as JSON")
    args = ap.parse_args()

    names = args.names or sorted(p.stem for p in ROOT.glob("*.scad") if p.name not in LIBRARIES)
    reports = [compare(n, args.diff_stl) for n in names]
    reports.sort(key=lambda r: -(r.symdiff_aligned if r.symdiff_aligned == r.symdiff_aligned else 9e9))

    print(f"{'part':<24} {'status':<14} {'ref mm3':>10} {'port mm3':>10} {'vol':>6} {'symdiff':>8} {'aligned':>8} {'shift':>6}")
    for r in reports:
        vol = f"{r.port_volume / r.ref_volume:.3f}" if r.ref_volume else "-"
        print(f"{r.name:<24} {r.status:<14} {r.ref_volume:>10.0f} {r.port_volume:>10.0f} {vol:>6} "
              f"{r.symdiff:>8.3f} {r.symdiff_aligned:>8.3f} {r.centroid_offset:>6.1f}")

    if args.json:
        args.json.write_text(json.dumps([asdict(r) for r in reports], indent=2))

    if args.threshold is not None:
        bad = [r for r in reports if r.status != "ok" or r.symdiff_aligned > args.threshold]
        if bad:
            print(f"\nFAIL: {', '.join(r.name for r in bad)}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
