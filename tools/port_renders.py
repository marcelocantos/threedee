# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Contact sheets comparing OpenSCAD reference and build123d port renders.

For each part, renders the reference STL, the port STL, and the two diff
meshes (missing = in reference only, extra = in port only) from four camera
angles with OpenSCAD, and tiles them into ``export/renders/<name>.png``.
Rows are views; columns are reference, port, diff (missing in red, extra in
blue). Run ``tools/port_oracle.py --diff-stl`` first so the diff meshes exist.

All three columns share one camera derived from the reference bounding box,
so a misplaced port shows as displaced, not rescaled. Fine red/blue speckle
on curved faces is facet noise between the 120-gon reference and the port's
true circles, not a defect.

This is a visual veto for a human, not the iteration signal; the oracle's
numbers are the signal.

Usage: ``python tools/port_renders.py [name ...]``
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
EXPORT = ROOT / "export"
LIBRARIES = {"gears.scad"}
SIZE = 400
# (label, OpenSCAD --camera "eye/centre" spec is built per part; these are direction vectors)
VIEWS = [("iso", (1, -1, 1)), ("top", (0, 0, 1)), ("front", (0, -1, 0.001)), ("side", (1, 0, 0.001))]


def render(scad_src: str, out: Path, centre, distance, direction) -> None:
    eye = [c + d * distance for c, d in zip(centre, direction)]
    cam = ",".join(f"{v:.3f}" for v in (*eye, *centre))
    with tempfile.NamedTemporaryFile("w", suffix=".scad", delete=False) as f:
        f.write(scad_src)
        src = f.name
    subprocess.run(
        ["openscad", "-o", str(out), "--camera", cam, "--projection", "ortho",
         "--imgsize", f"{SIZE},{SIZE}", src],
        check=True, capture_output=True, text=True,
    )


def sheet(name: str) -> Path | None:
    ref = EXPORT / "ref" / f"{name}.stl"
    port = EXPORT / f"{name}.stl"
    missing = EXPORT / "diff" / f"{name}-missing.stl"
    extra = EXPORT / "diff" / f"{name}-extra.stl"
    if not (ref.exists() and port.exists()):
        return None
    import trimesh
    m = trimesh.load(ref, force="mesh")
    centre = tuple(m.bounds.mean(axis=0))
    distance = float(max(m.extents)) * 2.4  # ortho zoom follows eye distance

    columns = [
        ("reference", f'import("{ref}");'),
        ("port", f'import("{port}");'),
        ("diff", f'color("red") import("{missing}"); color("blue") import("{extra}");'
                 f' %import("{ref}");' if missing.exists() and extra.exists() else ""),
    ]
    out_dir = EXPORT / "renders"
    out_dir.mkdir(parents=True, exist_ok=True)
    grid = Image.new("RGB", (SIZE * len(columns), SIZE * len(VIEWS) + 20), "white")
    draw = ImageDraw.Draw(grid)
    for ci, (label, _) in enumerate(columns):
        draw.text((ci * SIZE + 8, 4), f"{name}: {label}", fill="black")
    with tempfile.TemporaryDirectory() as tmp:
        for vi, (vlabel, direction) in enumerate(VIEWS):
            for ci, (_, src) in enumerate(columns):
                if not src:
                    continue
                png = Path(tmp) / f"{vi}-{ci}.png"
                render(src, png, centre, distance, direction)
                grid.paste(Image.open(png).convert("RGB"), (ci * SIZE, 20 + vi * SIZE))
            draw.text((8, 24 + vi * SIZE), vlabel, fill="black")
    out = out_dir / f"{name}.png"
    grid.save(out)
    return out


def main() -> int:
    names = sys.argv[1:] or sorted(p.stem for p in ROOT.glob("*.scad") if p.name not in LIBRARIES)
    for n in names:
        out = sheet(n)
        print(f"{n}: {out if out else 'skipped (missing STL)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
