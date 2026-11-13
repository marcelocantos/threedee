# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Express 1M2 stand: an open lattice stand that holds an OWC Express 1M2
external SSD upright on its long edge, about 10 mm off the table, with the
extruded cooling-fin channels vertical so air can rise through them.

The drive drops into a slot between two end trestles. It rests on two thin
lattice rails under its solid (smooth-side) body; nothing touches the fin
tips, and nothing stands between the base and the fins, so air rises from
the table through the diamond openings in the base and straight up the fin
channels. (v2.2: the base lattice runs continuously under the fins; v1 to
v2.1 cut an open window there, which split the lattice.) Side legs bear on the smooth face at
the two ends (clear of the rubber feet), on the solid unfinned block at one
end of the finned face, and on a 2 mm edge strip at the other end. The LED
end is open in the middle; the USB-C end is open above a 6 mm stop, so the
cable leaves freely. The trestles splay out at 45 degrees into a wide
lattice base, so the stand is hard to tip.

v2 to v2.2: the drive's overall length, height and thickness are measured (133 x
72 x 24 mm). Fin depth, the solid block, the edge strip, the rubber feet and
the edge rounding are still ESTIMATES; replace them when measured.

Print it as exported: base flat on the bed, no supports (every opening has a
45-degree or open roof).
"""

import argparse
import math

from build123d import *

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--no-preview", action="store_true", help="Export without opening the CAD viewer")
parser.add_argument("--no-standin", action="store_true", help="Skip exporting the drive stand-in STL")
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Drive: OWC Express 1M2 (mm). Overall size MEASURED; the rest are ESTIMATES.
# Pose: on its long edge. x along the table (length), y across (thickness,
# y = 0 is the smooth face, fins at the +y side), z up (standing height).
# ---------------------------------------------------------------------------
drive_length = 133.0        # MEASURED 12 Nov 2026 (spec said 132) -- long edge, along the table
drive_height = 72.0         # MEASURED 12 Nov 2026 (spec said 71.1) -- the face that stands up
drive_thickness = 24.0      # MEASURED 12 Nov 2026 (spec said 22.8) -- including fins
fin_height = 8.0            # ESTIMATE -- fin depth; the solid body is drive_thickness - fin_height
fin_edge = 2.0              # ESTIMATE -- solid strip at the non-block end of the finned face
block_length = 18.0         # ESTIMATE -- solid unfinned block at one end of the finned face
block_end = "port"          # ESTIMATE -- which end the block is at: "port" (USB-C end) or "led"
corner_radius = 2.0         # ESTIMATE -- rounding on the drive's long edges (rails keep clear of it)
foot_diameter = 12.0        # ESTIMATE -- rubber feet on the smooth face (two of them)
foot_height = 1.5           # ESTIMATE -- how far the feet stand off the smooth face
foot_inset = 22.0           # ESTIMATE -- foot centre from each end of the drive
foot_up = drive_height / 2  # ESTIMATE -- foot centre height up the face
drive_mass = 300            # g, design load (MEASURED about 260 g)

# ---------------------------------------------------------------------------
# Stand (mm).
# ---------------------------------------------------------------------------
fit_clearance = 0.2         # Gap each side between the drive and the stand (v2.1/v2.2: snug; v1/v2 had 0.6)
bottom_gap = 10.0           # Table to the drive's lower long edge
upright_height = 35.0       # Side legs rise this far up the drive's face
led_stop_height = 22.0      # End stops at the LED end (corners only; the middle stays open)
port_stop_height = 6.0      # End stops at the USB-C end (kept low, under the port)
end_stop_wrap = 3.0         # How far the end stops reach round onto the end face
post = 3.0                  # Side-leg thickness (y)
trestle = 2.4               # End-trestle thickness (x)
smooth_leg = 10.0           # Smooth-side legs: length along the face at each end
lead_in = 1.8               # 45-degree drop-in chamfer on the inner top edges
top_chamfer = 0.8           # Outer top edges
member = 2.0                # Lattice member width
base_width = 96.0           # Base footprint across the slot (y)
base_margin = 4.0           # Base beyond the trestles (x)
base_thick = 3.0            # Base plate thickness
base_border = 5.0           # Solid rim round the base lattice
base_corner = 6.0           # Base corner radius
base_pitch = 16.0           # Diamond lattice pitch in the base
rail = 2.0                  # Support-rail thickness (y), under the solid body
rail_inset = (2.5, 3.0)     # Rail outer faces in from the smooth face and from the start of the fins
lip = 2.0                   # Smooth-side lip thickness
lip_height = 3.0            # Smooth-side lip height above the drive's lower edge
toe = 3.0                   # Vertical toe at the outer feet of the trestles (no knife edges)

bed_size = 256              # Bambu X1 Carbon
pla = 1.24                  # g/cm^3

if block_end not in ("port", "led"):
    raise ValueError("block_end must be 'port' or 'led'")

L, T, H = drive_length, drive_thickness, drive_height
body = T - fin_height
c = fit_clearance
g = bottom_gap
y0, y1 = -c, T + c                      # slot faces
yc = T / 2                              # slot centre
x_led0, x_led1 = -c - trestle, -c       # LED-end trestle
x_prt0, x_prt1 = L + c, L + c + trestle  # port-end trestle
side_top = g + upright_height
if block_end == "port":
    fin_x0, fin_x1 = fin_edge, L - block_length
else:
    fin_x0, fin_x1 = block_length, L - fin_edge


def on_xz(pts, y_from, y_to):
    """Prism from an (x, z) profile, between y_from and y_to."""
    pl = Plane(origin=(0, y_from, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
    return extrude(pl * Polygon(*pts, align=None), amount=y_to - y_from, dir=(0, 1, 0))


def on_yz(pts, x_from, x_to):
    """Prism from a (y, z) profile, between x_from and x_to."""
    pl = Plane(origin=(x_from, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    return extrude(pl * Polygon(*pts, align=None), amount=x_to - x_from, dir=(1, 0, 0))


def diamond(u, v, h):
    return [(u + h, v), (u, v + h), (u - h, v), (u, v - h)]


def diamond_row(u0, u1, v0, v1):
    """Diamonds that fit wholly in [u0,u1] x [v0,v1], spaced to leave `member` between."""
    h = (v1 - v0) / 2
    if h < 1.2:
        return []
    pitch = 2 * h + member * math.sqrt(2)
    n = int((u1 - u0 - 2 * h) // pitch) + 1
    span = (n - 1) * pitch
    us = [(u0 + u1) / 2 - span / 2 + i * pitch for i in range(n)]
    return [diamond(u, (v0 + v1) / 2, h) for u in us]


def side_leg_profile(inner_y, outward):
    """(y, z) profile of a side leg; outward = -1 (smooth side) or +1 (fin side)."""
    o = inner_y + outward * post
    pts = [(inner_y, 0), (o, 0), (o, side_top - top_chamfer),
           (o - outward * top_chamfer, side_top), (inner_y + outward * lead_in, side_top),
           (inner_y, side_top - lead_in)]
    return pts if outward > 0 else pts[::-1]


def trestle_profile(stop_top):
    """(y, z) outline of an end trestle, counterclockwise."""
    so, fo = y0 - post, y1 + post                     # outer faces of the side legs
    yl, yr = yc - base_width / 2 + base_border, yc + base_width / 2 - base_border
    reach_l, reach_r = so - yl, yr - fo
    sl, sr = min(side_top - top_chamfer, toe + reach_l), min(side_top - top_chamfer, toe + reach_r)
    s_in, f_in = end_stop_wrap, T - end_stop_wrap
    return [
        (yl, 0), (yr, 0), (yr, toe), (fo, sr),
        (fo, side_top - top_chamfer), (fo - top_chamfer, side_top),
        (y1 + lead_in, side_top), (y1, side_top - lead_in),
        (y1, stop_top), (f_in + lead_in / 2, stop_top), (f_in, stop_top - lead_in / 2),
        (f_in, g - 2),
        (s_in, g - 2),
        (s_in, stop_top - lead_in / 2), (s_in - lead_in / 2, stop_top), (y0, stop_top),
        (y0, side_top - lead_in), (y0 - lead_in, side_top),
        (so + top_chamfer, side_top), (so, side_top - top_chamfer),
        (so, sl), (yl, toe),
    ], (yl, so, sl, yr, fo, sr)


def trestle_holes(dims):
    """Triangular openings in the splayed parts of a trestle (45-degree roofs)."""
    yl, so, sl, yr, fo, sr = dims
    holes = []
    m = member + 0.5
    zb = base_thick
    # Left: right-angle triangle with legs on z = zb and y = so - m; hypotenuse parallel to the 45° slope.
    a = so - m
    top = (toe + (a - yl)) - m * math.sqrt(2)
    left = a - (top - zb)
    if top - zb > 4:
        holes.append([(left, zb), (a, zb), (a, top)])
    b = fo + m
    topr = (toe + (yr - b)) - m * math.sqrt(2)
    right = b + (topr - zb)
    if topr - zb > 4:
        holes.append([(b, zb), (right, zb), (b, topr)])
    return holes


def end_trestle(x_from, x_to, stop_top):
    outline, dims = trestle_profile(stop_top)
    t = on_yz(outline, x_from, x_to)
    for h in trestle_holes(dims):
        t -= on_yz(h, x_from - 1, x_to + 1)
    return t


def lattice_wall(x_from, x_to, y_from, y_to, top, chamfer_side=None):
    """Vertical wall along x with a row of diamond openings below the drive."""
    pts = [(x_from, 0), (x_to, 0), (x_to, top), (x_from, top)]
    w = on_xz(pts, y_from, y_to)
    if chamfer_side is not None:  # lead-in on the slot side (+y) of the top edge
        ch = (y_to - y_from) / 2
        w -= on_yz([(y_to - ch, top), (y_to + 1, top + 1 + ch), (y_to + 1, top - ch - 1)][::-1], x_from - 1, x_to + 1)
    for d in diamond_row(x_from + 4, x_to - 4, base_thick + 0.8, g - 1.5):
        w -= on_xz(d, y_from - 1, y_to + 1)
    return w


# --- base: rounded plate, continuous diamond lattice (v2.2: no window) -----
bx0, bx1 = x_led0 - base_margin, x_prt1 + base_margin
by0, by1 = yc - base_width / 2, yc + base_width / 2
base = Pos((bx0 + bx1) / 2, yc, 0) * extrude(
    RectangleRounded(bx1 - bx0, by1 - by0, base_corner), amount=base_thick)
hp = (base_pitch - member * math.sqrt(2)) / 2
holes = []
nx, ny = int((bx1 - bx0) / base_pitch) + 2, int((by1 - by0) / base_pitch) + 2
for i in range(-nx, nx + 1):
    for j in range(-ny, ny + 1):
        for off in (0, 0.5):
            u, v = (bx0 + bx1) / 2 + (i + off) * base_pitch, yc + (j + off) * base_pitch
            holes.append(Pos(0, 0, -1) * extrude(Plane.XY * Polygon(*diamond(u, v, hp), align=None), amount=base_thick + 2))
inner = Pos((bx0 + bx1) / 2, yc, -1) * Box(bx1 - bx0 - 2 * base_border, by1 - by0 - 2 * base_border,
                                           base_thick + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
base -= Compound(holes) & inner
if len(base.solids()) != 1:
    raise ValueError(f"Base lattice is not one piece ({len(base.solids())} solids)")

# --- end trestles ----------------------------------------------------------
stand = base
stand += end_trestle(x_led0, x_led1, g + led_stop_height)
stand += end_trestle(x_prt0, x_prt1, g + port_stop_height)

# --- side legs (bear on solid parts of the drive only) ---------------------
smooth = side_leg_profile(y0, -1)
fin = side_leg_profile(y1, +1)
stand += on_yz(smooth, x_led0, smooth_leg)
stand += on_yz(smooth, L - smooth_leg, x_prt1)
if block_end == "port":
    stand += on_yz(fin, x_led0, fin_edge)
    stand += on_yz(fin, L - block_length + 2, x_prt1)
else:
    stand += on_yz(fin, x_led0, block_length - 2)
    stand += on_yz(fin, L - fin_edge, x_prt1)

# --- rails under the solid body and the smooth-side lip --------------------
ra = (rail_inset[0], rail_inset[0] + rail)
rb = (body - rail_inset[1] - rail, body - rail_inset[1])
for r in (ra, rb):
    stand += lattice_wall(x_led1, x_prt0, r[0], r[1], g)
stand += lattice_wall(smooth_leg, L - smooth_leg, y0 - lip, y0, g + lip_height, chamfer_side=+1)

stand = stand.clean()

# --- the drive stand-in (for checks and previews only; not printed) --------
drive = Pos(0, 0, g) * Box(L, body, H, align=(Align.MIN,) * 3)
drive += Pos(*( (L - block_length, body, g) if block_end == "port" else (0, body, g) )) * Box(block_length, fin_height, H, align=(Align.MIN,) * 3)
fin_pitch, fin_t = 3.0, 1.2
x = fin_x0
fins = []
while x + fin_t <= fin_x1:
    fins.append(Pos(x, body, g) * Box(fin_t, fin_height, H, align=(Align.MIN,) * 3))
    x += fin_pitch
drive += Compound(fins)
edge_strip = (0, fin_edge) if block_end == "port" else (L - fin_edge, L)
drive += Pos(edge_strip[0], body, g) * Box(fin_edge, fin_height, H, align=(Align.MIN,) * 3)
feet = [Pos(fx, 0, g + foot_up) * (Rotation(90, 0, 0) * Cylinder(foot_diameter / 2, foot_height, align=(Align.CENTER, Align.CENTER, Align.MIN)))
        for fx in (foot_inset, L - foot_inset)]
drive += Compound(feet)

def ivol(a, b):
    r = a & b
    return 0.0 if r is None else r.volume


# --- checks ----------------------------------------------------------------
clash = ivol(stand, drive)
if clash > 1e-6:
    raise ValueError(f"Stand clashes with the drive stand-in ({clash:.3f} mm^3)")
# Fin air channel: from the top of the base plate up through and above the fins.
# The base lattice below it (z 0..base_thick) is intended.
fin_column = Pos(fin_x0, body, base_thick) * Box(fin_x1 - fin_x0, fin_height, g + H + 50, align=(Align.MIN,) * 3)
blocked = ivol(stand, fin_column)
if blocked > 1e-6:
    raise ValueError(f"Stand obstructs the fin channels ({blocked:.3f} mm^3)")
for fx in (foot_inset, L - foot_inset):
    if abs(fx - (smooth_leg if fx < L / 2 else L - smooth_leg)) < foot_diameter / 2 + 1:
        raise ValueError("A smooth-side leg runs into a rubber foot")
if g + lip_height > g + foot_up - foot_diameter / 2 - 1:
    raise ValueError("Smooth-side lip reaches a rubber foot")
if rail_inset[0] < corner_radius or rail_inset[1] < 0:
    raise ValueError("Rail sits on the drive's rounded edge")

bb = stand.bounding_box()
cx, cy = (bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2
to_bed = Pos(bed_size / 2 - cx, bed_size / 2 - cy, -bb.min.Z)
stand_bed = to_bed * stand
drive_bed = to_bed * drive
bbb = stand_bed.bounding_box()
if bbb.min.X < 0 or bbb.min.Y < 0 or bbb.max.X > bed_size or bbb.max.Y > bed_size:
    raise ValueError("Stand is off the bed")

export_stl(stand_bed, "express-1m2-stand.stl", tolerance=0.02, angular_tolerance=0.08)
export_step(stand_bed, "express-1m2-stand.step")
if not args.no_standin:
    export_stl(drive_bed, "express-1m2-standin.stl", tolerance=0.05, angular_tolerance=0.2)

z_cg = g + H / 2
vol = stand.volume
print(f"stand {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm; slot {y1 - y0:.1f} mm wide; "
      f"drive {L} x {H} x {T} (body {body:.1f} + fins {fin_height}); gap {g}; uprights {upright_height} up the face; "
      f"fin channels x {fin_x0:.1f}..{fin_x1:.1f} clear from the base plate up; "
      f"tip angle sideways ~{math.degrees(math.atan2(base_width / 2, z_cg)):.0f} deg (CoG {z_cg:.1f} mm up); "
      f"{vol / 1000:.1f} cm^3 (~{vol / 1000 * pla:.0f} g PLA); solids {len(stand.solids())}, valid {stand.is_valid}")

if not args.no_preview:
    try:
        from ocp_vscode import show
        show(stand, drive)
    except ImportError:
        pass
