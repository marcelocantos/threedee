# threedee

Parametric parts for 3D printing, written as
[build123d](https://github.com/gumyr/build123d) Python scripts. Each script
under `projects/` is one part and exports it as STL and STEP. The OpenSCAD
originals the scripts were ported from are kept alongside them.

## Prerequisites

Python 3 with `build123d` installed in whatever `python` the Makefile finds
on `PATH`. `projects/triton_lifter.py` also needs `py_gearworks` for its
bevel gears (`projects/triton_lifter.py:11`). There is no requirements file,
lockfile, or `pyproject.toml` — the dependency set is whatever the ambient
interpreter has.

`ocp_vscode` is optional. Every script ends with `from ocp_vscode import
show` inside a `try` / `except ImportError`, so a missing module is silently
skipped (e.g. `projects/magnet_tube.py:36-40`). If `ocp_vscode` *is*
installed but no viewer is listening, each script prints a `CommsWarning`
traceback (`ValueError: Port could not be cast to integer value as 'None'`)
and still exports its files.

## Build

```bash
make          # every part → export/<part>.stl and export/<part>.step
make -k       # keep going past the part that currently fails (see below)
make clean    # remove export/
cd export && python ../projects/magnet_tube.py   # one part
```

`make` keeps a stamp per part in `export/.<part>.stamp` (`Makefile:6-8`), so
only scripts newer than their stamp are rebuilt. Scripts write their outputs
into the current directory, which is why the Makefile runs them from
`export/`. `export/` and mesh files are gitignored (`.gitignore`).

**`make` does not currently complete.** `projects/bosch_adapter.py:63`
(`add(shell & (Rot(0, 0, 45 * i) * mask))`) raises `ValueError: Cannot move
an empty shape` under build123d `0.10.1.dev310+ge8cae0660` — the boolean
intersection comes back empty. The other eleven parts export cleanly under
`make -k`. There is no test suite; running the scripts is the only check,
and `python3 -m py_compile projects/*.py` is the only check that runs
without the CAD kernel.

## Layout

| Path | Role |
|---|---|
| `projects/*.py` | The parts (twelve): baby gate latch, Bosch adapter, cat-flap Raspberry Pi housing, LED stumps, machinist-square mount, magnet tube, nail-gun tip, rotary-bearing jig, router-bit rack, screw-box partitions, Starlock holders, Triton lifter. |
| `*.scad` | The OpenSCAD originals. `gears.scad` is a third-party involute gear library, used by `triton-lifter.scad`. |
| `Makefile` | Builds everything under `export/`. |
| `bullseye.yaml` | Targets. Edit via the bullseye tools, never by hand. |
| `docs/audits/` | Dated entropy audits. |

File names use underscores in Python (`magnet_tube.py`) and hyphens for the
OpenSCAD files and exports (`magnet-tube.scad`, `magnet-tube.stl`).

## Status

The Python scripts are the declared source, but the 2026-08-22 entropy audit
([`docs/audits/entropy-audit-2026-08-22.md`](docs/audits/entropy-audit-2026-08-22.md))
found that several ports do not reproduce their OpenSCAD originals, and
nothing checks a port against its `.scad`:

- Rails, ribs, and holes collapse to the origin in `starlock_holders.py`,
  `screw_box_partitions.py`, and `router_bit_rack.py`, where a
  `Pos * Shape` result is discarded inside a `BuildPart` context (ENT-002).
- `magnet_tube.py` places its barrier 17.5 mm above the tube, because
  build123d's `Cylinder` is centered where OpenSCAD's is min-aligned
  (ENT-003).
- `catflap_rpi.py` shifts its outer shell by the camera width twice, so the
  port cutouts do not line up with the shell (ENT-004).

Treat a `.scad` file as the reference geometry until its port has been
printed or diffed against the original. Ten of the twelve scripts use
build123d's builder mode (`BuildPart`); the convention for new work is the
algebra API.

## License

The twelve Python scripts carry `# SPDX-License-Identifier: Apache-2.0`
headers. There is no `LICENSE` file. `gears.scad:45` declares itself
Creative Commons Attribution-NonCommercial-ShareAlike, which is not
compatible with an Apache-2.0 repository licence; that conflict is
unresolved.
