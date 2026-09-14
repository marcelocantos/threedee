# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Nailgun tip — tapered trapezium adapter with internal cavity and slot."""

from build123d import *

# Parameters
W1 = 5      # Bottom width
W2 = 8.5    # Top width
D = 8.5     # Depth
H = 5       # Height
Txy = 1.5   # Wall thickness (XY)
Tz1 = 1.2   # Floor thickness
Tz2 = 1.7   # Ceiling thickness

S1 = 3      # Slot depth
S2 = 2      # Slot height


def trapezium(w1: float, w2: float, d: float, h: float) -> Part:
    """Extrude a trapezoidal cross-section."""
    pts = [
        (w1 / 2, -d / 2),
        (w2 / 2, d / 2),
        (-w2 / 2, d / 2),
        (-w1 / 2, -d / 2),
    ]
    with BuildPart() as p:
        with BuildSketch():
            Polygon(pts)
        extrude(amount=h)
    return p.part


# Outer shell
outer = trapezium(W1, W2, D, H)

# Inner cavity
inner = Pos(0, Txy / 2, Tz1) * trapezium(W1 - 2 * Txy, W2 - 2 * Txy, D, H - Tz1 - Tz2)

# Upper cutout (cavity clipped to upper region only)
upper_cavity = Pos(0, Txy / 2, 2 + Tz1) * trapezium(W1 - 2 * Txy, W2 - 2 * Txy, D, H - Tz1 - Tz2)
clip_box = Pos(-5, -10, -5 + 2 + Tz1) * Box(
    10, 10, 10, align=(Align.MIN, Align.MIN, Align.MIN)
)
upper_cut = upper_cavity - clip_box

# Side slot
slot = Pos(0, 1, H / 2) * Box(10, S1, S2)

result = outer - inner - upper_cut - slot

export_stl(result, "nailgun-tip.stl")
export_step(result, "nailgun-tip.step")

try:
    from ocp_vscode import show
    show(result)
except ImportError:
    pass
