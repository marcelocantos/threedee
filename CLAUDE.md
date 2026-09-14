# threedee

Parametric 3D parts for 3D printing, built with
[build123d](https://github.com/gumyr/build123d) (Python).

## Structure

- `projects/` — Individual part designs (one `.py` per part)
- `export/` — Build output (STL + STEP), gitignored
- `bullseye.yaml` — Convergence targets (edit via the bullseye tools, not by hand)

## Build

```bash
make        # Build all parts to export/
make clean  # Remove export/
```

## Conventions

- Each project file is a standalone script that exports STL and STEP
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

## Gates

profile: base
override:
  - pr-workflow: skip
