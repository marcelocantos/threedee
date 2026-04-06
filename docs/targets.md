# Convergence Targets

## 🎯T1 All designs are build123d Python, OpenSCAD files retired

All `.scad` files have been ported to equivalent build123d Python scripts
in `projects/`. The OpenSCAD files and vendored `gears.scad` are removed.
Exported `.3mf` files are generated from the Python sources.

**Status**: Starting — project structure created, no files ported yet.

### 🎯T1.1 Project infrastructure supports build123d workflow

- `Makefile` builds all projects to `export/`
- `.gitignore` covers Python/build artifacts
- A simple proof-of-concept port validates the approach

**Status**: In progress.

### 🎯T1.2 All simple parts ported (no external library dependencies)

Files: `magnet-tube`, `led-stumps`, `nailgun-tip`, `baby-gate-latch`,
`bosch-adapter`, `catflap-rpi`, `rotary-bearing`, `router-bit-rack`.

**Status**: Not started.

### 🎯T1.3 BOSL2-dependent parts ported

Files: `screw-box-partitions`, `starlock-holders`, `machinist-square-mount`.
These use BOSL2 features (offset_sweep, grid_copies, etc.) that need
build123d equivalents.

**Status**: Not started.

### 🎯T1.4 Gear-dependent parts ported

File: `triton-lifter`. Needs a bevel gear implementation in build123d
(replacing `gears.scad`).

**Status**: Not started.
