# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Nominal tail, and the mate rebuilt from the measurement log.

The section frame matches oracle_expect: slide along +Z, depth along +Y,
shoulder on Y = 0. Positive flank angle widens the tip. The female
flank is the male flank offset by the designed normal clearance. This
module does not import the referent; the STEP round-trip is what checks
the offset.
"""

from __future__ import annotations

import math
from pathlib import Path

import sympy as sp
from build123d import Polygon, export_step, export_stl, extrude

import log as logmod

MATE_FEATURES = ("tail.flank_angle", "tail.width_recovery")


def _f(value) -> float:
    return float(value)


def spec_from_log(part_log: logmod.Log, citations: dict | None = None) -> dict:
    bound = logmod.require(part_log, MATE_FEATURES, citations)
    angle = bound["tail.flank_angle"]
    if angle.unit != "deg":
        raise logmod.LogError("flank angle must be in degrees")
    recovery = bound["tail.width_recovery"]
    neck = part_log.design_mm("neck") + logmod.to_mm(recovery.exact, recovery.unit)
    return {
        "angle_deg": angle.exact,
        "neck_mm": neck,
        "depth_mm": part_log.design_mm("depth"),
        "length_mm": part_log.design_mm("length"),
        "shoulder_mm": part_log.design_mm("shoulder"),
        "base_mm": part_log.design_mm("base"),
        "wall_mm": part_log.design_mm("wall"),
        "floor_mm": part_log.design_mm("floor"),
        "clearance_mm": part_log.design_mm("flank_clearance"),
        "tip_gap_mm": part_log.design_mm("tip_clearance"),
    }


def build_pair(spec: dict):
    """Male tail and female socket. `angle_deg` is the signed flank angle.

    Callers that already passed the log use spec_from_log. A planted
    mutant calls this directly with a nominal or a negated angle.
    """
    alpha = math.radians(_f(spec["angle_deg"]))
    neck = _f(spec["neck_mm"])
    depth = _f(spec["depth_mm"])
    length = _f(spec["length_mm"])
    shoulder = _f(spec["shoulder_mm"])
    base = _f(spec["base_mm"])
    wall = _f(spec["wall_mm"])
    floor = _f(spec["floor_mm"])
    clearance = _f(spec["clearance_mm"])
    tip_gap = _f(spec["tip_gap_mm"])
    if neck <= 0 or depth <= 0 or length <= 0 or clearance < 0 or tip_gap < 0:
        raise ValueError("dovetail sizes must be positive")

    tan_a = math.tan(alpha)
    cos_a = math.cos(alpha)
    if cos_a <= 0:
        raise ValueError("flank angle must stay inside (-90, 90) degrees")
    half = neck / 2
    tip_half = half + depth * tan_a
    if tip_half <= 0:
        raise ValueError("tip collapsed through the centerline")

    male_pts = [
        (-half - shoulder, -base),
        (half + shoulder, -base),
        (half + shoulder, 0),
        (half, 0),
        (tip_half, depth),
        (-tip_half, depth),
        (-half, 0),
        (-half - shoulder, 0),
    ]
    male = extrude(Polygon(*male_pts), length)
    if male.volume <= 0 or not male.is_valid:
        raise RuntimeError("male dovetail is not a valid solid")

    # Offset along the outward normal (cos α, -sin α) widens each
    # y-section by clearance/cos α per side. The plane gap stays `clearance`.
    y_floor = depth + tip_gap
    side = clearance / cos_a
    mouth = half + side
    floor_half = half + y_floor * tan_a + side
    block_half = max(mouth, abs(floor_half)) + wall
    block_top = y_floor + floor
    cavity = [(-mouth, 0), (mouth, 0), (floor_half, y_floor), (-floor_half, y_floor)]
    block = [(-block_half, 0), (block_half, 0), (block_half, block_top), (-block_half, block_top)]
    female = extrude(Polygon(*block), length) - extrude(Polygon(*cavity), length)
    if female.volume <= 0 or not female.is_valid:
        raise RuntimeError("female dovetail is not a valid solid")
    return male, female


def export_mate(part_log: logmod.Log, directory: Path | str, citations: dict | None = None) -> dict:
    """Write the mated pair. Refuses before any file is written."""
    spec = spec_from_log(part_log, citations)
    male, female = build_pair(spec)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "male_step": directory / "male.step",
        "female_step": directory / "female.step",
        "male_stl": directory / "male.stl",
        "female_stl": directory / "female.stl",
    }
    export_step(male, paths["male_step"])
    export_step(female, paths["female_step"])
    export_stl(male, paths["male_stl"])
    export_stl(female, paths["female_stl"])
    paths["spec"] = {key: str(value) if isinstance(value, sp.Expr) else value for key, value in spec.items()}
    return paths
