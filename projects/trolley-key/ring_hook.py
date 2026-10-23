# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Ring hook — flat tab with a ring, tapered stem and semicircular foot.

2D profile built from circles and straight lines only, extruded to a
thin plate for export. Dimensions measured from a photo against a ruler.
"""

import argparse
from math import acos, atan2, cos, hypot, sin
import struct

from build123d import *

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--plate", action="store_true", help="Export ten keys on an X1 Carbon plate")
parser.add_argument("--no-preview", action="store_true", help="Export without opening the CAD viewer")
args = parser.parse_args()

# Parameters (mm). y = 0 is the flat top of the semicircular foot.
ring_r = 6.75       # Ring outer radius
hole_r = 4.25       # Ring hole radius
ring_y = 28         # Ring centre height above the foot flat
foot_r = 10         # Foot semicircle radius (centred on the flat)
d_r = 7.5           # D cutout radius, concentric with the foot
d_flat = 2.2        # D cutout flat, below the foot flat
stem_hw = 3.4       # Stem half-width where it meets the foot flat
shoulder_r = 4.5    # Concave fillet between stem and foot flat (5 leaves no room for foot_corner_r)
foot_corner_r = 1   # Rounding where the foot arc meets the flat
tri_top = 21        # Triangular cutout: top edge height
tri_hw = 3.0        # Triangular cutout: half-width at the top
tri_apex = 0.5      # Triangular cutout: apex height
thickness = 3       # Plate thickness for export
hole_round = 1      # Rounding on the ring hole's top and bottom edges
corner_round = 1    # Rounding on the triangle and crescent cutout corners
cutout_fillet = 0.5 # Fillet on the triangle and crescent top and bottom edges
outer_fillet = 0.5  # Fillet on the outer top and bottom edges, except the foot arc

# Stem: lines from the foot corners (±stem_hw, 0) tangent to the ring.
d = hypot(stem_hw, ring_y)
a = atan2(-ring_y, -stem_hw) - acos(ring_r / d)  # left tangent point angle
tx, ty = ring_r * cos(a), ring_y + ring_r * sin(a)
stem = Polygon((-stem_hw, 0), (stem_hw, 0), (-tx, ty), (tx, ty), align=None)  # CCW

ring = Pos(0, ring_y) * Circle(ring_r)
foot = Circle(foot_r) & Rectangle(2 * foot_r, foot_r, align=(Align.CENTER, Align.MAX))

outline = ring + stem + foot
shoulders = (
    outline.vertices()
    .filter_by_position(Axis.Y, 0, 0)
    .filter_by_position(Axis.X, -stem_hw, stem_hw)
)
outline = fillet(shoulders, shoulder_r)
foot_corners = [v for v in outline.vertices() if abs(v.Y) < 1e-6 and abs(abs(v.X) - foot_r) < 1e-6]
outline = fillet(foot_corners, foot_corner_r)

hole = Pos(0, ring_y) * Circle(hole_r)
tri = Polygon((0, tri_apex), (tri_hw, tri_top), (-tri_hw, tri_top), align=None)  # CCW
dcut = Circle(d_r) & Pos(0, -d_flat) * Rectangle(2 * d_r, d_r, align=(Align.CENTER, Align.MAX))
tri = fillet(tri.vertices(), corner_round)
dcut = fillet(dcut.vertices(), corner_round)

profile = outline - hole - tri - dcut
result = extrude(profile, thickness)
hole_edges = [e for e in result.edges().filter_by(GeomType.CIRCLE) if abs(e.radius - hole_r) < 1e-6]
result = fillet(hole_edges, hole_round)

# Top and bottom edges of the triangle and crescent: horizontal edges whose
# midpoint projects onto a cutout boundary.
cutouts = tri + dcut
cutout_edges = [
    e for e in result.edges()
    if abs((e @ 0).Z - (e @ 1).Z) < 1e-9
    and cutouts.distance_to(Vector((e @ 0.5).X, (e @ 0.5).Y, 0)) < 1e-6
]
result = fillet(cutout_edges, cutout_fillet)

# Outer contour top and bottom edges, except the foot's semicircular arc.
outer = outline.faces()[0].outer_wire()
outer_edges = [
    e for e in result.edges()
    if abs((e @ 0).Z - (e @ 1).Z) < 1e-9
    and outer.distance_to(Vector((e @ 0.5).X, (e @ 0.5).Y, 0)) < 1e-6
    and not (e.geom_type == GeomType.CIRCLE and abs(e.radius - foot_r) < 1e-6)
]
result = fillet(outer_edges, outer_fillet)

export_stl(result, "ring-hook.stl")
export_step(result, "ring-hook.step")

if args.plate:
    columns, rows = 5, 2
    gap = 5  # Minimum gap between neighbouring bounding boxes, in mm.
    bed_size = 256  # X1 Carbon printable width and depth, in mm.
    bounds = result.bounding_box()
    pitch_x, pitch_y = bounds.size.X + gap, bounds.size.Y + gap
    plate_width = columns * pitch_x - gap
    plate_depth = rows * pitch_y - gap
    if max(plate_width, plate_depth) > bed_size:
        raise ValueError("Ten-key layout exceeds the X1 Carbon bed")
    start_x = (bed_size - plate_width) / 2 - bounds.min.X
    start_y = (bed_size - plate_depth) / 2 - bounds.min.Y
    offsets = [
        (start_x + col * pitch_x, start_y + row * pitch_y, -bounds.min.Z)
        for row in range(rows)
        for col in range(columns)
    ]
    result = Compound(children=[Pos(*offset) * result for offset in offsets])
    export_step(result, "trolley-key-10.step")

    # Translate the original triangles rather than remeshing the copied CAD
    # solids, so every printable copy preserves the accepted single-key mesh.
    with open("ring-hook.stl", "rb") as source:
        header = source.read(80)
        triangle_count = struct.unpack("<I", source.read(4))[0]
        triangles = source.read()
    with open("trolley-key-10.stl", "wb") as output:
        output.write(header)
        output.write(struct.pack("<I", triangle_count * len(offsets)))
        for offset in offsets:
            for triangle in struct.iter_unpack("<12fH", triangles):
                moved = list(triangle)
                for vertex in range(3):
                    for axis in range(3):
                        moved[3 + vertex * 3 + axis] += offset[axis]
                output.write(struct.pack("<12fH", *moved))

if not args.no_preview:
    try:
        from ocp_vscode import show
        show(result)
    except ImportError:
        pass
