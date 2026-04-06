# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Bosch adapter — cylindrical adapter with tapered slots and snap tabs."""

from build123d import *

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
    """Extruded trapezoidal slot mask."""
    pts = [
        (chord_lo / 2, 0),
        (-chord_lo / 2, 0),
        (-chord_mid / 2, h),
        (chord_mid / 2, h),
    ]
    with BuildPart() as p:
        with BuildSketch(Plane.XZ):
            Polygon(pts)
        extrude(amount=2 * r_outer, both=True)
    return p.part


mask = slot_mask(chordlo, chordmid, hmid, rolo)

# Build using context manager for clean solid management
with BuildPart() as adapter:
    # Main cylinder
    Cone(bottom_radius=rilo, top_radius=rimid, height=hhi, align=Align.MIN)
    # Inner bore
    Cone(bottom_radius=r3lo, top_radius=r3hi, height=hhi, align=Align.MIN, mode=Mode.SUBTRACT)
    # Bottom cone (entry chamfer)
    Cone(bottom_radius=rilo, top_radius=0, height=rilo / 1.5, align=Align.MIN, mode=Mode.SUBTRACT)

    # Primary slots (3 at 45-degree intervals)
    for i in [1, 2, 3]:
        shell = (
            Cone(bottom_radius=rolo, top_radius=romid, height=hmid, align=Align.MIN)
            - Cone(bottom_radius=rilo, top_radius=rimid, height=hmid, align=Align.MIN)
        )
        add(shell & (Rot(0, 0, 45 * i) * mask))

    # Tab slot (single, at angle 0)
    tab_shell = (
        Cone(bottom_radius=rolo, top_radius=rslotmid, height=hslotmid, align=Align.MIN)
        - Cone(bottom_radius=rilo, top_radius=rslotmid - t, height=hslotmid, align=Align.MIN)
    )
    add(tab_shell & mask)

    # Snap tabs
    dot = 2
    for i in range(2):
        with BuildPart(mode=Mode.ADD) as tab:
            Sphere(radius=dot)
            Cylinder(radius=dot, height=3 * dot, align=Align.MIN)
        scaled = scale(tab.part, by=(2, 1, 0.2))
        positioned = Rot(0, 0, 180 * i) * (Pos(0, -rslotmid - 0.3, hslotmid + dot) * Rot(-90, 0, 0)) * scaled
        add(positioned)

# Flip: original translates up by hhi then rotates 180 around X
result = adapter.part.mirror(Plane.XY).moved(Pos(0, 0, hhi))

export_stl(result, "bosch-adapter.stl")
export_step(result, "bosch-adapter.step")
