# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Triton lifter — a pair of involute bevel gears with hex / round sockets.

Port of ``triton-lifter.scad``, which calls ``bevel_gear`` from the vendored
``gears.scad`` (Dr Jörg Janssen's involute gear library) twice.  The tooth
flanks are spherical involutes, built here as the same polyhedra the library
emits: a quadrilateral cross-section swept over 16 steps of the polar angle
from the base cone to the tip cone, plus a root wedge between the root cone
and the base cone.
"""

from math import acos, asin, atan, cos, degrees, radians, sin, sqrt, tan

from build123d import *

# --- degree-based trigonometry, matching OpenSCAD ---------------------------


def _sin(a):
    return sin(radians(a))


def _cos(a):
    return cos(radians(a))


def _tan(a):
    return tan(radians(a))


def _asin(x):
    return degrees(asin(x))


def _acos(x):
    return degrees(acos(x))


def _atan(x):
    return degrees(atan(x))


def sphere_ev(theta0, theta):
    """gears.scad: azimuth angle of a spherical involute."""
    return 1 / _sin(theta0) * _acos(_cos(theta) / _cos(theta0)) - _acos(
        _tan(theta0) / _tan(theta)
    )


def sphere_to_cartesian(radius, theta, phi):
    """gears.scad: theta = angle to z-axis, phi = angle to x-axis in xy."""
    return (
        radius * _sin(theta) * _cos(phi),
        radius * _sin(theta) * _sin(phi),
        radius * _cos(theta),
    )


CLEARANCE = 0.05  # gears.scad: clearance between teeth

# Triangulation of the 8-point polyhedra emitted by gears.scad.
_POLY_FACES = [
    [0, 1, 2], [0, 2, 3], [0, 4, 1], [1, 4, 5], [1, 5, 2], [2, 5, 6],
    [2, 6, 3], [3, 6, 7], [0, 3, 7], [0, 7, 4], [4, 6, 5], [4, 7, 6],
]
_CAP_LOW = [[0, 1, 2], [0, 2, 3]]      # faces 0-1 of a polyhedron
_CAP_HIGH = [[0, 2, 1], [0, 3, 2]]     # faces 4-6-5 / 4-7-6, re-indexed
_SIDES = [
    [0, 4, 1], [1, 4, 5], [1, 5, 2], [2, 5, 6],
    [2, 6, 3], [3, 6, 7], [0, 3, 7], [0, 7, 4],
]


def _tri(a, b, c):
    return Face(Polyline(a, b, c, close=True).wire())


def _solid(points, faces):
    return Solid(Shell([_tri(*(points[i] for i in f)) for f in faces]))


def bevel_gear(modul, tooth_number, partial_cone_angle, tooth_width, bore,
               pressure_angle=20, helix_angle=0):
    """Port of the ``bevel_gear`` module in gears.scad (line ~732)."""
    d_outside = modul * tooth_number
    r_outside = d_outside / 2
    rg_outside = r_outside / _sin(partial_cone_angle)
    rg_inside = rg_outside - tooth_width
    alpha_spur = _atan(_tan(pressure_angle) / _cos(helix_angle))
    delta_b = _asin(_cos(alpha_spur) * _sin(partial_cone_angle))
    da_outside = (
        d_outside + (modul * 2.2) * _cos(partial_cone_angle)
        if modul < 1
        else d_outside + modul * 2 * _cos(partial_cone_angle)
    )
    ra_outside = da_outside / 2
    delta_a = _asin(ra_outside / rg_outside)
    c = modul / 6
    df_outside = d_outside - (modul + c) * 2 * _cos(partial_cone_angle)
    rf_outside = df_outside / 2
    delta_f = _asin(rf_outside / rg_outside)
    rkf = rg_outside * _sin(delta_f)
    height_f = rg_outside * _cos(delta_f)

    # Complementary truncated cone.
    height_k = (rg_outside - tooth_width) / _cos(partial_cone_angle)
    rk = (rg_outside - tooth_width) / _sin(partial_cone_angle)
    rfk = rk * height_k * _tan(delta_f) / (rk + height_k * _tan(delta_f))
    height_fk = rk * height_k / (height_k * _tan(delta_f) + rk)

    phi_r = sphere_ev(delta_b, partial_cone_angle)

    gamma_g = 2 * _atan(
        tooth_width * _tan(helix_angle) / (2 * rg_outside - tooth_width)
    )
    gamma = 2 * _asin(rg_outside / r_outside * _sin(gamma_g / 2))

    step = (delta_a - delta_b) / 16
    tau = 360 / tooth_number
    start = delta_b if delta_b > delta_f else delta_f
    mirrpoint = (180 * (1 - CLEARANCE)) / tooth_number + 2 * phi_r

    # The teeth sit inside translate([0,0,height_f]) rotate([0,180,0]); the
    # truncated cone carries that transform twice, which cancels to identity.
    def tooth_frame(p):
        return (-p[0], p[1], height_f - p[2])

    def section(delta, flankpoint):
        return [
            sphere_to_cartesian(rg_outside, delta, flankpoint),
            sphere_to_cartesian(rg_inside, delta, flankpoint + gamma),
            sphere_to_cartesian(rg_inside, delta, mirrpoint - flankpoint + gamma),
            sphere_to_cartesian(rg_outside, delta, mirrpoint - flankpoint),
        ]

    # --- one tooth (root wedge + swept involute flanks), rot = 0 ------------
    parts = []

    if delta_b > delta_f:
        # Tooth root: constant full width, 1 permille overlap with the tooth.
        pts = section(start * 1.001, mirrpoint) + section(delta_f, mirrpoint)
        parts.append(_solid([tooth_frame(p) for p in pts], _POLY_FACES))

    # Tooth: OpenSCAD's `for (delta = [start : step : delta_a - step])`.
    n_steps = int((delta_a - step - start) / step + 1e-9) + 1
    deltas = [start + i * step for i in range(n_steps + 1)]
    sections = [
        [tooth_frame(p) for p in section(d, sphere_ev(delta_b, d))]
        for d in deltas
    ]

    faces = [_tri(*(sections[0][i] for i in f)) for f in _CAP_LOW]
    faces += [_tri(*(sections[-1][i] for i in f)) for f in _CAP_HIGH]
    for lo, hi in zip(sections, sections[1:]):
        ring = lo + hi
        faces += [_tri(*(ring[i] for i in f)) for f in _SIDES]
    parts.append(Solid(Shell(faces)))

    tooth = parts[0].fuse(*parts[1:]) if len(parts) > 1 else parts[0]
    teeth = [Rot(Z=tau * n) * tooth for n in range(tooth_number)]

    # --- truncated cone body, bored ----------------------------------------
    body = loft(
        [
            Plane.XY * Circle(rkf * 1.001),
            Plane.XY.offset(height_f - height_fk) * Circle(rkf * 1.001 * rfk / rkf),
        ],
        ruled=True,
    )
    body -= Pos(0, 0, -1) * Cylinder(
        radius=bore / 2,
        height=height_f - height_fk + 2,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    gear = body.solid().fuse(*teeth).clean()
    # Centre a tooth on the x-axis, as gears.scad does.
    return Rot(Z=phi_r + 90 * (1 - CLEARANCE) / tooth_number) * gear


# --- triton-lifter.scad -----------------------------------------------------

m = 3 / 2       # modulus
w = 20 / 2      # tooth width
b = 0.5 / 2     # bore

gear = bevel_gear(
    modul=m,
    tooth_number=20,
    partial_cone_angle=45,
    tooth_width=w,
    bore=b,
)

MOUNT = Pos(0, 0, -2.7) * Cylinder(
    radius=14.95 / 2, height=3, align=(Align.CENTER, Align.CENTER, Align.MIN)
)

blank = (gear + MOUNT).solid()

hex_socket = Pos(0, 0, -3) * extrude(
    Plane.XY * RegularPolygon(radius=(10 * (2 / sqrt(3)) - 0.2) / 2, side_count=6),
    amount=24,
)
round_socket = Pos(0, 0, -3) * Cylinder(
    radius=(10 + 0.4) / 2, height=24, align=(Align.CENTER, Align.CENTER, Align.MIN)
)

result = Compound(
    children=[
        (blank - hex_socket).solid(),
        Pos(3.5 * w, 0, 0) * (blank - round_socket).solid(),
    ]
)

export_stl(result, "triton-lifter.stl")
export_step(result, "triton-lifter.step")

try:
    from ocp_vscode import show
    show(result)
except ImportError:
    pass
