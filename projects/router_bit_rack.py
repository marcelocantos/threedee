# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Router bit rack — grid of tilted slots with reinforced beam structure."""

from build123d import *
from math import floor

# OpenSCAD's cube() is min-aligned on every axis, while its cylinder()/cone()
# are centred in x/y and sit on z=0. build123d centres everything by default,
# and a bare Align.MIN aligns all three axes.
CUBE = (Align.MIN, Align.MIN, Align.MIN)
BASE_AT_Z0 = (Align.CENTER, Align.CENTER, Align.MIN)

# Slot parameters
slot_diam = 10
slot_height = 13
slot_tilt = 15  # degrees
slot_hole_diam = 6.625
hole_depth = 11
padding = 5

# Grid parameters
grid_unit_x = 24
grid_unit_y = 24.85
grid_cols = 9
grid_rows = 9
grid_width = grid_unit_x * grid_cols
grid_height = grid_unit_y * grid_rows

# Beam/rib parameters
beam_width = 4
rib_width = 1.5
strut_height = 7
rib_height = 1.5

# Mount parameters
mount_diam = 12
mount_inset = 1
mount_offset = beam_width / 2 + mount_diam / 2 - mount_inset


def mount(i, j, a):
    """Corner/center mount with beveled hole."""
    y = i * grid_unit_y
    x = j * grid_unit_x
    bevel_diam = 9
    height = 3

    disc = Cylinder(radius=mount_diam / 2, height=height, align=BASE_AT_Z0)
    bevel = Pos(0, 0, height - bevel_diam / 2) * Cone(
        bottom_radius=0, top_radius=bevel_diam / 2,
        height=bevel_diam / 2, align=BASE_AT_Z0,
    )
    m = disc - bevel
    return Pos(x, y, 0) * Rot(0, 0, a) * Pos(mount_offset, mount_offset, 0) * m


mid_row = floor(grid_rows / 2)
mid_col = floor(grid_cols / 2)

solids = []

# Horizontal ribs and beams
for i in range(grid_rows + 1):
    y = i * grid_unit_y
    solids.append(Pos(0, y - rib_width / 2, 0) * Box(grid_width, rib_width, strut_height, align=CUBE))
    solids.append(Pos(0, y - beam_width / 2, 0) * Box(grid_width, beam_width, rib_height, align=CUBE))

# Vertical ribs and beams
for j in range(grid_cols + 1):
    x = j * grid_unit_x
    solids.append(Pos(x - rib_width / 2, 0, 0) * Box(rib_width, grid_height, strut_height, align=CUBE))
    solids.append(Pos(x - beam_width / 2, 0, 0) * Box(beam_width, grid_height, rib_height, align=CUBE))

# Tilted slot cylinders (outer)
for i in range(grid_rows + 1):
    for j in range(grid_cols + 1):
        cyl = Cylinder(radius=slot_diam / 2, height=slot_height + padding, align=BASE_AT_Z0)
        solids.append(
            Pos(j * grid_unit_x, i * grid_unit_y, 0) * Rot(-slot_tilt, 0, 0) * Pos(0, 0, -padding) * cyl
        )

# Corner and centre mounts
for args in [(0, 0, 0), (0, grid_cols, 90), (grid_rows, grid_cols, 180), (grid_rows, 0, 270)]:
    solids.append(mount(*args))
solids.append(mount(mid_row, mid_col, 0))

# Reinforced horizontal beam at row 4
solids.append(
    Pos(0, 4 * grid_unit_y - beam_width / 2, 0) * Box(grid_width, beam_width, strut_height, align=CUBE)
)

# Reinforced vertical strut near center mount
x_strut = mid_col * grid_unit_x + mount_offset + mount_diam / 2 - 1.5
solids.append(
    Pos(x_strut, 0, 0) * Box(beam_width - rib_width, grid_height, strut_height, align=CUBE)
)

rack = Part() + solids

# --- Subtractions ---
cuts = []

# Hole cylinders
for i in range(grid_rows + 1):
    for j in range(grid_cols + 1):
        cyl = Cylinder(radius=slot_hole_diam / 2, height=slot_height, align=BASE_AT_Z0)
        cuts.append(
            Pos(j * grid_unit_x, i * grid_unit_y, 0)
            * Rot(-slot_tilt, 0, 0)
            * Pos(0, 0, slot_height - hole_depth)
            * cyl
        )

# Clip below z=0
cuts.append(
    Pos(-10, -10, -10) * Box(grid_width + 20, grid_height + 20, 10, align=CUBE)
)

result = rack - cuts

export_stl(result, "router-bit-rack.stl")
export_step(result, "router-bit-rack.step")

try:
    from ocp_vscode import show
    show(result)
except ImportError:
    pass
