# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Bosch adapter — cylindrical adapter with tapered slots and snap tabs."""

from build123d import *

# OpenSCAD's cylinder()/cone() sit on the z=0 plane, centred on the z axis.
# build123d's bare Align.MIN would also shift them into the +x/+y quadrant.
BASE_AT_Z0 = (Align.CENTER, Align.CENTER, Align.MIN)

# Extrusion tolerance for 0.4mm nozzle
t = 0.2

hmid = 15
hhi = 25 - t

# Radii (inner/outer at low/mid/high)
rilo = 46.38 / 2 - t
rolo = 48.36 / 2 - t
rimid = 45.54 / 2 - t
romid = 47.31 / 2 - t

rslotmid = 46.2 / 2
hslotmid = 11.26

r3lo = 35.65 / 2 + t / 2
r3hi = 35 / 2 + t / 2

# Chord widths for slots
chordmid = 11.15
chordlo = 13.5


def slot_mask(chord_lo, chord_mid, h, r_outer):
    """Trapezoidal wedge spanning the full diameter, used to carve slot arcs."""
    pts = [
        (chord_lo / 2, 0),
        (-chord_lo / 2, 0),
        (-chord_mid / 2, h),
        (chord_mid / 2, h),
    ]
    return extrude(Plane.XZ * Polygon(*pts, align=None), amount=2 * r_outer, both=True)


mask = slot_mask(chordlo, chordmid, hmid, rolo)

# Main cylinder, less the inner bore and the entry chamfer at the base.
parts = [
    Cone(bottom_radius=rilo, top_radius=rimid, height=hhi, align=BASE_AT_Z0)
    - Cone(bottom_radius=r3lo, top_radius=r3hi, height=hhi, align=BASE_AT_Z0)
    - Cone(bottom_radius=rilo, top_radius=0, height=rilo / 1.5, align=BASE_AT_Z0)
]

# Primary slots (3 at 45-degree intervals)
slot_shell = (
    Cone(bottom_radius=rolo, top_radius=romid, height=hmid, align=BASE_AT_Z0)
    - Cone(bottom_radius=rilo, top_radius=rimid, height=hmid, align=BASE_AT_Z0)
)
parts += [slot_shell & (Rot(0, 0, 45 * i) * mask) for i in [1, 2, 3]]

# Tab slot (single, at angle 0). The mask spans the full diameter, so this
# yields the two arcs the OpenSCAD original also produces.
tab_shell = (
    Cone(bottom_radius=rolo, top_radius=rslotmid, height=hslotmid, align=BASE_AT_Z0)
    - Cone(bottom_radius=rilo, top_radius=rslotmid - t, height=hslotmid, align=BASE_AT_Z0)
)
parts.append(tab_shell & mask)

# Snap tabs
dot = 2
tab = Pos(0, -rslotmid - 0.3, hslotmid + dot) * (
    Rot(-90, 0, 0)
    * scale(
        Sphere(radius=dot) + Cylinder(radius=dot, height=3 * dot, align=BASE_AT_Z0),
        by=(2, 1, 0.2),
    )
)
parts += [Rot(0, 0, 180 * i) * tab for i in range(2)]

body = Part() + parts

# Flip: original translates up by hhi then rotates 180 around X
result = Pos(0, 0, hhi) * (Rot(180, 0, 0) * body)

export_stl(result, "bosch-adapter.stl")
export_step(result, "bosch-adapter.step")

try:
    from ocp_vscode import show
    show(result)
except ImportError:
    pass
