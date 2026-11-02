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
from math import pi, sqrt, tan

from build123d import *

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
clearance = 0.5         # Gap per side between the white top's edge and the wall
v_clearance = 1.0       # Gap between the scale's top and the shelf underside
protrusion = 5          # How far the pushed-in scale sticks out past the rail fronts
min_bearing = 3.5       # Least lip overlap under the base the build accepts
lip_width = 15          # Lip reach from the wall's inner face, under the base
lip_thickness = 3
gusset = 5              # 45 degree fillet in the wall-lip corner, clear of the taper
wall = 11               # Thick side wall carrying the screws
lead_in = 1.5           # Front chamfer on the lip top and gusset, which meet the base's bevel
side_lead_in = 3        # Front chamfer on the wall's inner face, where the scale's sides enter
lip_nose = 1.5          # Rounds the top edge of each lip's front chamfer into a nose
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
screw_count = 3         # Per rail
screw_inset = 20        # First and last hole from the rail's open length ends

# Carve-outs (mm).
boss_wall = 4           # Solid wall around each counterbore, along the rail
skin = 2                # Outer skin beside the pockets
inner_skin = 2          # Strip along the inner face; guides the white top's edge
boss_skin = 1.5         # Least wall either side of a counterbore
end_wall = 4            # Solid ends: behind the lead-in, and in front of the back wall
min_pocket = 6          # Shortest stretch worth pocketing
bed_size = 256          # Bambu X1 Carbon printable width and depth
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
screw_x = -wall / 2
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
if wall / 2 - cb_r < boss_skin:
    raise ValueError("Wall is too thin for the counterbore")
if wall - skin - inner_skin < 4:
    raise ValueError("Wall is too thin to pocket")
if back_height < height - slot_h + 5 or back_height > height:
    raise ValueError("Back wall must rise at least 5 mm above the lips, and not past the shelf")
# Bed placement: centred across, and pushed back off-centre if needed so the
# part's hull clears the excluded corner. The footprint is a full rectangle,
# so its convex hull is its bounding box.
x_margin = (bed_size - outer) / 2
y_front = (bed_size - length) / 2
if x_margin < exclude_x + exclude_margin:
    y_front = max(y_front, exclude_y + exclude_margin)
y_back = bed_size - length - y_front
margin = min(x_margin, y_front, y_back)
if margin < min_margin:
    raise ValueError(f"Part leaves only {margin:.1f} mm of bed margin")
if x_margin < exclude_x + exclude_margin and y_front < exclude_y + exclude_margin:
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
pitch = (length - back_thickness - 2 * screw_inset) / (screw_count - 1)
holes = [screw_inset + i * pitch for i in range(screw_count)]
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
    """The lip chamfer's top edge: a line across the lip top at y = lead_in."""
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
    out = set()
    for e, fs in faces.items():
        p = e @ 0.5
        if len(fs) == 2 and fs[0].normal_at(p).dot(fs[1].normal_at(p)) < 0.999:
            out.add(e)
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

# Print plate: the right way up, placed on the bed as worked out above.
box = cradle.bounding_box()
plate = Pos(x_margin - box.min.X, y_front - box.min.Y, -box.min.Z) * cradle

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

export_stl(plate, "scale-rails-plate.stl")
export_step(plate, "scale-rails-plate.step")
export_step(assembly, "scale-rails-assembly.step")
export_stl(cradle, "scale-rails-installed.stl")
export_stl(scale, "scale-ghost.stl")

print(f"cradle {outer} x {length} x {height} mm; on the bed x {x_margin:g}..{x_margin + outer:g}, "
      f"y {y_front:g}..{y_front + length:g} (margins {x_margin:g} sides, {y_front:g} front, {y_back:g} back; "
      f"clear of the {exclude_x} x {exclude_y} mm excluded corner); "
      f"lip {bearing:.1f} mm under the base; scale top {v_clearance} mm below the shelf; "
      f"scale out {protrusion} mm; screws at y = {', '.join(f'{y:g}' for y in holes)} mm; "
      f"rounding {edge_radius} mm, lip nose {lip_nose} mm; "
      f"{cradle.volume:.0f} mm^3 ({solid_volume:.0f} before carve-outs)")
for note in unrounded:
    print(f"left sharp (each side): {note}")

if not args.no_preview:
    try:
        from ocp_vscode import show
        show(assembly)
    except ImportError:
        pass
