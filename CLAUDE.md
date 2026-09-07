# threedee

Parametric 3D parts for 3D printing, built with
[build123d](https://github.com/gumyr/build123d) (Python).

## Structure

- `projects/` — Individual part designs (one `.py` per part)
- `export/` — Build output (STL + STEP), gitignored
- `docs/targets.md` — Convergence targets

## Build

```bash
make        # Build all parts to export/, then check their geometry
make clean  # Remove export/
```

`make` ends with `tools/check_geometry.py`, which measures every exported
STL against `expectations.yaml` and fails the build on empty, degenerate or
misplaced output. The expected volumes and bounding boxes come from
rendering the OpenSCAD originals (`openscad -o ref.stl <part>.scad`), not
from the build123d output they gate.

## Conventions

- Each project file is a standalone script that exports STL and STEP
- Use build123d's algebra API (operators `+`, `-`, `&`) for combining solids
- No epsilon hacks — BREP handles coincident faces correctly
- File names use underscores in Python, hyphens in exports

## Delivery

Merged to master.

## TODO

`docs/TODO.md`
