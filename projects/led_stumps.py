# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""LED stumps — array of cylindrical spacers with center holes."""

from build123d import *

# Parameters
outer_d = 10
inner_d = 4.5
height = 20
spacing = 12

# Single stump
stump = Cylinder(radius=outer_d / 2, height=height) - Cylinder(radius=inner_d / 2, height=height)

# Grid: 2 columns x 7 rows (matching original: i=0, j=0..1, k=0..6)
result = Compound(children=[
    Pos(j * spacing, k * spacing, 0) * stump
    for j in range(2)
    for k in range(7)
])

export_stl(result, "led-stumps.stl")
export_step(result, "led-stumps.step")
