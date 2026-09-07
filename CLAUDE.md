# threedee

Parametric 3D parts for 3D printing, built with
[build123d](https://github.com/gumyr/build123d) (Python).

## Structure

- `projects/` — Individual part designs (one `.py` per part)
- `export/` — Build output (STL + STEP), gitignored
- `docs/targets.md` — Convergence targets

## Build

```bash
make        # Build all parts to export/
make clean  # Remove export/
pytest      # Geometry oracles (bbox/solid-count checks on the built parts)
```

`make` only checks that each script exited 0, which is not enough to catch a
part that builds cleanly but is the wrong shape. `tests/` asserts on the solids.

## Conventions

- Each project file is a standalone script that exports STL and STEP
- Use build123d's algebra API (operators `+`, `-`, `&`) for combining solids
- No epsilon hacks — BREP handles coincident faces correctly
- File names use underscores in Python, hyphens in exports

## Delivery

Merged to master.

## TODO

`docs/TODO.md`
