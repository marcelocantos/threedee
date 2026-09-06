Parametric 3D-printable parts as build123d Python scripts, ported from OpenSCAD originals kept alongside.

# threedee

Parametric 3D parts for 3D printing, built with
[build123d](https://github.com/gumyr/build123d) (Python).
[`README.md`](README.md) covers the prerequisites, the build, and the
current state of the ports.

## Structure

- `projects/` — the parts, one standalone `.py` script per part
- `*.scad` — the OpenSCAD originals; `gears.scad` is a third-party library
- `export/` — build output (STL + STEP), gitignored
- `bullseye.yaml` — convergence targets; use the bullseye tools, never edit by hand
- `docs/audits/` — entropy audits; the 2026-08-22 one lists the ports that
  diverge from their `.scad`

## Build

```bash
make        # build all parts to export/
make clean  # remove export/
```

There is no test suite: running a script is the check. `python3 -m
py_compile projects/*.py` is the only check that runs without the CAD
kernel. `make` currently stops at `projects/bosch_adapter.py:63`
(`ValueError: Cannot move an empty shape`); `make -k` builds the other
eleven. `projects/triton_lifter.py` needs `py_gearworks`.

## Conventions

- Each project file is a standalone script that exports STL and STEP, then
  tries `ocp_vscode.show()` inside a `try` / `except ImportError`
- Use build123d's algebra API (operators `+`, `-`, `&`) for combining solids.
  Ten existing parts still use builder mode (`BuildPart`); do not mix the two
  in one part — a `Pos * Shape` result is silently discarded inside a
  `BuildPart` context unless passed to `add()`
- OpenSCAD's `cylinder(h=)` is min-aligned and build123d's `Cylinder` is
  centered: when porting a `translate()`, port the alignment too
- No epsilon hacks — BREP handles coincident faces correctly
- No magic numbers: give every dimension a named parameter at the top of the
  script, as the existing parts do
- File names use underscores in Python, hyphens in exports and `.scad`
- A port is not done until its geometry has been checked against the `.scad`
  original or a print

## Delivery

Merged to master.
