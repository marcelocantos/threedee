# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Puzzle tray: a shallow base that holds a 3 x 3 wooden picture-cube puzzle
(Hape, 45.1 mm cubes) in place of its cardboard box.

A single square pocket holds the nine cubes pressed against one another,
with a little play overall so they lift out without binding. The outer
walls rise to a fraction of the cube height and roll over into the top with
a large rounding; every other outside edge gets a small one. The pocket's
vertical corners have round reliefs cut outward into the wall, so the cubes'
corners never ride on a fillet, and its floor meets the walls square so the
cubes sit flat.

The middle of each outer wall has a vertical channel, cut by a cylinder
standing just outside the wall, so a thumb and forefinger can pinch across a
corner (channels on two adjacent walls). The channel flanks turn past the
45-degree pinch line so the pinch hooks the fingers (checked below). The
channels run the full height, open at the top and the bottom, and their
edges are rounded into the wall.

When hollow_walls is on, each wall holds sealed internal cavities with a
peaked roof so they print without supports, leaving a skin of
skin_thickness everywhere. Behind each channel the wall is too thin for a
cavity and stays solid. The corners and the floor stay solid. It prints the
right way up on its flat bottom with no supports. A separate modifier STL
covers the channels for fuzzy skin in the slicer.
"""

import argparse
import sys
from pathlib import Path

from build123d import *

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_part  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--no-preview", action="store_true", help="Export without opening the CAD viewer")
parser.add_argument("--solid", action="store_true", help="Force solid walls (override hollow_walls)")
args = parser.parse_args()

# Puzzle (mm).
cube = 45.1             # Cube size, measured
grid = 3                # Cubes per side
play = 1.6              # Total slack across the pocket (0.8 mm a side; v4 had 0.6 and fitted tight)

# Tray (mm).
wall_fraction = 0.4     # Wall height above the pocket floor, as a fraction of the cube
wall = 8                # Wall thickness (7 without the grip channels)
floor = 2               # Floor thickness
top_round = 5           # Outer top edges and outer vertical corners
edge_round = 1          # Every other outside edge
relief = 1.5            # Radius of the round reliefs in the pocket's corners

# Grip channels in the middle of the outer walls.
grips = True
grip_walls = "+x -x +y -y"  # Which walls get one
grip_width = 20         # Chord across the channel at the wall face (before blending)
grip_depth = 5          # Depth into the wall at the middle (gives R12.5 with a 20 mm chord)
grip_blend = 1.5        # Rounding where the channel meets the wall
min_hook = 4            # Required hook angle beyond the pinch line (degrees), checked below
min_wall_left = 2.5     # Wall kept between the channel and the pocket

# Hollow walls: sealed cavities with a peaked roof (prints support-free).
hollow_walls = True     # Toggle; --solid on the command line forces this off
skin_thickness = 1.2    # Skin left around each cavity (3 perimeters at 0.4 mm)
corner_solid = 14       # Solid length retained at each end of a wall cavity (mm)
min_cavity = 1.5        # Narrowest cavity kept behind a grip; narrower slivers are filled solid
grip_clearance = 0.15   # Extra cavity keep-out round each grip, so the edge blend keeps a full skin
top_clearance = 1.05    # Cavity ridge lowered so its outer shoulder stays 1.2 mm inside the top roll-over

# Fuzzy-skin modifier volumes for the grips (exported separately).
modifier_depth = 1.2    # How far the modifier reaches into the wall behind the channel surface
modifier_z0 = 0.4       # Bottom of the modifier (keeps the first layer clean)
modifier_z1 = 15        # Top of the modifier, below the 5 mm top roll-over

bed_size = 256          # Bambu X1 Carbon
exclude_x, exclude_y = 18, 28  # Bambu Studio's excluded front-left corner

if args.solid:
    hollow_walls = False

pocket = grid * cube + play
side = pocket + 2 * wall
depth = cube * wall_fraction
height = floor + depth
s2 = side / 2
h = pocket / 2
grip_radius = ((grip_width / 2) ** 2 + grip_depth ** 2) / (2 * grip_depth)

# Hook check. A finger pinching across a corner bears on the flank of each
# channel nearest the other channel, and pushes along the line between the two
# contact points. The flank normal at polar angle phi (from the wall normal)
# turns furthest towards the other channel where the cylinder meets the edge
# blend: cos(phi_t) = (R - depth + blend) / (R + blend). Past that the blend
# rolls the surface back to the wall face. phi_t must exceed the pinch line's
# angle to the wall normal, or the finger is pushed out of the channel.
import math
hook_edge = math.degrees(math.asin((grip_width / 2) / grip_radius))
hook_angle = math.degrees(math.acos((grip_radius - grip_depth + grip_blend) / (grip_radius + grip_blend)))
_rt = math.radians(hook_angle)
_d = side / 2 + grip_radius - grip_depth
_thumb = (_d - grip_radius * math.cos(_rt), grip_radius * math.sin(_rt))   # on the +x channel, +y flank
_finger = (grip_radius * math.sin(_rt), _d - grip_radius * math.cos(_rt))  # on the +y channel, +x flank
pinch_angle = math.degrees(math.atan2(_finger[1] - _thumb[1], _thumb[0] - _finger[0]))  # from the +x wall normal
if grips and hook_angle < pinch_angle + min_hook:
    raise ValueError(f"Grip hook {hook_angle:.1f} deg is under pinch line {pinch_angle:.1f} + {min_hook} deg")

if grips and wall - grip_depth < min_wall_left:
    raise ValueError(f"Only {wall - grip_depth:.2f} mm of wall left behind the grip channels")
if grips and wall - grip_depth < grip_blend + edge_round:
    raise ValueError("Wall is too thin behind the channel for its blend and the rim round")
if hollow_walls and wall - 2 * skin_thickness < 0.8:
    raise ValueError(f"Wall {wall} mm is too thin for skin_thickness {skin_thickness} mm on both faces")
if hollow_walls and grips and wall - grip_depth < 2 * skin_thickness + 0.4:
    raise ValueError(
        f"Only {wall - grip_depth:.2f} mm behind the grips; need >= {2 * skin_thickness + 0.4:.2f} mm "
        f"for a {skin_thickness} mm skin on both faces"
    )

# Body: a square with rounded corners, rolled over into the top.
body = extrude(RectangleRounded(side, side, top_round), height)
body = fillet(body.edges().group_by(Axis.Z)[-1], top_round)

# Pocket, with the corner reliefs.
pocket_sketch = Rectangle(pocket, pocket)
for x in (-h, h):
    for y in (-h, h):
        pocket_sketch += Pos(x, y) * Circle(relief)
body -= Pos(0, 0, floor) * extrude(pocket_sketch, depth + 1)
rim = [e for e in body.edges()
       if min(v.Z for v in e.vertices()) > floor + 0.5
       and max(abs(v.X) for v in e.vertices()) < h + relief + 1e-3
       and max(abs(v.Y) for v in e.vertices()) < h + relief + 1e-3]
body = fillet(rim, edge_round)

# Grip channels: each cylinder's axis stands outside the wall at its middle.
axes = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}
grip_centres = []
if grips:
    for name in grip_walls.split():
        dx, dy = axes[name]
        d = s2 + grip_radius - grip_depth
        grip_centres.append((dx * d, dy * d))
        body -= Pos(dx * d, dy * d, -1) * Cylinder(grip_radius, height + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))

    def on_channel(e):
        # Every sampled point lies on one channel's cylinder, above the bed.
        pts = [e.position_at(t) for t in (0, 0.25, 0.5, 0.75, 1)]
        if min(p.Z for p in pts) < 1e-3:
            return False
        return any(all(abs(((p.X - cx) ** 2 + (p.Y - cy) ** 2) ** 0.5 - grip_radius) < 1e-3 for p in pts)
                   for cx, cy in grip_centres)

    body = fillet([e for e in body.edges() if on_channel(e)], grip_blend)

# Small rounding round the bottom, following the channels.
bed = [e for e in body.edges()
       if all(abs(v.Z) < 1e-3 for v in e.vertices()) and abs(e.center().Z) < 1e-3]
body = fillet(bed, edge_round)

solid_volume = body.volume

# Hollow the four walls with sealed, peaked cavities. The floor and the
# corner regions stay solid: the floor is only 2 mm (too thin to skin on
# both faces at skin_thickness), and solid corners keep the tray stiff and
# avoid awkward cavity ends in the outer rounds.
if hollow_walls:
    skin = skin_thickness
    z_bot = skin
    z_peak = height - skin - top_clearance
    half_len = h - corner_solid
    if half_len < 10:
        raise ValueError(f"corner_solid {corner_solid} mm leaves only {half_len:.1f} mm of cavity length")

    def peaked_profile(u0, u1, z0, z1):
        """(u, z) polygon for a cavity section with a >=45° peaked roof."""
        width = u1 - u0
        slope_h = width / 2  # 45° from each shoulder to the ridge
        z_shoulder = z1 - slope_h
        if z_shoulder < z0 + 0.2:
            return [(u0, z0), (u1, z0), ((u0 + u1) / 2, z1)]
        return [
            (u0, z0),
            (u1, z0),
            (u1, z_shoulder),
            ((u0 + u1) / 2, z1),
            (u0, z_shoulder),
        ]

    def cavity_along_x(y0, y1, x0, x1):
        # Face in the YZ plane; extrude explicitly along +X so placement is unambiguous.
        pts = [Vector(0, y, z) for y, z in peaked_profile(y0, y1, z_bot, z_peak)]
        return Pos(x0, 0, 0) * extrude(
            Face(Wire.make_polygon(pts, close=True)), x1 - x0, dir=(1, 0, 0)
        )

    def cavity_along_y(x0, x1, y0, y1):
        # Face in the XZ plane; extrude explicitly along +Y (without dir the face
        # normal can point -Y and the cavity lands outside the tray).
        pts = [Vector(x, 0, z) for x, z in peaked_profile(x0, x1, z_bot, z_peak)]
        return Pos(0, y0, 0) * extrude(
            Face(Wire.make_polygon(pts, close=True)), y1 - y0, dir=(0, 1, 0)
        )

    cavity = (
        cavity_along_x(h + skin, s2 - skin, -half_len, half_len)
        + cavity_along_x(-(s2 - skin), -(h + skin), -half_len, half_len)
        + cavity_along_y(h + skin, s2 - skin, -half_len, half_len)
        + cavity_along_y(-(s2 - skin), -(h + skin), -half_len, half_len)
    )
    # Keep at least `skin` of wall behind each grip channel. Where that would
    # leave a cavity narrower than min_cavity (right behind the deepest part),
    # fill the wall solid across a band instead of printing a sliver.
    keep_r = grip_radius + skin + grip_clearance
    inner_face = wall - skin  # cavity's pocket-side boundary, measured in from the outer face
    # Cavity width at offset t along the wall: (R - depth + inner_face) - sqrt(keep_r^2 - t^2)
    reach = grip_radius - grip_depth + inner_face - min_cavity
    band = math.sqrt(max(keep_r ** 2 - reach ** 2, 0.0)) if reach < keep_r else 0.0
    for name, (cx, cy) in zip(grip_walls.split(), grip_centres):
        cavity -= Pos(cx, cy, -1) * Cylinder(
            keep_r, height + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        if band > 0:
            dx, dy = axes[name]
            mid = s2 - wall / 2
            size = (wall + 2, 2 * band, height + 2) if dx else (2 * band, wall + 2, height + 2)
            cavity -= Pos(dx * mid, dy * mid, height / 2) * Box(*size)
    if not cavity.is_valid or len(cavity.solids()) != 8:
        raise ValueError(
            f"Wall cavities invalid: solids={len(cavity.solids())}, valid={cavity.is_valid}"
        )
    for i, s in enumerate(cavity.solids()):
        bb = s.bounding_box()
        # Each cavity must sit inside the tray's wall band, not outside it.
        if bb.min.X < -s2 - 0.1 or bb.max.X > s2 + 0.1 or bb.min.Y < -s2 - 0.1 or bb.max.Y > s2 + 0.1:
            raise ValueError(f"Cavity {i} extends outside the tray: {bb}")
    body -= cavity
    if not body.is_valid or len(body.solids()) != 1:
        raise ValueError(
            f"Hollowing failed: solids={len(body.solids())}, valid={body.is_valid}"
        )
    if len(body.shells()) != 1 + len(cavity.solids()):
        raise ValueError(
            f"Expected 1 outer + {len(cavity.solids())} void shells, got {len(body.shells())}"
        )

tray = Pos(bed_size / 2, bed_size / 2, 0) * body

# Fuzzy-skin modifier: one slim curved slab hugging each grip channel, from
# just above the first layer to below the top roll-over, reaching
# modifier_depth into the wall (well clear of the pocket face) and spanning
# the channel and its blends. Load it in the slicer as a modifier on the tray
# (same coordinates) and set fuzzy skin on it; see the README.
modifier = None
if grips:
    for name, (cx, cy) in zip(grip_walls.split(), grip_centres):
        dx, dy = axes[name]
        ring = Cylinder(grip_radius + modifier_depth, modifier_z1 - modifier_z0,
                        align=(Align.CENTER, Align.CENTER, Align.MIN)) - Cylinder(
            grip_radius - 2, modifier_z1 - modifier_z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        span = grip_width / 2 + grip_blend + 1
        size = (wall + 4, 2 * span, modifier_z1 - modifier_z0) if dx else (2 * span, wall + 4, modifier_z1 - modifier_z0)
        clip = Pos(dx * (s2 - wall / 2) - cx, dy * (s2 - wall / 2) - cy, 0) * Box(*size, align=(Align.CENTER, Align.CENTER, Align.MIN))
        piece = Pos(cx, cy, modifier_z0) * (ring & clip)
        modifier = piece if modifier is None else modifier + piece
    if len(modifier.solids()) != len(grip_centres):
        raise ValueError(f"Grip modifier has {len(modifier.solids())} pieces")
    modifier = Pos(bed_size / 2, bed_size / 2, 0) * modifier

bb = tray.bounding_box()
if bb.min.X < exclude_x + 3 and bb.min.Y < exclude_y + 3:
    raise ValueError("Tray reaches the excluded corner")
if bb.max.X > bed_size or bb.max.Y > bed_size or bb.min.X < 0 or bb.min.Y < 0:
    raise ValueError("Tray is off the bed")

export_part.export_stl(tray, "puzzle-tray.stl", tolerance=0.02, angular_tolerance=0.08)
export_part.export_step(tray, "puzzle-tray.step")
if modifier is not None:
    export_part.export_stl(modifier, "puzzle-tray-grip-modifier.stl", tolerance=0.02, angular_tolerance=0.08)

vol = tray.volume
pla = 1.24  # g/cm^3
hollow_note = (
    f"hollow walls on, skin {skin_thickness} mm, corner solid {corner_solid} mm; "
    f"solid would be {solid_volume / 1000:.1f} cm^3 ({solid_volume / 1000 * pla:.0f} g PLA); "
    f"saved {(solid_volume - vol) / 1000:.1f} cm^3"
    if hollow_walls else "hollow walls off"
)
print(f"tray {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.2f} mm; "
      f"pocket {pocket:.1f} mm square, {depth:.2f} mm deep ({wall_fraction:.0%} of the {cube} mm cubes), "
      f"{play / 2:.2f} mm play a side; wall {wall} mm; "
      f"grip channels {'R%.2f, %g mm wide, %g mm deep, blend %g, %g mm wall left; hook %.1f deg (edge %.1f) vs pinch line %.1f deg' % (grip_radius, grip_width, grip_depth, grip_blend, wall - grip_depth, hook_angle, hook_edge, pinch_angle) if grips else 'off'}; "
      f"{hollow_note}; "
      f"{vol / 1000:.1f} cm^3 (~{vol / 1000 * pla:.0f} g PLA); solids {len(tray.solids())}, valid {tray.is_valid}")

if not args.no_preview:
    export_part.preview(tray)
