# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Thickness gauge. The plate does not export until the log calibrates it.

The labelled step is the nominal. The solid's thickness is the
calibration reading. Length and width stay the nominal plate size.
"""

from __future__ import annotations

from pathlib import Path

import sympy as sp
from build123d import Align, Box, export_step, export_stl

import log as logmod

FEATURE = "blade.thickness"


def spec_from_log(part_log: logmod.Log, citations: dict | None = None) -> dict:
    bound = logmod.require(part_log, (FEATURE,), citations)
    thickness = bound[FEATURE]
    return {
        "thickness_mm": logmod.to_mm(thickness.exact, thickness.unit),
        "length_mm": part_log.design_mm("length"),
        "width_mm": part_log.design_mm("width"),
    }


def build_gauge(spec: dict):
    length = float(spec["length_mm"])
    width = float(spec["width_mm"])
    thickness = float(spec["thickness_mm"])
    if length <= 0 or width <= 0 or thickness <= 0:
        raise ValueError("gauge sizes must be positive")
    plate = Box(length, width, thickness, align=(Align.MIN, Align.MIN, Align.MIN))
    if plate.volume <= 0 or not plate.is_valid:
        raise RuntimeError("gauge is not a valid solid")
    return plate


def export_gauge(part_log: logmod.Log, directory: Path | str, citations: dict | None = None) -> dict:
    spec = spec_from_log(part_log, citations)
    plate = build_gauge(spec)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "step": directory / "gauge.step",
        "stl": directory / "gauge.stl",
    }
    export_step(plate, paths["step"])
    export_stl(plate, paths["stl"])
    paths["spec"] = {
        key: str(value) if isinstance(value, sp.Expr) else value for key, value in spec.items()
    }
    return paths
