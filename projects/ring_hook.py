# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Ring hook — flat profile with top ring, tapered neck, and semicircular base."""

from build123d import *

from ring_hook_profile import base_cutout, neck_triangle, outer_boundary, ring_hole

THICKNESS = 2.5


def extrude_profile(draw):
    with BuildPart() as part:
        with BuildSketch():
            draw()
        extrude(amount=THICKNESS)
    return part.part


outer = extrude_profile(lambda: Polygon(outer_boundary()))
ring_hole_solid = Pos(0, 0, 0) * extrude_profile(lambda: Polygon(ring_hole()))
triangle = extrude_profile(lambda: Polygon(neck_triangle()))
base_cutout_solid = extrude_profile(lambda: Polygon(base_cutout()))

result = outer - ring_hole_solid - triangle - base_cutout_solid

export_stl(result, "ring-hook.stl")
export_step(result, "ring-hook.step")

try:
    from ocp_vscode import Camera, show

    show(Rot(0, 0, 180) * result, reset_camera=Camera.RESET)
except ImportError:
    pass
