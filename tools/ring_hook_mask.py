#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Adaptive blue mask, morph close, and small inner-corner symmetry tweak."""

from __future__ import annotations

import cv2
import numpy as np

from blue_hue_filter import blue_hue_grayscale

MIN_HOLE_AREA = 5000


def symmetrize_triangle_corner(mask: np.ndarray, *, y0: int = 810, y1: int = 930) -> np.ndarray:
    """Nudge the left inner neck edge to mirror the right (photo shadow asymmetry)."""
    out = mask.copy()
    ys, xs = np.where(out > 0)
    if len(xs) == 0:
        return out
    cx = int(round((xs.min() + xs.max()) / 2))
    for y in range(y0, y1):
        row = out[y] > 0
        left_band = range(max(0, cx - 220), cx)
        right_band = range(cx, min(out.shape[1], cx + 220))
        left_in = max((x for x in left_band if row[x]), default=None)
        right_in = min((x for x in right_band if row[x]), default=None)
        if left_in is None or right_in is None:
            continue
        target_left = int(round(2 * cx - right_in))
        if target_left > left_in:
            out[y, left_in + 1 : target_left + 1] = 255
    return out


def widget_mask(rgb: np.ndarray, *, fix_corner: bool = True) -> np.ndarray:
    closed = cv2.morphologyEx(blue_hue_grayscale(rgb), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=1)
    if fix_corner:
        closed = symmetrize_triangle_corner(closed)
    return closed


def extract_loops(mask: np.ndarray) -> list[np.ndarray]:
    """Return [outer, ring hole, triangle, base slot] contours."""
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise RuntimeError("no contours in mask")
    outer_i = int(np.argmax([cv2.contourArea(c) for c in contours]))
    outer = contours[outer_i]
    holes: list[np.ndarray] = []
    if hierarchy is not None:
        child = hierarchy[0][outer_i][2]
        while child >= 0:
            c = contours[child]
            if cv2.contourArea(c) >= MIN_HOLE_AREA:
                holes.append(c)
            child = hierarchy[0][child][0]
    holes.sort(key=lambda c: cv2.moments(c)["m01"] / cv2.moments(c)["m00"])
    if len(holes) != 3:
        raise RuntimeError(f"expected 3 holes, got {len(holes)}")
    return [outer, *holes]
