# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Screw box partitions — trapezoid-shaped dividers with chamfered edges and drain holes."""

from build123d import *

h = 41
w = 49
r = 0.5

# Main trapezoid body: translate([r, 0, 0]) linear_extrude(1.4) polygon(...)
# with the local h shadowed to h - 2*r inside the SCAD union() block.
h_body = h - 2 * r
body_pts = [
    (0, 0),
    (h_body, 0.5),
    (h_body, w - 0.5),
    (0, w),
]
body = Pos(r, 0, 0) * extrude(Polygon(body_pts), amount=1.4)

# Rounded edge (rib along the x=0 edge): translate([r2, 0, r2])
# rotate(-90, [1, 0, 0]) cylinder(h=w, r=r2) — the z-axis cylinder is
# rotated to run along y, then pinned tangent to x=0 and z=0.
r2 = 0.7
rib = Pos(r2, 0, r2) * Rot(-90, 0, 0) * Cylinder(
    radius=r2, height=w, align=(Align.CENTER, Align.CENTER, Align.MIN)
)

part = body + rib

# Chamfer cuts at the top-right corners (outer, un-shadowed h/w).
c = 5
chamfer_top = Pos(h, r, 0) * Rot(0, 0, 45) * Box(c, c, 4)
chamfer_bottom = Pos(h, w - r, 0) * Rot(0, 0, 45) * Box(c, c, 4)
part -= chamfer_top
part -= chamfer_bottom

# Recessed area: translate([2.5, 2, 0.8]) linear_extrude(1.4) of a smaller
# polygon (outer h/w shadowed to h-5 / w-4 inside this block; the
# minkowski() with a single child is a no-op in the original SCAD).
h_recess = h - 5
w_recess = w - 4
recess_pts = [
    (0, 0),
    (h_recess, 0.5),
    (h_recess, w_recess - 0.5),
    (0, w_recess),
]
recess = Pos(2.5, 2, 0.8) * extrude(Polygon(recess_pts), amount=1.4)
part -= recess

# Drain holes grid: grid_copies(spacing=4, n=[9, 11]) centered at
# (h/2, w/2), each a min-aligned d=2.5 x h=1 cylinder.
for ix in range(-4, 5):
    for iy in range(-5, 6):
        hole = Pos(h / 2 + ix * 4, w / 2 + iy * 4, 0) * Cylinder(
            radius=1.25, height=1, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        part -= hole

result = part

export_stl(result, "screw-box-partitions.stl")
export_step(result, "screw-box-partitions.step")

try:
    from ocp_vscode import show
    show(result)
except ImportError:
    pass
