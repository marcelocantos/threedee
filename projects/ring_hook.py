# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Ring hook — flat tab with a ring, tapered stem and semicircular foot.

2D profile built from circles and straight lines only, extruded to a
thin plate for export. Dimensions measured from a photo against a ruler.
"""

from math import acos, atan2, cos, hypot, sin

from build123d import *

# Parameters (mm). y = 0 is the flat top of the semicircular foot.
ring_r = 6.75       # Ring outer radius
hole_r = 4.25       # Ring hole radius
ring_y = 28         # Ring centre height above the foot flat
foot_r = 10         # Foot semicircle radius (centred on the flat)
d_r = 7.5           # D cutout radius, concentric with the foot
d_flat = 2.2        # D cutout flat, below the foot flat
stem_hw = 3.4       # Stem half-width where it meets the foot flat
shoulder_r = 5      # Concave fillet between stem and foot flat
tri_top = 21        # Triangular cutout: top edge height
tri_hw = 3.0        # Triangular cutout: half-width at the top
tri_apex = 0.5      # Triangular cutout: apex height
thickness = 3       # Plate thickness for export

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

hole = Pos(0, ring_y) * Circle(hole_r)
tri = Polygon((0, tri_apex), (tri_hw, tri_top), (-tri_hw, tri_top), align=None)  # CCW
dcut = Circle(d_r) & Pos(0, -d_flat) * Rectangle(2 * d_r, d_r, align=(Align.CENTER, Align.MAX))

profile = outline - hole - tri - dcut
result = extrude(profile, thickness)

export_stl(result, "ring-hook.stl")
export_step(result, "ring-hook.step")

try:
    from ocp_vscode import show
    show(result)
except ImportError:
    pass
