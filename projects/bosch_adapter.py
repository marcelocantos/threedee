# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Bosch adapter — cylindrical adapter with tapered slots and snap tabs."""

from build123d import *

# Small deltas, exactly as in the SCAD source: several subtractions in this
# part cut a void whose radius profile only grazes (rather than crosses) the
# solid it's cut from, which is a degenerate, mesh-fragile boolean. The SCAD
# nudges those cuts by d/d2 so they genuinely cross instead of merely
# touching; build123d needs the same nudge for the same reason (confirmed:
# without it, `main` and the tab-slot shell are only tangent along a single
# circle and OCC's fuse leaves a crack there).
d = 0.001
d2 = 2 * d

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

# OpenSCAD's cylinder()/cone() are centred in x/y and run from z=0 to z=h.
MIN_Z = (Align.CENTER, Align.CENTER, Align.MIN)


def cone(bottom_radius, top_radius, height, z0=0.0):
    """A z0..z0+height cone, centred in x/y (OpenSCAD cylinder() convention)."""
    c = Cone(bottom_radius=bottom_radius, top_radius=top_radius, height=height, align=MIN_Z)
    return Pos(0, 0, z0) * c if z0 else c


def union(*parts):
    """Fuse a series of shapes, working around `+` occasionally degrading
    a multi-solid fuse result to a bare ShapeList instead of a Compound."""
    result = parts[0]
    for part in parts[1:]:
        result = result + part
        if isinstance(result, (list, ShapeList)):
            result = Compound(children=list(result))
    return result


def slot_mask(chord_lo, chord_mid, h, r_outer):
    """Trapezoidal slot mask, swept along Y across the full shell radius.

    Mirrors the SCAD mask: a trapezoid drawn in the XZ plane (wide at z=0,
    narrow at z=h), linear-extruded along Y and centred on Y=0.
    """
    with BuildSketch(Plane.XZ) as sk:
        Polygon((chord_lo / 2, 0), (-chord_lo / 2, 0), (-chord_mid / 2, h), (chord_mid / 2, h))
    return extrude(sk.sketch, amount=r_outer, both=True)


mask = slot_mask(chordlo, chordmid, hmid, rolo)

# Main cylinder: tapered tube (nudged +d, per SCAD), bored out, with a
# conical entry chamfer at the bottom.
main = (
    cone(rilo + d, rimid + d, hhi)
    - cone(r3lo, r3hi, hhi + d2, -d)
    - cone(rilo, 0, rilo / 1.5, -d2)
)

# Primary slots (3 at 45-degree intervals): a tapered annular shell, sliced by
# the mask rotated to each slot's angle.
slots = []
for i in (1, 2, 3):
    shell = cone(rolo, romid, hmid) - cone(rilo, rimid, hmid + d2, -d)
    slots.append(shell & (Rot(0, 0, 45 * i) * mask))
primary_slots = union(*slots)

# Tab slot (single, at angle 0): same idea, shorter shell, unrotated mask.
tab_shell = cone(rolo, rslotmid, hslotmid) - cone(rilo, rslotmid - t, hslotmid + d2, -d)
tab_slot = tab_shell & mask

# Snap tabs: a scaled sphere+cylinder blob, mounted on the tab-slot wall at
# angle 0 and 180.
dot = 2
tabs = []
for i in range(2):
    blob = union(Sphere(radius=dot), Cylinder(radius=dot, height=3 * dot, align=MIN_Z))
    scaled = scale(blob, by=(2, 1, 0.2))
    tabs.append(Rot(0, 0, 180 * i) * Pos(0, -rslotmid - 0.3, hslotmid + dot) * Rot(-90, 0, 0) * scaled)
snap_tabs = union(*tabs)

assembly = union(main, primary_slots, tab_slot, snap_tabs)

# Original: translate([0, 0, hhi]) rotate(180, [1, 0, 0]) { ... }
result = Pos(0, 0, hhi) * Rot(180, 0, 0) * assembly

export_stl(result, "bosch-adapter.stl")
export_step(result, "bosch-adapter.step")

try:
    from ocp_vscode import show
    show(result)
except ImportError:
    pass
