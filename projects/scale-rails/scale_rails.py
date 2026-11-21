# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Scale rails — a one-piece U-shaped cradle that hangs a flat kitchen scale
(Soehnle, 220 x 220 x 20 mm) under a pantry shelf.

The scale has a thin white top that overhangs a black base whose sides
taper inward toward the bottom. Each side is a thick L-section rail, screwed
up into the shelf, with a wide lip that reaches under the base's bottom edge.
There is no ceiling: the scale's top runs just clear of the shelf itself,
to keep the stack as shallow as possible. A back wall across the full width
joins the two rails at the back and stops the scale with `protrusion` of it
out past the rail fronts, which sit flush with the shelf edge.

Installed frame: x across the shelf (+x towards the scale from the left
rail), y from the shelf front (y = 0) towards the back, z up, with z = 0 at
the shelf underside. The part prints the right way up, standing on the
bottom faces of its lips, walls and back wall: the lips lie on the bed, the
walls and back wall rise straight up and every cavity opens upwards, so
nothing overhangs and no supports are needed.

To lighten the thick walls, each stretch between the screw bosses has a
pocket open on the shelf face (straight up in the print, so it needs no
roof). The outer skin, a strip along the inner face that guides the white
top, the floor over the lip root, the bosses with their shelf faces, the
front ends behind the lead-in and the back wall stay solid.
"""

import argparse
import sys
from pathlib import Path
from math import pi, sqrt, tan

from build123d import *

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_part  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--no-preview", action="store_true", help="Export without opening the CAD viewer")
args = parser.parse_args()

# Scale (mm). Insets are from the white top's edge to the black base's side,
# estimated from a side-on photo at ~3 px/mm; measure to confirm.
scale_width = 220       # Side to side; the rails grip these two edges
scale_depth = 220       # Front to back
scale_thickness = 20    # Overall height, white top to bottom of base
white_thickness = 4     # White top slab
base_inset_top = 6      # Black base side, just under the white top
base_inset_bottom = 10.5  # Black base side, at the bottom face (underside photo)

# Rails (mm).
clearance = 1.0         # Gap per side between the white top's edge and the wall
v_clearance = 1.0       # Gap between the scale's top and the shelf underside
protrusion = 10         # How far the pushed-in scale sticks out past the rail fronts
min_bearing = 3.5       # Least lip overlap under the base the build accepts
lip_width = 15.5        # Lip reach from the wall's inner face, under the base
lip_thickness = 3
gusset = 5              # 45 degree fillet in the wall-lip corner, clear of the taper
wall = 10.5             # Thick side wall carrying the screws
lead_in = 1.5           # Front chamfer on the lip top and gusset, which meet the base's bevel
side_lead_in = 3        # Front chamfer on the wall's inner face, where the scale's sides enter
lip_nose = 1.5          # Rounds the top edge of each lip's front chamfer into a nose
round_lip = True        # Round each lip's front corner in plan, from its tip to the gusset
edge_radius = 1         # Fillet on every edge not lying in the shelf face, bar the screw holes

# Back wall (mm): joins the rails behind the scale and stops it.
back_thickness = 4      # Along the rails
back_height = None      # Up from the bottom face; None runs it up to the shelf

# Screws: up through the wall into the shelf, from below.
screw_d = 3.5           # Wood screw shank (3.5 x 16 mm countersunk)
screw_clear = 0.4       # Shank hole clearance
head_d = 7.0            # Countersunk head diameter (90 degree)
head_clear = 0.6        # Counterbore clearance over the head
seat = 5                # Plastic between the head's top and the shelf
# The holes are already drilled in the shelf, so their positions are fixed
# from the rails' outer faces and fronts, whatever else changes.
screw_from_outer = 5.5  # Hole centre in from the wall's outer face
screw_ys = (20, 107.5, 195)  # Hole centres back from the rail fronts

# Carve-outs (mm).
boss_wall = 4           # Solid wall around each counterbore, along the rail
skin = 2                # Outer skin beside the pockets
inner_skin = 2          # Strip along the inner face; guides the white top's edge
boss_skin = 1.2         # Least wall either side of a counterbore
end_wall = 4            # Solid ends: behind the lead-in, and in front of the back wall
min_pocket = 6          # Shortest stretch worth pocketing
bed_size = 256          # Bambu X1 Carbon printable width and depth

# Stress-relief slots (mm): narrow cuts across each rail's floor (lip, gusset
# and the wall's base under the pockets), from the outer skin to just short
# of the lip's tip, and up through the back wall's foot. They break the long
# runs of solid first layers that ASA's shrinkage curls up. Each rail slot
# leaves the outer skin and a strip along the lip's tip whole, and each back
# wall slot stops below a strut, so the part stays one piece.
slots = True
slot_width = 2          # Across the slot
slot_tip = 3            # Lip left whole at its tip, beyond the slot's end
slot_round = 0.5        # Rounds the slot's edges, bar those on the bed
back_slots = True       # Slots up through the back wall's foot, under its struts
back_slot_h = 8         # Back wall slot height from the bed, to its pointed top

# Lattice (mm): diamond openings with 45 degree sides through the side walls
# between the screw bosses and through the back wall, so their tops print
# without supports. Solid bands stay along the shelf face and the bottom, and
# round the bosses, the lips and the back corners.
lattice = True
lattice_top = 3.5       # Solid band under the shelf face
lattice_floor = 1.5     # Solid above the pockets' floor, in the side walls
lattice_strut = 3       # Least strut between openings, at its waist
lattice_end = 2         # Least solid between an opening and the boss beyond a pocket's end
lattice_corner = 1      # Rounds the diamonds' points
lattice_round = 1       # Rounds the openings' edges on the walls' outer and inner faces
back_lattice = True
back_bottom = 4         # Solid band along the back wall's foot
back_solid = 15         # Solid back wall beyond each lip's tip

# Brim (mm): a thin pad on the bed around each rail's open front end and
# its back corner, to hold them down against curling. A thin strip next to
# the part, one layer thick, lets the pad snap or peel off along the part's
# edge after printing. The installed model has none. brim_thickness 0 leaves
# it off.
brim_thickness = 0.4    # Two 0.2 mm layers
brim_front = 8          # Ahead of the rail front
brim_out = 3            # Past the wall's outer face (the bed is tight across)
brim_in = 8             # Past the lip's tip, towards the middle
brim_back = 40          # Back along the rail from its front
brim_radius = 3         # Corner rounding
brim_layer = 0.2        # Thickness of the strip next to the part, to snap along
brim_hinge = 1.5        # Width of that thin strip
brim_rear = 6           # Behind the back wall (the bed is tight along)
brim_along = 30         # Along the back wall from the wall's inner face
min_margin = 3          # Least bed margin around the part the build accepts
# Bambu Studio's X1 Carbon bed_exclude_area (front-left corner, where the
# filament cutter trips). Studio warns if the part's convex hull touches it.
exclude_x = 18
exclude_y = 28
exclude_margin = 3      # Least gap between the part's hull and the excluded corner

slot_h = scale_thickness + v_clearance
height = slot_h + lip_thickness
lip_top = -slot_h
length = scale_depth - protrusion + back_thickness
screw_x = -wall + screw_from_outer
span = scale_width + 2 * clearance          # Between the walls' inner faces
outer = span + 2 * wall                     # Across the outer walls
if back_height is None:
    back_height = height

# Base side at the bottom, measured from the wall's inner face.
base_edge = clearance + base_inset_bottom
bearing = lip_width - base_edge
if bearing < min_bearing:
    raise ValueError(f"Lip reaches only {bearing:.1f} mm under the base")
# The gusset's hypotenuse must stay clear of the tapered base side.
taper = (base_inset_bottom - base_inset_top) / (scale_thickness - white_thickness)
gusset_gap = min(base_edge - taper * d - (gusset - d) for d in (0, gusset))
if gusset_gap < 1:
    raise ValueError("Gusset fouls the tapered base")
cb_r = (head_d + head_clear) / 2
if min(screw_from_outer, wall - screw_from_outer) - cb_r < boss_skin:
    raise ValueError("Wall is too thin for the counterbore")
if wall - skin - inner_skin < 4:
    raise ValueError("Wall is too thin to pocket")
if back_height < height - slot_h + 5 or back_height > height:
    raise ValueError("Back wall must rise at least 5 mm above the lips, and not past the shelf")
# Bed placement: the part lies turned a quarter turn, its open front ends
# towards the bed's right, so the brims ahead of them get the bed's spare
# depth. Its footprint across the bed is then the rails' outer width plus
# the side brims; along the bed, the length plus the front brims. It is
# centred, pushed right if needed so its hull (a rectangle) clears the
# excluded corner.
brim_on = brim_thickness > 0
foot_x = length + (brim_front + brim_rear if brim_on else 0)
foot_y = outer + (2 * brim_out if brim_on else 0)
y_front = (bed_size - foot_y) / 2         # Bed margin front and back
x_left = (bed_size - foot_x) / 2
if y_front < exclude_y + exclude_margin:
    x_left = max(x_left, exclude_x + exclude_margin)
x_right = bed_size - foot_x - x_left
margin = min(y_front, x_left, x_right)
if margin < min_margin:
    raise ValueError(f"Part leaves only {margin:.1f} mm of bed margin")
if y_front < exclude_y + exclude_margin and x_left < exclude_x + exclude_margin:
    raise ValueError("Part is too close to the bed's excluded corner")

corner = (Align.MIN, Align.MIN, Align.MIN)

# Left rail: wall inner face at x = 0, white top's edge at x = clearance.
def near(a, b):
    return abs(a - b) < 1e-3


profile = Polygon(
    (-wall, -height),
    (lip_width, -height),
    (lip_width, lip_top),
    (gusset, lip_top),
    (0, lip_top + gusset),
    (0, 0),
    (-wall, 0),
    align=None,
)  # CCW in the XZ plane seen from -y
# The gusset's foot is rounded here rather than with the other edges, as
# OCCT won't blend it in 3D where it runs into the lip nose.
foot = [v for v in profile.vertices() if near(v.X, gusset) and near(v.Y, lip_top)]  # Sketch y is installed z
if edge_radius > 0:
    profile = fillet(foot, edge_radius)
rail = extrude(Plane.XZ * profile, -length)

# Rounded lip corner: seen from below, each lip's front corner is a quarter
# circle running from the lip's tip forward to where the gusset's foot blend
# starts, so the lip's front shrinks to the wall and gusset alone.
foot_x = gusset + (edge_radius * tan(pi / 8) if edge_radius > 0 else 0)
corner_r = lip_width - foot_x
if round_lip:
    c = (lip_width - corner_r, corner_r)
    rail -= Pos(c[0], -1, -height - 1) * Box(corner_r + 1, corner_r + 1, lip_thickness + 1, align=corner) \
        - Pos(c[0], c[1], -height - 2) * Cylinder(corner_r, lip_thickness + 3, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Lead-in: 45 degree chamfers on the slot's edges at the open front end,
# lead_in on the lip top and gusset (they meet the base's bevel) and the
# larger side_lead_in on the wall's inner face, where the scale's sides
# enter. Chamfers keep these faces planar, so the rounding below can blend
# them cleanly.
def front_edges(part, test):
    return [e for e in part.edges() if all(near(v.Y, 0) for v in e.vertices()) and test(e)]


rail = chamfer(front_edges(rail, lambda e: all(near(v.X, 0) for v in e.vertices())), side_lead_in)
rail = chamfer(front_edges(rail, lambda e: near(e.center().Z, lip_top) and e.center().X > 0
                           or near(e.center().X + e.center().Z, gusset + lip_top) and e.center().X > 0), lead_in)

# Screw holes: shank to the shelf, 90 degree countersink, then a counterbore
# down to the bottom face. The hole axes stand upright in the print, and the
# countersink narrows upwards at 45 degrees, so no hole needs a roof.
shank_r = (screw_d + screw_clear) / 2
head_r = head_d / 2
sink_h = head_r - shank_r
cb_h = height - seat - sink_h
holes = list(screw_ys)
if holes[-1] + cb_r + boss_skin > length - back_thickness:
    raise ValueError("Back screw hole runs into the back wall")
for y in holes:
    at = Pos(screw_x, y, -height)
    rail -= at * Cylinder(shank_r, height, align=(Align.CENTER, Align.CENTER, Align.MIN))
    rail -= at * Cylinder(cb_r, cb_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    rail -= at * Pos(0, 0, cb_h) * Cone(head_r, shank_r, sink_h, align=(Align.CENTER, Align.CENTER, Align.MIN))

solid_rail = rail

# Pockets between the bosses and the solid ends, open on the shelf face and
# floored level with the top of the gusset.
boss_half = cb_r + boss_wall
edges = [max(lead_in, side_lead_in) + end_wall]
for y in holes:
    edges += [y - boss_half, y + boss_half]
edges.append(length - back_thickness - end_wall)
bays = [(a, b) for a, b in zip(edges[::2], edges[1::2]) if b - a >= min_pocket]
pocket_z = lip_top + gusset
for a, b in bays:
    rail -= Pos(-wall + skin, a, pocket_z) * Box(wall - skin - inner_skin, b - a, -pocket_z, align=corner)


def half(r):
    """A left rail with the left half of the back wall."""
    back = Pos(-wall, length - back_thickness, -height) * Box(outer / 2, back_thickness, back_height, align=corner)
    return r + back


def pair(h):
    """Join a half cradle with its mirror image about the middle."""
    return h + Pos(span, 0, 0) * mirror(h, Plane.YZ)


solid_volume = pair(half(solid_rail)).volume


# Rounding, done on the half cradle so both sides come out the same. The
# edges lying in the shelf face stay sharp, as do the screw holes and the cut
# down the middle of the back wall; everything else is filleted, including
# the edges on the bed and the vertical corners that meet the shelf face only
# at a point. The top edge of each lip's front chamfer gets lip_nose first,
# giving a rounded nose that still meets the base's bevel. The rest get
# edge_radius in two passes: the corners on the wall's inner face run down
# into the gusset's blends, which OCCT only manages once those exist, so
# they go second. The bed edges come last so that they blend around the
# rounded vertical corners. Anything OCCT still refuses is retried on its own
# and, failing that, left sharp and listed.
nose_setback = lip_nose * tan(pi / 8)     # How far the nose fillet eats into its faces
edge_setback = edge_radius * tan(pi / 8)  # The same for a 135 degree edge_radius fillet
if nose_setback + edge_setback >= lead_in * sqrt(2):
    raise ValueError("Lip nose fillets overlap on the lip chamfer")
if edge_setback + edge_radius >= lip_thickness - lead_in:
    raise ValueError("Lip chamfer and bed fillets leave no lip front")
if max(edge_radius, lip_nose) > skin:
    raise ValueError("Rounding is larger than the pocket skins")


def hole_edges(part):
    """Edges of the screw holes: the cones, and the cylinders of their radii."""
    return {
        e for f in part.faces()
        if f.geom_type == GeomType.CONE
        or (f.geom_type == GeomType.CYLINDER and any(near(f.radius, r) for r in (shank_r, cb_r)))
        for e in f.edges()
    }


def in_shelf(e):
    return all(near(v.Z, 0) for v in e.vertices()) and near(e.center().Z, 0)


def on_bed(e):
    return all(near(v.Z, -height) for v in e.vertices()) and near(e.center().Z, -height)


def in_middle(e):
    return all(near(v.X, span / 2) for v in e.vertices())


def is_nose(e):
    """The lip chamfer's top edge: a line across the lip top at y = lead_in,
    or with round_lip, the arc round the corner on the lip top."""
    if round_lip:
        return (e.geom_type == GeomType.CIRCLE and e.length > corner_r
                and all(near(v.Z, lip_top) for v in e.vertices()))
    if e.geom_type != GeomType.LINE:
        return False
    a, b = e.vertices()
    return near(a.Y, lead_in) and near(b.Y, lead_in) and near(a.Z, lip_top) and near(b.Z, lip_top)


def creases(part):
    """Edges where the two faces meet at an angle, not tangent blend edges."""
    faces = {}
    for f in part.faces():
        for e in f.edges():
            faces.setdefault(e, []).append(f)
    # Preserve traversal order. Hash order changes the input to OCCT fillets
    # and can change how their surfaces are parameterized for tessellation.
    out = []
    for e, fs in faces.items():
        p = e @ 0.5
        if len(fs) == 2 and fs[0].normal_at(p).dot(fs[1].normal_at(p)) < 0.999:
            out.append(e)
    return out


def to_round(part, test):
    """Creased edges passing test, other than the shelf face, holes and middle."""
    holes = hole_edges(part)
    return [e for e in creases(part)
            if e not in holes and not (in_shelf(e) or in_middle(e)) and test(e)]


def on_inner_face(e):
    """A corner on the wall's inner face that reaches the shelf face."""
    return all(near(v.X, 0) for v in e.vertices()) and any(near(v.Z, 0) for v in e.vertices())


def where(e):
    a, b = e @ 0, e @ 1
    return f"({a.X:.1f}, {a.Y:.1f}, {a.Z:.1f})-({b.X:.1f}, {b.Y:.1f}, {b.Z:.1f})"


def blend(part, edges, size, op, label):
    """Apply op to the edges together, falling back to one at a time."""
    if size <= 0 or not edges:
        return part
    try:
        return op(edges, size)
    except ValueError:
        pass
    ok, skipped = [], []
    for e in sorted(edges, key=lambda e: -e.length):
        try:
            op(ok + [e], size)
            ok.append(e)
        except ValueError:
            skipped.append(e)
    part = op(ok, size) if ok else part
    for old in skipped:
        # Retry on the new shape: the edge's remainder lies on the same line.
        line = Line(old @ 0, old @ 1) if old.geom_type == GeomType.LINE else None
        again = [e for e in part.edges()
                 if line is not None and e.geom_type == GeomType.LINE
                 and all(line.distance_to(e @ t) < 1e-3 for t in (0, 1))]
        try:
            part = op(again, size) if again else part
            done = bool(again)
        except ValueError:
            done = False
        if not done:
            unrounded.append(f"{label} {where(old)} ({old.length:.1f} mm)")
    return part


unrounded = []
cradle = half(rail)
noses = [e for e in cradle.edges() if is_nose(e)]
if len(noses) != 1:
    raise ValueError(f"Found {len(noses)} lip chamfer top edges, not 1")
cradle = blend(cradle, noses, lip_nose, fillet, "lip nose")
cradle = blend(cradle, to_round(cradle, lambda e: not (on_bed(e) or on_inner_face(e))),
               edge_radius, fillet, "edge")
cradle = blend(cradle, to_round(cradle, lambda e: not on_bed(e)), edge_radius, fillet, "edge")
cradle = blend(cradle, to_round(cradle, on_bed), edge_radius, fillet, "bed")
cradle = pair(cradle).clean()
rounded_volume = cradle.volume


# Lattice and slots, cut into the whole rounded cradle.
def both(shape):
    """A left-side shape and its mirror image on the right."""
    return [shape, Pos(span, 0, 0) * mirror(shape, Plane.YZ)]


def diamond(h):
    """A square on its point, h tall and wide, its points rounded."""
    d = Rot(0, 0, 45) * Rectangle(h / sqrt(2), h / sqrt(2))
    return fillet(d.vertices(), lattice_corner) if lattice_corner > 0 else d


def spread(a, b, h):
    """Centres of the most diamonds h wide that fit between a and b."""
    room = b - a - 2 * lattice_end - h
    if room < 0:
        return []
    n = int(room // (h + lattice_strut)) + 1
    if n == 1:
        return [(a + b) / 2]
    return [a + lattice_end + h / 2 + i * room / (n - 1) for i in range(n)]


def inside(e, x=None, y=None, z=None):
    """Whether the edge lies within the given (low, high) ranges."""
    bb = e.bounding_box()
    return all(r is None or (lo.__getattribute__(a) > r[0] - 1e-3 and hi.__getattribute__(a) < r[1] + 1e-3)
               for a, r, lo, hi in (("X", x, bb.min, bb.max), ("Y", y, bb.min, bb.max), ("Z", z, bb.min, bb.max)))


def on_planes(e, axis, values):
    vs = e.vertices()
    return any(all(near(getattr(v, axis), c) for v in vs) for c in values)


# Side walls: one row of diamonds per pocket, through the outer skin, the
# pocket and the inner skin, above the pocket's floor.
side_lo = pocket_z + lattice_floor
side_hi = -lattice_top
side_h = side_hi - side_lo
side_ys = [[y for y in spread(a, b, side_h)] for a, b in bays] if lattice else []
# Back wall: diamonds spaced out from a strut down the middle, stopping
# back_solid short of each lip's tip.
back_top = -height + back_height
back_lo = -height + back_bottom
back_hi = back_top - lattice_top
back_h = back_hi - back_lo
back_pitch = back_h + lattice_strut
back_xs = []
if back_lattice and back_h > 0:
    k = 0
    while span / 2 - back_pitch / 2 - k * back_pitch - back_h / 2 >= lip_width + back_solid:
        back_xs += [span / 2 - back_pitch / 2 - k * back_pitch, span / 2 + back_pitch / 2 + k * back_pitch]
        k += 1
back_xs.sort()
if lattice and side_h <= 4 * lattice_corner:
    raise ValueError("Side walls are too short for the lattice")

openings = []
for ys in side_ys:
    for y in ys:
        openings += both(Plane((-wall - 1, y, (side_lo + side_hi) / 2), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
                         * extrude(diamond(side_h), wall + 2))
for x in back_xs:
    openings.append(Plane((x, length + 1, (back_lo + back_hi) / 2), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
                    * extrude(diamond(back_h), back_thickness + 2))
for o in openings:
    cradle -= o
lattice_edges = []
for ys in side_ys:
    for y in ys:
        lattice_edges += [e for e in cradle.edges()
                          if on_planes(e, "X", (-wall, 0, span, span + wall))
                          and inside(e, y=(y - side_h / 2, y + side_h / 2), z=(side_lo, side_hi))]
for x in back_xs:
    lattice_edges += [e for e in cradle.edges()
                      if on_planes(e, "Y", (length - back_thickness, length))
                      and inside(e, x=(x - back_h / 2, x + back_h / 2), z=(back_lo, back_hi))]
cradle = blend(cradle, lattice_edges, lattice_round, fillet, "lattice")

# Slots. In the rails, one across the floor at each strut between the
# side wall diamonds (or spread through each pocket's length without the
# lattice), from the outer skin to slot_tip short of the lip's tip. The cut
# runs up into the pocket, under the inner skin (a 2 mm bridge) and through
# the gusset, so the floor is cut right through.
if lattice:
    slot_ys = [(a + b) / 2 for ys in side_ys for a, b in zip(ys, ys[1:])]
else:
    slot_ys = [y for a, b in bays for y in spread(a, b, slot_width)]
slot_ys = slot_ys if slots else []
slot_x0 = -wall + skin
slot_x1 = lip_width - slot_tip
cutters = []
for y in slot_ys:
    w = slot_width
    cut = Pos(slot_x0, y - w / 2, -height - 1) * Box(slot_x1 - slot_x0, w, pocket_z + height + 1, align=corner)
    # Clears the pocket floor's rounded corners over the slot.
    cut += Pos(slot_x0, y - w / 2, -height - 1) * Box(wall - skin - inner_skin, w,
                                                    pocket_z + edge_radius + 0.2 + height + 1, align=corner)
    cutters += both(cut)
# In the back wall, one under each strut between the diamonds, with a
# pointed top that prints without supports.
back_slot_xs = [(a + b) / 2 for a, b in zip(back_xs, back_xs[1:])] if slots and back_slots else []
w = slot_width
arch = Polygon((-w / 2, -1), (w / 2, -1), (w / 2, back_slot_h - w / 2), (0, back_slot_h), (-w / 2, back_slot_h - w / 2),
               align=None)
for x in back_slot_xs:
    cutters.append(Plane((x, length + 1, -height), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
                   * extrude(arch, back_thickness + 2))
for c in cutters:
    cradle -= c
slot_edges = []
for y in slot_ys:
    ends = (y - slot_width / 2, y + slot_width / 2)
    slot_edges += [e for e in cradle.edges()
                   if on_planes(e, "Y", ends) and not on_bed(e)
                   and (inside(e, x=(0, lip_width)) or inside(e, x=(span - lip_width, span)))]
    slot_edges += [e for e in cradle.edges()
                   if all(any(near(v.Y, c) for c in ends) for v in e.vertices()) and not on_bed(e)
                   and (inside(e, x=(slot_x1, slot_x1)) or inside(e, x=(span - slot_x1, span - slot_x1)))]
for x in back_slot_xs:
    slot_edges += [e for e in cradle.edges()
                   if on_planes(e, "Y", (length - back_thickness, length)) and not on_bed(e)
                   and inside(e, x=(x - slot_width / 2, x + slot_width / 2), z=(-height, -height + back_slot_h))]
cradle = blend(cradle, list(dict.fromkeys(slot_edges)), slot_round, fillet, "slot")
cradle = cradle.clean()

# The screw holes must not move: the shelf is drilled.
found = sorted({(round(f.axis_of_rotation.position.X, 3), round(f.axis_of_rotation.position.Y, 3))
                for f in cradle.faces()
                if f.geom_type == GeomType.CYLINDER and near(f.radius, shank_r)})
wanted = sorted((round(x, 3), round(y, 3)) for x in (screw_x, span - screw_x) for y in screw_ys)
if found != wanted:
    raise ValueError(f"Screw holes moved: {found} != {wanted}")
if len(cradle.solids()) != 1 or not cradle.is_valid:
    raise ValueError("Cradle is not one valid solid")

# Print plate: the right way up, with a brim pad around each front end,
# turned and placed on the bed as worked out above.
printed = cradle
if brim_on:
    mn = (Align.MIN, Align.MIN)
    sheet = Pos(-wall - brim_out, -brim_front) * RectangleRounded(
        wall + lip_width + brim_out + brim_in, brim_front + brim_back, brim_radius, align=mn)
    # The rail's footprint near the front, as it meets the bed.
    foot = Pos(-wall, 0) * Rectangle(wall + lip_width, brim_back + brim_front, align=mn)
    if round_lip:
        cx = lip_width - corner_r
        foot -= Pos(cx, 0) * Rectangle(corner_r + 1, corner_r, align=mn) \
            - Pos(cx, corner_r) * Circle(corner_r)
    # The back corner: round the rail's back end and along the back wall.
    if brim_rear > 0:
        sheet += Pos(-wall - brim_out, length - brim_back) * RectangleRounded(
            wall + lip_width + brim_out + brim_in, brim_back + brim_rear, brim_radius, align=mn)
        sheet += Pos(-wall - brim_out, length - back_thickness - brim_in) * RectangleRounded(
            wall + brim_out + brim_along, back_thickness + brim_in + brim_rear, brim_radius, align=mn)
        foot += Pos(-wall, length - brim_back - 1) * Rectangle(wall + lip_width, brim_back + 1, align=mn)
        foot += Pos(-wall, length - back_thickness) * Rectangle(wall + brim_along + brim_hinge + 1, back_thickness,
                                                                align=mn)
    thick = sheet - offset(foot, brim_hinge)
    pad = Pos(0, 0, -height) * (extrude(sheet, brim_layer)
                                + Pos(0, 0, brim_layer) * extrude(thick, brim_thickness - brim_layer))
    printed = printed + pad + Pos(span, 0, 0) * mirror(pad, Plane.YZ)
    # Keep the slots open through the pads' thin layer.
    for c in cutters:
        printed -= c - Pos(0, 0, -height + brim_thickness + 0.1) * Box(1000, 1000, 1000, align=(Align.CENTER, Align.CENTER, Align.MIN))
    printed = printed.clean()
turned = Rot(0, 0, 90) * printed   # Rail fronts now face +x
box = turned.bounding_box()
plate = Pos(x_left - box.min.X, y_front - box.min.Y, -box.min.Z) * turned
pb = plate.bounding_box()

# Reference scale, pushed in against the back wall and resting on the lips.
scale_y = length - back_thickness - scale_depth
white = Pos(clearance, scale_y, -v_clearance - white_thickness) * Box(
    scale_width, scale_depth, white_thickness, align=corner
)
inset = base_inset_bottom
base_profile = Polygon(
    (clearance + inset, lip_top),
    (clearance + scale_width - inset, lip_top),
    (clearance + scale_width - base_inset_top, -v_clearance - white_thickness),
    (clearance + base_inset_top, -v_clearance - white_thickness),
    align=None,
)
base = Pos(0, scale_y, 0) * extrude(Plane.XZ * base_profile, -scale_depth)
scale = white + base
assembly = Compound(children=[cradle, scale])

export_part.export_stl(plate, "scale-rails-plate.stl")
export_part.export_step(plate, "scale-rails-plate.step")
export_part.export_step(assembly, "scale-rails-assembly.step")
export_part.export_stl(cradle, "scale-rails-installed.stl")
export_part.export_stl(scale, "scale-ghost.stl")

print(f"cradle {outer} x {length} x {height} mm; plate turned, fronts to the right, with "
      f"{'brims' if brim_on else 'no brim'}; on the bed x {pb.min.X:.1f}..{pb.max.X:.1f}, "
      f"y {pb.min.Y:.1f}..{pb.max.Y:.1f} (clear of the {exclude_x} x {exclude_y} mm excluded corner); "
      f"lip {bearing:.1f} mm under the base; scale top {v_clearance} mm below the shelf; "
      f"scale out {protrusion} mm; screws at y = {', '.join(f'{y:g}' for y in holes)} mm; "
      f"rounding {edge_radius} mm, lip nose {lip_nose} mm; "
      f"{cradle.volume:.0f} mm^3 ({solid_volume:.0f} before carve-outs, {rounded_volume:.0f} before lattice and slots)")
print(f"lattice: {sum(map(len, side_ys))} diamonds {side_h:g} mm tall per side wall "
      f"(per pocket: {', '.join(str(len(ys)) for ys in side_ys)}), {len(back_xs)} {back_h:g} mm tall in the back wall; "
      f"slots: {len(slot_ys)} per rail at y = {', '.join(f'{y:.1f}' for y in slot_ys)}, "
      f"{len(back_slot_xs)} in the back wall at x = {', '.join(f'{x:.1f}' for x in back_slot_xs)}")
print(f"screw holes at {found}; plate {len(plate.solids())} solid, valid {plate.is_valid}")
for note in unrounded:
    print(f"left sharp (each side): {note}")

if not args.no_preview:
    export_part.preview(assembly)
