# threedee

Parametric 3D parts for 3D printing, built with
[build123d](https://github.com/gumyr/build123d) (Python).

This is the shared instruction file. `CLAUDE.md` points here.

## Structure

- `projects/` — Part designs, command-line generators, and project tests
- `projects/trolley-key/` — Shopping trolley coin substitute (ring hook), with source, README and local exports
- `projects/scale-rails/` — One-piece under-shelf cradle (two rails joined by a back wall) for the Soehnle kitchen scale, with source, README and local exports
- `projects/puzzle-tray/` — Tray for a 3 × 3 wooden picture-cube puzzle (replaces its cardboard box), with source, README and local exports
- `projects/express-1m2-stand/` — Open lattice stand holding an OWC Express 1M2 SSD upright on its long edge, fins vertical, 10 mm off the table, with source, README and local exports
- `projects/mixer-stand/` — Upright nose-down stand for a Braun MultiQuick stick-blender motor body: 45° cone seat for the coupling tip, loose guide sleeve round the wide ring, 140 mm round base, with source, README and local exports
- `projects/ascut/` — Measurement-driven dovetail mate and calibrated thickness gauge
- `projects/haberdasher/` and `projects/dissections/` — Printable dissection trays and tiles with exact geometry tests
- `export/` — Build output (STL + STEP), gitignored
- `tools/bambu/` — Local LAN tools for the Bambu X1 Carbon (preset flattening, FTPS upload, MQTT print/status, camera stills). Credentials are read from Bambu Studio at runtime; see `tools/bambu/README.md`.
- `bullseye.yaml` — Convergence targets (edit via the bullseye tools, not by hand)

## Build

The CAD kernel is the pinned `build123d` release in `pyproject.toml`
(`uv.lock` pins the transitive set). `make` runs it with
`uv run --frozen --offline` from the worktree `.venv`, not from a
global interpreter.

```bash
uv sync     # Create .venv and install the lockfile
make        # Build the default part set to its export/ directories
make clean  # Remove the default build outputs
```

## Conventions

- Part generators can run as scripts and export STL and STEP
- The default Make targets share STL, STEP and viewer calls through `export_part.py`
- Use build123d's algebra API (operators `+`, `-`, `&`) for combining solids
- No epsilon hacks — BREP handles coincident faces correctly
- File names use underscores in Python, hyphens in exports

## Porting from OpenSCAD

Every defect in the 2026-09 port audit came from one of these:

- `Cylinder`, `Cone`, `Box` are centred on all axes; OpenSCAD `cylinder`
  is base-aligned and `cube` corner-aligned. Use
  `align=(Align.CENTER, Align.CENTER, Align.MIN)` for cylinders and cones,
  `align=(Align.MIN,)*3` for cubes. Never pass a bare scalar `Align.MIN`:
  it applies to all three axes and slides a cylinder off its own axis.
- No `BuildPart`. `Pos(...) * Shape(...)` inside a builder adds the
  unlocated copy and discards the located one.
- `minkowski` with a sphere is an outward `offset(kind=Kind.ARC)`, not a
  `fillet`. BOSL2 `rounding=` is a fillet.
- `rotate([a, b, c])` is extrinsic: `Rotation(X=a, Y=b, Z=c,
  ordering=Extrinsic.XYZ)` when more than one angle is nonzero.
- `cylinder($fn=N)` with small N is a deliberate polygon (first vertex on
  +x); port it as `RegularPolygon`, not a circle.
- `Polygon` points must be counterclockwise; clockwise gives a reversed
  face that never fuses with its neighbours.

## Delivery

Pushed to master.
