# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Mixer stand: holds a Braun MultiQuick stick-blender motor body (no shaft
fitted) upright, nose down.

The coupling tip drops into a 45-degree funnel. The funnel narrows to an
open bore just a little smaller than the tip, so the tip's bottom edge lands
on the 45-degree wall and centres itself there; nothing touches the drive
socket, and the bore is open right through so drips fall out and the funnel
is easy to wipe. Above the funnel a loose guide sleeve surrounds the wide
ring (lock-release buttons included) with generous clearance and a big 45-degree
lead-in, so the body drops in easily and only snugs up when the tip meets the
cone. A 45-degree skirt joins the sleeve to a wide round base, so the tall,
heavy body is hard to tip over.

Print it as exported: base flat on the bed, no supports (the funnel and the
skirt are 45-degree slopes, and the windows are diamonds with 45-degree roofs).
"""

import argparse
import math
import sys
from pathlib import Path

from build123d import *

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_part  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--no-preview", action="store_true", help="Export without opening the CAD viewer")
parser.add_argument("--no-standin", action="store_true", help="Skip exporting the mixer stand-in STL")
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Mixer motor body (mm), nose down. z = 0 at the tip's bottom edge.
# ---------------------------------------------------------------------------
ring_diameter = 61.0        # MEASURED 13 Nov 2026 -- wide ring INCLUDING the two lock-release buttons
coupling_diameter = 31.6    # MEASURED 13 Nov 2026 -- coupling end at its narrowest
ring_to_tip = 36.0          # MEASURED 13 Nov 2026 (approx) -- bottom of the wide ring to the tip
body_length = 235.0         # MEASURED 13 Nov 2026 -- overall length
tip_diameter = 33.0         # ESTIMATE -- outer diameter at the very tip (lipped past the narrow point)
tip_lip_height = 3.0        # ESTIMATE -- height of that lip
collar_diameter = 40.0      # ESTIMATE -- the short step between the knurled coupling and the ring
collar_height = 8.0         # ESTIMATE
ring_core_diameter = 58.0   # ESTIMATE -- the ring without the buttons
ring_height = 12.0          # ESTIMATE
body_diameter = (56.0, 50.0)  # ESTIMATE -- body just above the ring, and near the top
body_mass = 700.0           # g, ESTIMATE ("fairly dense")
cg_fraction = (0.45, 0.50, 0.55)  # ESTIMATE -- centre of gravity as a fraction of body_length above the tip

# ---------------------------------------------------------------------------
# Stand (mm).
# ---------------------------------------------------------------------------
cone_undersize = 1.5        # Bore (cone bottom) diameter = tip_diameter - this
seat_floor = 3.0            # Height of the open bore below the cone (the tip lands just above this)
guide_clearance = 2.0       # Radial gap between the ring (buttons included) and the guide sleeve
guide_engage = 8.0          # Straight sleeve height alongside the ring, above its bottom edge
lead_in = 4.0               # 45-degree lead-in at the top of the sleeve
wall = 6.0                  # Sleeve wall thickness (must exceed lead_in + 2 * round_small)
skirt_top = 12.0            # Height where the 45-degree skirt meets the sleeve
base_diameter = 140.0       # Round footprint
base_thick = 4.0            # Base plate thickness
base_edge_round = 2.0       # Rounding on the base's top outer edge
bottom_chamfer = 0.6        # Elephant-foot chamfer round the bottom outer edge
skirt_fillet = 5.0          # Cove where the skirt meets the base plate (easy to wipe)
round_small = 0.8           # Rounding on the sleeve's top edges (x3 on the skirt shoulder)
window_count = 8            # Diamond windows in the sleeve below the ring (0 = none)
window_half = (6.0, 7.0)    # Diamond half-width, half-height (half-height >= half-width keeps 45-degree roofs)
base_window_count = 18      # Diamond openings round the base plate (0 = none)
base_window_half = 5.0      # Half-diagonal of each base opening
base_rim = 6.0              # Solid rim outside the base openings
hollow_shell = 3.5          # Underside hollow under the funnel and skirt, leaving this shell (0 = solid)

bed_size = 256              # Bambu X1 Carbon
pla = 1.24                  # g/cm^3

# ---------------------------------------------------------------------------
# Derived geometry. Stand coordinates: z = 0 on the bed, axis on z.
# ---------------------------------------------------------------------------
r_bore = (tip_diameter - cone_undersize) / 2
r_tip = tip_diameter / 2
r_guide = ring_diameter / 2 + guide_clearance
r_out = r_guide + wall
R = base_diameter / 2
z_cone_top = seat_floor + (r_guide - r_bore)          # 45 degrees: rise = run
z_contact = seat_floor + (r_tip - r_bore)             # where the tip's edge meets the cone
z_ring = z_contact + ring_to_tip                      # bottom of the wide ring
z_band_top = z_ring + guide_engage
z_top = z_band_top + lead_in
r_skirt = r_out + (skirt_top - base_thick)            # 45-degree skirt
if wall < lead_in + 2 * round_small + 0.2:
    raise ValueError("wall must exceed lead_in + 2 * round_small")
if r_bore >= coupling_diameter / 2:
    raise ValueError("Bore is wider than the coupling: the tip would not land on the cone")
if r_skirt + skirt_fillet + 1 > R - base_rim - 2 * base_window_half and base_window_count:
    raise ValueError("Base too small for the base openings")

pts = [
    (r_bore, 0), (R - bottom_chamfer, 0), (R, bottom_chamfer), (R, base_thick),
    (r_skirt, base_thick), (r_out, skirt_top), (r_out, z_top),
    (r_guide + lead_in, z_top), (r_guide, z_band_top), (r_guide, z_cone_top),
    (r_bore, seat_floor),
]
profile = Plane.XZ * Polygon(*pts, align=None)


def vertex_at(face, x, z):
    return [v for v in face.vertices() if abs(v.X - x) < 1e-6 and abs(v.Z - z) < 1e-6]


for (x, z), rad in (((R, base_thick), base_edge_round), ((r_skirt, base_thick), skirt_fillet),
                    ((r_out, skirt_top), round_small * 3), ((r_out, z_top), round_small),
                    ((r_guide + lead_in, z_top), round_small), ((r_guide, z_band_top), round_small),
                    ((r_guide, z_cone_top), round_small * 2), ((r_bore, seat_floor), 0.6)):
    profile = fillet(vertex_at(profile, x, z), rad)

if hollow_shell:
    t = hollow_shell * math.sqrt(2)               # vertical offset of a 45-degree shell of that thickness
    r_in = r_bore + hollow_shell
    z_in = seat_floor + (r_in - r_bore) - t      # under the funnel at the inner wall
    r_pk = (base_thick + r_skirt - seat_floor + r_bore) / 2
    z_pk = seat_floor + (r_pk - r_bore) - t      # apex where the funnel and skirt undersides meet
    r_co = r_skirt - hollow_shell - base_thick   # outer edge on the bed
    if z_in <= 0.5 or r_co <= r_in + 2:
        raise ValueError("Hollow does not fit; reduce hollow_shell or set it to 0")
    profile -= Plane.XZ * Polygon((r_in, 0), (r_co, 0), (r_pk, z_pk), (r_in, z_in), align=None)

stand = revolve(profile, Axis.Z, 360)

if window_count:
    hw, hh = window_half
    zc = (max(skirt_top + round_small * 3, z_cone_top + round_small * 2) + z_ring) / 2
    if zc - hh < skirt_top or zc + hh > z_ring:
        raise ValueError("Sleeve windows do not fit between the skirt and the ring")
    pl = Plane(origin=(r_guide - 1, 0, zc), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    win = extrude(pl * Polygon((hw, 0), (0, hh), (-hw, 0), (0, -hh), align=None), amount=wall + 2)
    for i in range(window_count):
        stand -= Rotation(0, 0, 360 * (i + 0.5) / window_count) * win

if base_window_count:
    rw = (r_skirt + skirt_fillet + R - base_rim) / 2
    h = base_window_half
    hole = Pos(rw, 0, -1) * extrude(Plane.XY * Polygon((h, 0), (0, h), (-h, 0), (0, -h), align=None),
                                    amount=base_thick + 2)
    for i in range(base_window_count):
        stand -= Rotation(0, 0, 360 * (i + 0.5) / base_window_count) * hole

# ---------------------------------------------------------------------------
# Rough stand-in for the motor body (checks and previews only; not its real shape).
# ---------------------------------------------------------------------------
def cyl(d, z0, z1):
    return Pos(0, 0, z0) * Cylinder(d / 2, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


zt = z_contact
tip = cyl(tip_diameter, zt, zt + tip_lip_height)
coupling = cyl(coupling_diameter, zt + tip_lip_height, z_ring - collar_height)
collar = cyl(collar_diameter, z_ring - collar_height, z_ring)
ring = cyl(ring_core_diameter, z_ring, z_ring + ring_height)
btn_w = (ring_diameter - ring_core_diameter) / 2 + 3
for s in (1, -1):
    ring += Pos(s * (ring_diameter / 2 - btn_w / 2), 0, z_ring + 1) * Box(btn_w, 14, ring_height - 2,
                                                                           align=(Align.CENTER, Align.CENTER, Align.MIN))
ring = Part(ring.intersect(cyl(ring_diameter, z_ring, z_ring + ring_height)).solids())   # buttons' outer faces lie on the 61 mm circle
z_body = z_ring + ring_height
z_end = zt + body_length
body = Pos(0, 0, z_body) * Cone(body_diameter[0] / 2, body_diameter[1] / 2, z_end - z_body - 8,
                                align=(Align.CENTER, Align.CENTER, Align.MIN))
body += Pos(0, 0, z_end - 8) * Cylinder(body_diameter[1] / 2, 8, align=(Align.CENTER, Align.CENTER, Align.MIN))
body = fillet(body.edges().group_by(Axis.Z)[-1], 6)
body += Pos(0, -body_diameter[1] / 2 + 2, z_end - 45) * Box(16, 8, 30, align=(Align.CENTER, Align.CENTER, Align.MIN))  # switch
body += Pos(0, body_diameter[1] / 2 - 2, z_end - 30) * (Rotation(-60, 0, 0) * Cylinder(5, 25, align=(Align.CENTER, Align.CENTER, Align.MIN)))  # cord
mixer = tip + coupling + collar + ring + body

# ---------------------------------------------------------------------------
# Checks.
# ---------------------------------------------------------------------------
assert len(stand.solids()) == 1 and stand.is_valid, "Stand must be one valid solid"
vol = stand.volume


def overlap(a, b):
    r = a & b
    if r is None:
        return 0.0
    return sum(x.volume for x in r) if isinstance(r, (list, ShapeList)) else r.volume


lowered = overlap(Pos(0, 0, -0.1) * mixer, stand)
raised = overlap(Pos(0, 0, 0.05) * mixer, stand)
assert lowered > 0, "Tip does not meet the cone"
assert raised < 1e-6, f"Stand-in clashes with the stand above the seat ({raised:.3f} mm^3)"
assert r_bore < r_tip, "Tip would drop through the bore"
tip_gap_below = z_contact  # nothing under the tip: the bore is open to the table
ring_gap = stand.distance_to(ring)
coupling_gap = stand.distance_to(coupling + collar)
assert abs(ring_gap - guide_clearance) < 0.05, f"Ring clearance {ring_gap:.2f}"
# Lean allowed by the guide: pivot on the tip's far edge, ring corner meets the sleeve.
lean = math.degrees(math.atan2(guide_clearance, z_band_top - z_contact))
stand_cg = stand.center().Z
tips = []
for f in cg_fraction:
    z_m = z_contact + f * body_length
    z_cg = (body_mass * z_m + vol / 1000 * pla * stand_cg) / (body_mass + vol / 1000 * pla)
    tips.append((f, z_m, math.degrees(math.atan2(R, z_cg)), math.degrees(math.atan2(R, z_m))))

bb = stand.bounding_box()
to_bed = Pos(bed_size / 2, bed_size / 2, -bb.min.Z)
stand_bed = to_bed * stand
mixer_bed = to_bed * mixer
bbb = stand_bed.bounding_box()
if bbb.min.X < 0 or bbb.min.Y < 0 or bbb.max.X > bed_size or bbb.max.Y > bed_size:
    raise ValueError("Stand is off the bed")

export_part.export_stl(stand_bed, "mixer-stand.stl", tolerance=0.02, angular_tolerance=0.08)
export_part.export_step(stand_bed, "mixer-stand.step")
if not args.no_standin:
    export_part.export_stl(mixer_bed, "mixer-standin.stl", tolerance=0.05, angular_tolerance=0.2)

print(f"mixer-stand: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm; "
      f"{vol / 1000:.1f} cm^3 (~{vol / 1000 * pla:.0f} g PLA); solids {len(stand.solids())}, valid {stand.is_valid}")
print(f"  bore/cone bottom {2 * r_bore:.1f} mm at z {seat_floor:.1f}; cone top {2 * r_guide:.1f} mm at z {z_cone_top:.2f}; "
      f"tip edge ({tip_diameter:.1f}) seats at z {z_contact:.2f}, {z_contact - seat_floor:.2f} mm above the bore, open below")
print(f"  guide ID {2 * r_guide:.1f} mm (ring {ring_diameter:.1f} incl. buttons, {guide_clearance:.1f} mm/side; "
      f"measured gap {ring_gap:.2f}); band z {z_ring:.1f}..{z_band_top:.1f}, lead-in to {2 * (r_guide + lead_in):.1f} at z {z_top:.1f}")
print(f"  coupling/collar to stand min gap {coupling_gap:.2f} mm; clash raised 0.05 mm: {raised:.4f} mm^3; "
      f"overlap lowered 0.1 mm: {lowered:.3f} mm^3 (tip on the cone)")
print(f"  lean allowed by the guide ~{lean:.1f} deg; base {base_diameter:.0f} mm round")
for f, z_m, a, a0 in tips:
    print(f"  tip-over: mixer CoG {f * 100:.0f}% ({z_m:.0f} mm up): {a:.1f} deg with {body_mass:.0f} g + stand, "
          f"{a0:.1f} deg ignoring the stand's weight")

if not args.no_preview:
    export_part.preview(stand, mixer)
