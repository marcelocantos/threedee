# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Measure a dovetail by reading the STEP solid back, not the generator.

Angles come from face normals of the reimported solid. Gaps are
distances between those planes. The builder's parameter record is not
an input.
"""

from __future__ import annotations

import math
from pathlib import Path

from build123d import import_step, import_stl

# Tighter than the 0.01° / 0.05 mm acceptance. The STEP round-trip of
# these planar faces lands well inside either ceiling.
ANGLE_TOL_DEG = 1e-4
MM_TOL = 1e-4
STL_TOL_MM = 0.05

_MATE_KEYS = (
    "male_angle_deg",
    "female_angle_deg",
    "flank_gap_mm",
    "tip_gap_mm",
    "datum_gap_mm",
    "male_neck_mm",
    "male_tip_mm",
    "female_mouth_mm",
)


def _only_solid(shape):
    found = list(shape.solids())
    if len(found) != 1:
        raise RuntimeError(f"expected one solid, found {len(found)}")
    return found[0]


def _unit(normal):
    mag = math.hypot(normal.X, normal.Y, normal.Z)
    if mag == 0:
        raise RuntimeError("zero-length face normal")
    return normal.X / mag, normal.Y / mag, normal.Z / mag


def _plane_gap(normal, origin, point) -> float:
    nx, ny, nz = _unit(normal)
    return abs(nx * (point.X - origin.X) + ny * (point.Y - origin.Y) + nz * (point.Z - origin.Z))


def _flank_faces(solid):
    found = []
    for face in solid.faces():
        normal = face.normal_at()
        if abs(normal.Z) > 1e-5 or abs(normal.X) < 0.05 or abs(normal.Y) < 0.05:
            continue
        found.append(face)
    return found


def _right_flank(solid):
    rights = [face for face in _flank_faces(solid) if face.center().X > 0]
    if len(rights) != 1:
        raise RuntimeError(f"expected one right flank, found {len(rights)}")
    return rights[0]


def _signed_male(face) -> float:
    normal = face.normal_at()
    nx, ny = normal.X, normal.Y
    if nx < 0:
        nx, ny = -nx, -ny
    return math.degrees(math.atan2(-ny, nx))


def _signed_female(face) -> float:
    normal = face.normal_at()
    nx, ny = normal.X, normal.Y
    # The socket's outward normal points into the cavity, so the right
    # flank has a negative X component when the angle is positive.
    if nx > 0:
        nx, ny = -nx, -ny
    return math.degrees(math.atan2(ny, -nx))


def _horizontal(solid, ny_sign: float):
    found = []
    for face in solid.faces():
        normal = face.normal_at()
        if abs(normal.Z) > 1e-5 or abs(normal.X) > 1e-4:
            continue
        if normal.Y * ny_sign <= 0.5:
            continue
        found.append(face)
    if not found:
        raise RuntimeError("no horizontal face")
    return found


def _span_x(face) -> tuple[float, float]:
    """X of the flank edge at the shoulder (min Y) and at the tip (max Y)."""
    vertices = list(face.vertices())
    if len(vertices) < 2:
        raise RuntimeError("flank has no vertices")
    root = min(vertices, key=lambda vertex: vertex.Y)
    tip = max(vertices, key=lambda vertex: vertex.Y)
    return root.X, tip.X


def _section_xy(solid) -> list[list[float]]:
    ends = []
    for face in solid.faces():
        normal = face.normal_at()
        if normal.Z < -0.9:
            ends.append(face)
    if not ends:
        return []
    end = min(ends, key=lambda face: face.center().Z)
    points = []
    for edge in end.outer_wire().edges():
        start = edge.position_at(0)
        points.append([start.X, start.Y])
    return points


def measure_mate(male_step: Path | str, female_step: Path | str) -> dict:
    male = _only_solid(import_step(male_step))
    female = _only_solid(import_step(female_step))
    male_flank = _right_flank(male)
    female_flank = _right_flank(female)
    male_root_x, male_tip_x = _span_x(male_flank)
    female_root_x, _female_tip_x = _span_x(female_flank)

    male_shoulders = _horizontal(male, +1)
    female_mouths = _horizontal(female, -1)
    shoulder = min(male_shoulders, key=lambda face: abs(face.center().Y))
    mouth = min(female_mouths, key=lambda face: abs(face.center().Y))
    male_tip_face = max(male_shoulders, key=lambda face: face.center().Y)
    floor = max(female_mouths, key=lambda face: face.center().Y)

    male_box = male_flank.bounding_box()
    female_box = female_flank.bounding_box()
    overlap = min(male_box.max.Y, female_box.max.Y) - max(male_box.min.Y, female_box.min.Y)

    return {
        "male_angle_deg": _signed_male(male_flank),
        "female_angle_deg": _signed_female(female_flank),
        "flank_gap_mm": _plane_gap(male_flank.normal_at(), male_flank.center(), female_flank.center()),
        "tip_gap_mm": _plane_gap(male_tip_face.normal_at(), male_tip_face.center(), floor.center()),
        "datum_gap_mm": _plane_gap(shoulder.normal_at(), shoulder.center(), mouth.center()),
        "male_neck_mm": 2 * male_root_x,
        "male_tip_mm": 2 * male_tip_x,
        "female_mouth_mm": 2 * female_root_x,
        "flank_overlap_mm": overlap,
        "section_xy": _section_xy(male),
    }


def _bbox_size(shape) -> tuple[float, float, float]:
    box = shape.bounding_box()
    return box.size.X, box.size.Y, box.size.Z


def measure_gauge(step_path: Path | str, stl_path: Path | str) -> dict:
    solid = _only_solid(import_step(step_path))
    mesh = import_stl(stl_path)
    step_size = _bbox_size(solid)
    stl_size = _bbox_size(mesh)
    return {
        "step_mm": step_size,
        "stl_mm": stl_size,
        "step_thickness_mm": step_size[2],
        "stl_thickness_mm": stl_size[2],
    }


def mesh_agrees(step_path: Path | str, stl_path: Path | str) -> list[str]:
    """The STL extent matches the reimported STEP solid."""
    solid = _only_solid(import_step(step_path))
    mesh = import_stl(stl_path)
    step_size = _bbox_size(solid)
    stl_size = _bbox_size(mesh)
    problems = []
    for axis, step_mm, stl_mm in zip("xyz", step_size, stl_size):
        if abs(step_mm - stl_mm) > STL_TOL_MM:
            problems.append(f"stl {axis} {stl_mm} disagrees with step {step_mm}")
    return problems


def judge_mate(measurement: dict, expected: dict) -> list[str]:
    problems = []
    for key in _MATE_KEYS:
        got = measurement[key]
        want = expected[key]
        tol = ANGLE_TOL_DEG if key.endswith("_deg") else MM_TOL
        if abs(got - want) > tol:
            problems.append(f"{key}: measured {got:.6f} expected {want:.6f}")
    if measurement["flank_overlap_mm"] <= 0:
        problems.append("flank faces do not overlap along the depth")
    if measurement["male_angle_deg"] <= 0 or measurement["female_angle_deg"] <= 0:
        problems.append("flank angle does not lock; the tip is not wider than the neck")
    return problems


def judge_gauge(measurement: dict, thickness_mm: float, length_mm: float, width_mm: float) -> list[str]:
    problems = []
    for label, size in (("step", measurement["step_mm"]), ("stl", measurement["stl_mm"])):
        tol = MM_TOL if label == "step" else STL_TOL_MM
        for axis, got, want in zip("xyz", size, (length_mm, width_mm, thickness_mm)):
            if abs(got - want) > tol:
                problems.append(f"gauge {label} {axis}: measured {got:.6f} expected {want:.6f}")
    # The label is the nominal. Shipping that thickness is the failure.
    if abs(measurement["stl_thickness_mm"] - thickness_mm) > STL_TOL_MM:
        problems.append("stl thickness is not the calibration")
    return problems
