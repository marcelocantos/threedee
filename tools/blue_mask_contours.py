#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Adaptive blue mask → raw contour edges + fitted geometric objects (step by step)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from math import atan2, cos, pi, sin, sqrt
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blue_hue_filter import DEFAULT_PHOTO, blue_hue_grayscale

OUT = Path(__file__).resolve().parent.parent / "export" / "ring-hook-edges.png"
MIN_AREA = 5000
# Stop stem bottoms slightly above the D cutout flat (image y down).
D_FLAT_BACKOFF = 4.0


def mask_from_photo(rgb: np.ndarray) -> np.ndarray:
    return cv2.morphologyEx(blue_hue_grayscale(rgb), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=1)


def contour_edges(mask: np.ndarray) -> list[np.ndarray]:
    """All significant boundary loops: largest outer, then inner holes by area."""
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise RuntimeError("no contours in mask")
    ranked = sorted(
        ((i, cv2.contourArea(c)) for i, c in enumerate(contours)),
        key=lambda item: item[1],
        reverse=True,
    )
    outer_i = ranked[0][0]
    loops = [contours[outer_i]]
    if hierarchy is not None:
        child = hierarchy[0][outer_i][2]
        holes: list[tuple[int, float]] = []
        while child >= 0:
            a = cv2.contourArea(contours[child])
            if a >= MIN_AREA:
                holes.append((child, a))
            child = hierarchy[0][child][0]
        holes.sort(key=lambda item: item[1], reverse=True)
        loops.extend(contours[i] for i, _ in holes)
    return loops


def fit_line(pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Unit direction and a point on the line."""
    c = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
    d = vt[0]
    d = d / np.linalg.norm(d)
    if d[1] < 0:
        d = -d
    return c, d


def line_intersection(c1: np.ndarray, d1: np.ndarray, c2: np.ndarray, d2: np.ndarray) -> tuple[float, float]:
    t, _ = np.linalg.solve(np.column_stack([d1, -d2]), c2 - c1)
    p = c1 + t * d1
    return float(p[0]), float(p[1])


def project_to_segment(c: np.ndarray, d: np.ndarray, p: np.ndarray, q: np.ndarray) -> tuple[float, float]:
    """Clip infinite line (c,d) to the segment between projections of p and q."""
    tp = float(np.dot(p - c, d))
    tq = float(np.dot(q - c, d))
    t0, t1 = (tp, tq) if tp < tq else (tq, tp)
    a = c + t0 * d
    b = c + t1 * d
    return (float(a[0]), float(a[1])), (float(b[0]), float(b[1]))


def fit_circle(pts: np.ndarray) -> tuple[float, float, float]:
    x, y = pts[:, 0].astype(float), pts[:, 1].astype(float)
    a = np.column_stack([2 * x, 2 * y, np.ones(len(x))])
    b = x * x + y * y
    cx, cy, c = np.linalg.lstsq(a, b, rcond=None)[0]
    r = sqrt(max(c + cx * cx + cy * cy, 1.0))
    return float(cx), float(cy), float(r)


@dataclass
class RingDonut:
    """Top ring: concentric outer and inner circles (image px, y down)."""

    cx: float
    cy: float
    r_outer: float
    r_inner: float

    @classmethod
    def from_loops(cls, outer: np.ndarray, inners: list[np.ndarray]) -> RingDonut:
        if not inners:
            raise RuntimeError("no inner contours for ring hole")
        ring_hole = min(inners, key=lambda c: cv2.moments(c)["m01"] / cv2.moments(c)["m00"])
        hole_pts = ring_hole.reshape(-1, 2).astype(float)
        cx, cy, r_inner = fit_circle(hole_pts)

        outer_pts = outer.reshape(-1, 2).astype(float)
        dist_all = np.hypot(outer_pts[:, 0] - cx, outer_pts[:, 1] - cy)
        # Top cap of the ring only — avoid neck points that inflate the radius.
        band = outer_pts[
            (outer_pts[:, 1] < cy + r_inner * 0.35) & (dist_all > r_inner * 0.98) & (dist_all < r_inner * 1.8)
        ]
        if len(band) < 30:
            band = outer_pts[(outer_pts[:, 1] < cy + r_inner * 0.55) & (dist_all > r_inner * 0.95)]
        radii = np.hypot(band[:, 0] - cx, band[:, 1] - cy)
        r_outer = float(np.median(radii))
        return cls(cx=cx, cy=cy, r_outer=r_outer, r_inner=r_inner)

    def to_json(self) -> dict:
        return {"kind": "ring_donut", **asdict(self)}


def triangle_hole(inners: list[np.ndarray]) -> np.ndarray:
    """Inner loop between ring hole and base slot."""
    return sorted(inners, key=lambda c: cv2.moments(c)["m01"] / cv2.moments(c)["m00"])[1]


def slot_hole(inners: list[np.ndarray]) -> np.ndarray:
    """Bottom D-slot inner loop."""
    return sorted(inners, key=lambda c: cv2.moments(c)["m01"] / cv2.moments(c)["m00"])[2]


def d_flat_y(slot: np.ndarray) -> float:
    return float(slot.reshape(-1, 2)[:, 1].min())


def _angle(cx: float, cy: float, x: float, y: float) -> float:
    return float(atan2(y - cy, x - cx))


def _short_arc_sweep(a0: float, a1: float) -> tuple[float, float]:
    """Return (a_start, a_end) spanning the minor arc between two angles."""
    sweep = (a1 - a0) % (2 * pi)
    if sweep > pi:
        sweep -= 2 * pi
    return a0, a0 + sweep


def _arc_points(cx: float, cy: float, r: float, a0: float, a1: float, n: int = 48) -> list[tuple[float, float]]:
    a0, a1 = _short_arc_sweep(a0, a1)
    if abs(a1 - a0) < 1e-6:
        a1 = a0 + 1e-3
    return [(cx + r * cos(a), cy + r * sin(a)) for a in np.linspace(a0, a1, n)]


def _semicircle_arc(cx: float, cy: float, r: float, n: int = 64) -> list[tuple[float, float]]:
    """Bottom semicircle: left chord end → bottom → right chord end (image y down)."""
    return [
        (cx + r * cos(a), cy - r * sin(a))
        for a in (pi + (2 * pi - pi) * i / n for i in range(n + 1))
    ]


@dataclass
class PartialDonut:
    """Bottom half-ring: flat top chord + outer semicircle (image px, y down)."""

    cx: float
    flat_y: float
    r_outer: float

    @property
    def cy(self) -> float:
        return self.flat_y

    @classmethod
    def from_contours(cls, outer: np.ndarray, ring: RingDonut) -> PartialDonut:
        outer_pts = outer.reshape(-1, 2).astype(float)
        y_lo = ring.cy + ring.r_outer * 0.8
        y_hi = float(np.percentile(outer_pts[:, 1], 97))
        best_y = y_lo
        best_w = 0.0
        for y in np.linspace(y_lo, y_hi, 120):
            x_left = _edge_x_at_y(outer, float(y), ring.cx, side="left")
            x_right = _edge_x_at_y(outer, float(y), ring.cx, side="right")
            if x_left is None or x_right is None:
                continue
            width = x_right - x_left
            if width > best_w:
                best_w = width
                best_y = float(y)
        x_left = _edge_x_at_y(outer, best_y, ring.cx, side="left")
        x_right = _edge_x_at_y(outer, best_y, ring.cx, side="right")
        if x_left is None or x_right is None:
            raise RuntimeError("could not locate base flat chord")
        cx = float((x_left + x_right) / 2)
        flat_y = best_y
        arc_pts = outer_pts[outer_pts[:, 1] > flat_y + 6]
        if len(arc_pts) < 40:
            raise RuntimeError("too few base arc samples")
        cx, flat_y, r_outer = cls._refine_semicircle(cx, flat_y, arc_pts)
        return cls(cx=cx, flat_y=flat_y, r_outer=r_outer)

    @staticmethod
    def _refine_semicircle(
        cx: float, flat_y: float, arc_pts: np.ndarray
    ) -> tuple[float, float, float]:
        """Nudge centre and radius so the arc hugs the outer silhouette."""
        best_err = float("inf")
        best = (cx, flat_y, float(np.median(np.hypot(arc_pts[:, 0] - cx, arc_pts[:, 1] - flat_y))))
        for dcx in np.linspace(-12, 10, 23):
            for dfy in np.linspace(-20, 8, 29):
                ccx = cx + dcx
                cfy = flat_y + dfy
                rs = np.hypot(arc_pts[:, 0] - ccx, arc_pts[:, 1] - cfy)
                r = float(np.median(rs))
                err = float(np.mean(np.abs(rs - r)))
                if err < best_err:
                    best_err = err
                    best = (ccx, cfy, r)
        return best

    def outer_loop(self) -> list[tuple[float, float]]:
        left = (self.cx - self.r_outer, self.flat_y)
        right = (self.cx + self.r_outer, self.flat_y)
        return [left, *_semicircle_arc(self.cx, self.flat_y, self.r_outer)[1:-1], right]

    def to_json(self) -> dict:
        return {
            "kind": "partial_donut",
            "cx": self.cx,
            "flat_y": self.flat_y,
            "r_outer": self.r_outer,
        }


@dataclass
class DCutout:
    """D-shaped base slot: flat top + bottom semicircle concentric with the outer base."""

    cx: float
    cy: float
    r: float
    flat_y: float
    x_left: float
    x_right: float

    @classmethod
    def from_contours(cls, slot: np.ndarray, base: PartialDonut) -> DCutout:
        pts = slot.reshape(-1, 2).astype(float)
        cx, cy = base.cx, base.flat_y
        y_top = float(pts[:, 1].min())
        top = pts[pts[:, 1] < y_top + 12]
        c_top, d_top = fit_line(top)
        if abs(d_top[0]) >= abs(d_top[1]):
            flat_y = float(c_top[1])
        else:
            flat_y = float(np.median(top[:, 1]))
        arc_pts = pts[pts[:, 1] > flat_y + 8]
        if len(arc_pts) < 20:
            raise RuntimeError("too few D-slot arc samples")
        r = float(np.median(np.hypot(arc_pts[:, 0] - cx, arc_pts[:, 1] - cy)))
        dy = flat_y - cy
        if dy >= r:
            raise RuntimeError("D cutout flat sits below circle centre")
        dx = sqrt(r * r - dy * dy)
        return cls(
            cx=cx,
            cy=cy,
            r=r,
            flat_y=flat_y,
            x_left=float(cx - dx),
            x_right=float(cx + dx),
        )

    def _junction_angles(self) -> tuple[float, float]:
        a_left = float(atan2(-(self.flat_y - self.cy), self.x_left - self.cx))
        a_right = float(atan2(-(self.flat_y - self.cy), self.x_right - self.cx))
        return a_left, a_right

    def inner_loop(self, n: int = 48) -> list[tuple[float, float]]:
        """Closed loop: flat top chord + lower circular arc (image y down)."""
        a_left, a_right = self._junction_angles()
        a_start, a_end = _short_arc_sweep(a_left, a_right)
        left = (self.x_left, self.flat_y)
        right = (self.x_right, self.flat_y)
        arc = _arc_points(self.cx, self.cy, self.r, a_start, a_end, n=n)
        return [left, right, *reversed(arc[1:-1])]

    def to_json(self) -> dict:
        return {
            "kind": "d_cutout",
            "cx": self.cx,
            "cy": self.cy,
            "r": self.r,
            "flat_y": self.flat_y,
            "x_left": self.x_left,
            "x_right": self.x_right,
        }


def _stem_outer_edge(stem: AngledRect) -> tuple[np.ndarray, np.ndarray]:
    """Unit direction (top→bottom) and outer-bottom corner on the stem rectangle."""
    outer_top = np.array(stem.corners[0], dtype=float)
    outer_bot = np.array(stem.corners[3], dtype=float)
    d = outer_bot - outer_top
    d = d / np.linalg.norm(d)
    return d, outer_bot


def _line_distance(c: np.ndarray, d: np.ndarray, p: np.ndarray) -> float:
    v = c - p
    return float(abs(v[0] * d[1] - v[1] * d[0]))


def _foot_on_line(p: np.ndarray, d: np.ndarray, c: np.ndarray) -> np.ndarray:
    return p + float(np.dot(c - p, d)) * d


def _line_normal_toward(d: np.ndarray, p: np.ndarray, toward: np.ndarray) -> np.ndarray:
    """Unit normal to line (p, d) pointing toward `toward`."""
    n = np.array([-d[1], d[0]], dtype=float)
    if np.dot(toward - p, n) < 0:
        n = -n
    return n / np.linalg.norm(n)


def _shoulder_exterior_hint(flat_tangent_x: float, flat_y: float, *, side: str) -> np.ndarray:
    """Point just outside the base corner — shoulder centres sit on this side of the stem."""
    eps = 1.0
    x = flat_tangent_x - eps if side == "left" else flat_tangent_x + eps
    return np.array([x, flat_y - eps])


def _shoulder_radius_from_tangents(
    flat_tangent_x: float,
    flat_y: float,
    stem_p: np.ndarray,
    stem_d: np.ndarray,
    *,
    side: str,
) -> float:
    """Radius from tangency to the D flat at flat_tangent_x and the stem outer line."""
    exterior = _shoulder_exterior_hint(flat_tangent_x, flat_y, side=side)
    n = _line_normal_toward(stem_d, stem_p, exterior)
    return (n[0] * (flat_tangent_x - stem_p[0]) + n[1] * (flat_y - stem_p[1])) / (1 + n[1])


def _shoulder_center_from_tangents(flat_tangent_x: float, flat_y: float, r: float) -> np.ndarray:
    """Centre implied by horizontal flat tangency at (flat_tangent_x, flat_y) and radius r."""
    return np.array([flat_tangent_x, flat_y - r])


def _shoulder_contour_band(
    outer: np.ndarray,
    *,
    corner_x: float,
    flat_y: float,
    stem_t: np.ndarray,
    side: str,
    arc: np.ndarray,
) -> np.ndarray:
    """Outer-contour samples along the shoulder fillet (exclude arc endpoints)."""
    y0, y1 = stem_t[1] - 30, flat_y
    if side == "left":
        pts = outer[
            (outer[:, 1] >= y0)
            & (outer[:, 1] <= y1)
            & (outer[:, 0] >= corner_x)
            & (outer[:, 0] <= stem_t[0] + 15)
        ]
    else:
        pts = outer[
            (outer[:, 1] >= y0)
            & (outer[:, 1] <= y1)
            & (outer[:, 0] <= corner_x)
            & (outer[:, 0] >= stem_t[0] - 15)
        ]
    if len(arc) < 3 or len(pts) == 0:
        return pts
    keep: list[np.ndarray] = []
    n = len(arc)
    for p in pts:
        j = int(np.argmin(np.hypot(arc[:, 0] - p[0], arc[:, 1] - p[1])))
        if 0.08 * n < j < 0.92 * n:
            keep.append(p)
    return np.array(keep) if len(keep) >= 20 else pts


def _fit_shoulder_flat_tangent_x(
    base: PartialDonut,
    stem: AngledRect,
    outer: np.ndarray,
    *,
    side: str,
) -> float:
    """Slide flat tangency along the base chord until the arc hugs the outer contour."""
    flat_y = base.flat_y
    d, stem_p = _stem_outer_edge(stem)
    corner_x = base.cx - base.r_outer if side == "left" else base.cx + base.r_outer
    lo, hi = (corner_x, base.cx) if side == "left" else (base.cx, corner_x)
    best_tx = corner_x
    best_err = float("inf")
    for flat_tx in np.linspace(lo, hi, 200):
        r = _shoulder_radius_from_tangents(flat_tx, flat_y, stem_p, d, side=side)
        if r <= 20 or r >= 300:
            continue
        centre = _shoulder_center_from_tangents(flat_tx, flat_y, r)
        stem_t = _foot_on_line(stem_p, d, centre)
        if abs(_line_distance(centre, d, stem_t) - r) > 0.05:
            continue
        cx, cy = float(centre[0]), float(centre[1])
        a_flat = _angle(cx, cy, flat_tx, flat_y)
        a_stem = _angle(cx, cy, float(stem_t[0]), float(stem_t[1]))
        a0, a1 = _short_arc_sweep(a_flat, a_stem)
        arc = np.array(_arc_points(cx, cy, r, a0, a1, n=80))
        band = _shoulder_contour_band(
            outer, corner_x=corner_x, flat_y=flat_y, stem_t=stem_t, side=side, arc=arc
        )
        if len(band) < 25:
            continue
        dists = np.array([np.hypot(arc[:, 0] - p[0], arc[:, 1] - p[1]).min() for p in band])
        err = float(np.median(dists))
        if err < best_err:
            best_err = err
            best_tx = float(flat_tx)
    return best_tx


@dataclass
class ShoulderArc:
    """Circular fillet tangent to the D flat and the stem outer edge."""

    cx: float
    cy: float
    r: float
    a_start: float
    a_end: float
    stem_tangent: tuple[float, float]
    flat_tangent: tuple[float, float]

    def arc_loop(self, n: int = 48) -> list[tuple[float, float]]:
        return _arc_points(self.cx, self.cy, self.r, self.a_start, self.a_end, n=n)

    def verify(self, flat_y: float, stem_d: np.ndarray, *, tol: float = 1e-2) -> None:
        centre = np.array([self.cx, self.cy])
        stem = np.array(self.stem_tangent)
        flat = np.array(self.flat_tangent)
        if abs(self.cy + self.r - flat_y) > tol:
            raise RuntimeError(f"flat tangency off by {abs(self.cy + self.r - flat_y):.4f}px")
        if abs(_line_distance(centre, stem_d, stem) - self.r) > tol:
            raise RuntimeError("stem-line tangency failed")
        if abs(np.linalg.norm(centre - flat) - self.r) > tol:
            raise RuntimeError("flat tangent point not on circle")
        if flat[1] > flat_y + tol or stem[1] > flat_y + tol:
            raise RuntimeError("shoulder tangency points must sit on or above the D flat")

    def to_json(self) -> dict:
        return {
            "kind": "shoulder_arc",
            "cx": self.cx,
            "cy": self.cy,
            "r": self.r,
            "a_start_deg": float(np.degrees(self.a_start)),
            "a_end_deg": float(np.degrees(self.a_end)),
            "stem_tangent": list(self.stem_tangent),
            "flat_tangent": list(self.flat_tangent),
        }


@dataclass
class ShoulderPair:
    left: ShoulderArc
    right: ShoulderArc

    @classmethod
    def from_stems(cls, base: PartialDonut, stems: StemPair, outer: np.ndarray) -> ShoulderPair:
        left = cls._analytic_shoulder(base, stems.left, outer=outer, side="left")
        right = cls._analytic_shoulder(base, stems.right, outer=outer, side="right")
        left.verify(base.flat_y, _stem_outer_edge(stems.left)[0])
        right.verify(base.flat_y, _stem_outer_edge(stems.right)[0])
        return cls(left=left, right=right)

    @staticmethod
    def _analytic_shoulder(
        base: PartialDonut, stem: AngledRect, *, outer: np.ndarray, side: str
    ) -> ShoulderArc:
        """Circle tangent to the D flat and stem outer edge; radius from the outer contour."""
        flat_y = base.flat_y
        d, outer_bot = _stem_outer_edge(stem)
        flat_tangent_x = _fit_shoulder_flat_tangent_x(base, stem, outer, side=side)
        r = _shoulder_radius_from_tangents(flat_tangent_x, flat_y, outer_bot, d, side=side)
        centre = _shoulder_center_from_tangents(flat_tangent_x, flat_y, r)
        cx, cy = float(centre[0]), float(centre[1])
        stem_t = _foot_on_line(outer_bot, d, centre)
        flat_tangent = (flat_tangent_x, flat_y)
        a_corner = _angle(cx, cy, flat_tangent_x, flat_y)
        a_stem = _angle(cx, cy, float(stem_t[0]), float(stem_t[1]))
        a_start, a_end = _short_arc_sweep(a_corner, a_stem)
        return ShoulderArc(
            cx=cx,
            cy=cy,
            r=r,
            a_start=a_start,
            a_end=a_end,
            stem_tangent=(float(stem_t[0]), float(stem_t[1])),
            flat_tangent=flat_tangent,
        )

    def to_json(self) -> dict:
        return {"kind": "shoulder_pair", "left": self.left.to_json(), "right": self.right.to_json()}


def _rect_corners(p_top: np.ndarray, p_bot: np.ndarray, inner_vec: np.ndarray) -> list[tuple[float, float]]:
    outer_vec = -inner_vec
    return [
        tuple(p_top + outer_vec),
        tuple(p_top + inner_vec),
        tuple(p_bot + inner_vec),
        tuple(p_bot + outer_vec),
    ]


def _sample_stem_angle(
    outer: np.ndarray,
    tri: np.ndarray,
    cx: float,
    *,
    side: str,
    y_top: float,
    y_bot: float,
) -> float:
    """Lean from vertical (radians), symmetrised magnitude only."""
    mids: list[tuple[float, float]] = []
    for y in np.linspace(y_top, y_bot, 40):
        xo = _edge_x_at_y(outer, y, cx, side=side)
        xi = _inner_x_at_y(tri, y, cx, side=side)
        if xo is None or xi is None:
            continue
        if abs(xi - xo) < 8:
            continue
        mids.append(((xo + xi) / 2, float(y)))
    if len(mids) < 4:
        raise RuntimeError(f"could not sample {side} stem")
    _, d = fit_line(np.array(mids))
    return float(atan2(abs(d[0]), d[1]))


def _stem_edge_error(
    ring: RingDonut,
    theta: float,
    outer: np.ndarray,
    tri: np.ndarray,
    cx: float,
    *,
    side: str,
    y_top: float,
    y_bot: float,
) -> float:
    """Mean squared x error of tangent stem edges vs contour boundaries."""
    half_w = (ring.r_outer - ring.r_inner) / 2
    d, p = _stem_axes(theta, side=side)
    centre = np.array([ring.cx, ring.cy])
    anchor = centre - ((ring.r_inner + ring.r_outer) / 2) * p
    outer_origin = anchor - half_w * p
    inner_origin = anchor + half_w * p
    err = 0.0
    n = 0
    for y in np.linspace(y_top, y_bot, 36):
        xo = _edge_x_at_y(outer, y, cx, side=side)
        xi = _inner_x_at_y(tri, y, cx, side=side)
        if xo is None or xi is None:
            continue
        s = (y - outer_origin[1]) / d[1]
        if s < 0:
            continue
        x_outer = outer_origin[0] + s * d[0]
        x_inner = inner_origin[0] + s * d[0]
        err += (x_outer - xo) ** 2 + (x_inner - xi) ** 2
        n += 2
    return err / n if n else float("inf")


def _fit_stem_theta(
    ring: RingDonut,
    outer: np.ndarray,
    tri: np.ndarray,
    cx: float,
    *,
    side: str,
    y_top: float,
    y_bot: float,
) -> float:
    """Contour lean, refined so tangent stem edges track outer and void boundaries."""
    seed = _sample_stem_angle(outer, tri, cx, side=side, y_top=y_top, y_bot=y_bot)
    span = 0.10 if side == "left" else 0.06
    thetas = np.linspace(max(0.005, seed - span), seed + span, 120)
    best = seed
    best_err = float("inf")
    for theta in thetas:
        err = _stem_edge_error(
            ring, float(theta), outer, tri, cx, side=side, y_top=y_top, y_bot=y_bot
        )
        if err < best_err:
            best_err = err
            best = float(theta)
    return best


def _stem_axes(theta: float, *, side: str) -> tuple[np.ndarray, np.ndarray]:
    """Unit centreline direction d and inner normal p (toward ring centre)."""
    if side == "left":
        d = np.array([sin(theta), cos(theta)])
        p = np.array([cos(theta), -sin(theta)])
    else:
        d = np.array([-sin(theta), cos(theta)])
        p = np.array([-cos(theta), -sin(theta)])
    return d, p


def _analytic_stem(ring: RingDonut, theta: float, flat_y: float, *, side: str) -> AngledRect:
    """Rectangle with both long edges tangent to the ring inner and outer circles."""
    centre = np.array([ring.cx, ring.cy])
    half_w = (ring.r_outer - ring.r_inner) / 2
    d, p = _stem_axes(theta, side=side)
    # Unique centreline through the ring annulus midline; top corners sit on the circles.
    anchor = centre - ((ring.r_inner + ring.r_outer) / 2) * p
    bottom_y = flat_y - D_FLAT_BACKOFF
    t_bot = (bottom_y - anchor[1] - half_w * sin(theta)) / d[1]
    p_top = anchor
    p_bot = anchor + t_bot * d
    inner_vec = half_w * p
    corners = _rect_corners(p_top, p_bot, inner_vec)
    angle = float(np.degrees(atan2(d[1], d[0])))
    length = float(np.linalg.norm(p_bot - p_top))
    return AngledRect(corners=corners, width=half_w * 2, length=length, angle_deg=angle)


def _edge_x_at_y(contour: np.ndarray, y: float, cx: float, *, side: str, margin: float = 3.0) -> float | None:
    pts = contour.reshape(-1, 2).astype(float)
    band = pts[np.abs(pts[:, 1] - y) < margin]
    if side == "left":
        half = band[band[:, 0] < cx - 2]
        return float(half[:, 0].min()) if len(half) else None
    if side == "right":
        half = band[band[:, 0] > cx + 2]
        return float(half[:, 0].max()) if len(half) else None
    raise ValueError(side)


def _inner_x_at_y(tri: np.ndarray, y: float, cx: float, *, side: str, margin: float = 3.0) -> float | None:
    pts = tri.reshape(-1, 2).astype(float)
    band = pts[np.abs(pts[:, 1] - y) < margin]
    if side == "left":
        half = band[(band[:, 0] < cx - 2) & (band[:, 0] > cx - 200)]
        return float(half[:, 0].max()) if len(half) else None
    half = band[(band[:, 0] > cx + 2) & (band[:, 0] < cx + 200)]
    return float(half[:, 0].min()) if len(half) else None


@dataclass
class AngledRect:
    """Rectangle on a slight angle (4 corners, clockwise)."""

    corners: list[tuple[float, float]]
    width: float
    length: float
    angle_deg: float

    def to_json(self) -> dict:
        return {
            "kind": "angled_rect",
            "corners": self.corners,
            "width": self.width,
            "length": self.length,
            "angle_deg": self.angle_deg,
        }


@dataclass
class StemPair:
    left: AngledRect
    right: AngledRect

    @classmethod
    def from_contours(
        cls, outer: np.ndarray, tri: np.ndarray, ring: RingDonut, flat_y: float
    ) -> StemPair:
        cx = ring.cx
        tri_pts = tri.reshape(-1, 2).astype(float)
        y_top = float(tri_pts[:, 1].min())
        y_bot = float(tri_pts[:, 1].max())
        y_top = max(y_top, ring.cy + ring.r_inner * 0.85)
        return cls(
            left=_analytic_stem(
                ring,
                _fit_stem_theta(
                    ring, outer, tri, cx, side="left", y_top=y_top, y_bot=y_bot
                ),
                flat_y,
                side="left",
            ),
            right=_analytic_stem(
                ring,
                _fit_stem_theta(
                    ring, outer, tri, cx, side="right", y_top=y_top, y_bot=y_bot
                ),
                flat_y,
                side="right",
            ),
        )

    def to_json(self) -> dict:
        return {"kind": "stem_pair", "left": self.left.to_json(), "right": self.right.to_json()}


def render_overlay(
    rgb: np.ndarray,
    loops: list[np.ndarray],
    ring: RingDonut | None = None,
    stems: StemPair | None = None,
    base: PartialDonut | None = None,
    shoulders: ShoulderPair | None = None,
    d_cutout: DCutout | None = None,
) -> np.ndarray:
    vis = rgb.copy()
    for i, cnt in enumerate(loops):
        col = (0, 220, 255) if i == 0 else (255, 180, 80)
        cv2.drawContours(vis, [cnt], -1, col, 2, cv2.LINE_AA)
    if ring is not None:
        c = (int(ring.cx), int(ring.cy))
        cv2.circle(vis, c, int(round(ring.r_outer)), (60, 255, 120), 3, cv2.LINE_AA)
        cv2.circle(vis, c, int(round(ring.r_inner)), (60, 255, 120), 3, cv2.LINE_AA)
        cv2.circle(vis, c, 4, (40, 200, 80), -1, cv2.LINE_AA)
    if base is not None:
        loop = np.array(base.outer_loop(), dtype=np.int32).reshape(-1, 1, 2)
        cv2.polylines(vis, [loop], False, (80, 200, 255), 3, cv2.LINE_AA)
        left = (int(base.cx - base.r_outer), int(base.flat_y))
        right = (int(base.cx + base.r_outer), int(base.flat_y))
        cv2.line(vis, left, right, (80, 200, 255), 3, cv2.LINE_AA)
    if stems is not None:
        for rect in (stems.left, stems.right):
            pts = np.array(rect.corners, dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(vis, [pts], True, (255, 80, 255), 3, cv2.LINE_AA)
    if shoulders is not None:
        for arc in (shoulders.left, shoulders.right):
            pts = np.array(arc.arc_loop(), dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(vis, [pts], False, (0, 200, 255), 3, cv2.LINE_AA)
    if d_cutout is not None:
        loop = np.array(d_cutout.inner_loop(), dtype=np.int32).reshape(-1, 1, 2)
        cv2.polylines(vis, [loop], True, (255, 220, 60), 3, cv2.LINE_AA)
    return vis


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("photo", nargs="?", default=str(DEFAULT_PHOTO))
    p.add_argument("-o", "--output", default=str(OUT))
    p.add_argument("--open", action="store_true")
    args = p.parse_args()

    rgb = np.array(Image.open(args.photo).convert("RGB"))
    mask = mask_from_photo(rgb)
    loops = contour_edges(mask)
    inners = loops[1:]
    ring = RingDonut.from_loops(loops[0], inners)
    slot = slot_hole(inners)
    base = PartialDonut.from_contours(loops[0], ring)
    d_cutout = DCutout.from_contours(slot, base)
    stems = StemPair.from_contours(loops[0], triangle_hole(inners), ring, d_cutout.flat_y)
    shoulders = ShoulderPair.from_stems(base, stems, loops[0].reshape(-1, 2).astype(float))
    overlay = render_overlay(rgb, loops, ring, stems, base, shoulders, d_cutout)

    h, w = rgb.shape[:2]
    gap = 16
    panel = np.full((h, w * 3 + gap * 2, 3), 255, np.uint8)
    panel[:, :w] = rgb
    panel[:, w + gap : w + gap + w] = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
    panel[:, w * 2 + gap * 2 :] = overlay

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(panel).save(out)

    json_path = out.with_name("ring-hook-objects.json")
    json_path.write_text(
        json.dumps(
            {
                "ring": ring.to_json(),
                "stems": stems.to_json(),
                "base": base.to_json(),
                "d_cutout": d_cutout.to_json(),
                "shoulders": shoulders.to_json(),
            },
            indent=2,
        )
        + "\n"
    )

    print(f"wrote {out}  ({len(loops)} contour loops)")
    for i, cnt in enumerate(loops):
        kind = "outer" if i == 0 else f"inner{i}"
        print(f"  {kind}: {len(cnt)} pts, area={cv2.contourArea(cnt):.0f} px²")
    print(f"  ring_donut: centre=({ring.cx:.0f},{ring.cy:.0f}) r_outer={ring.r_outer:.0f} r_inner={ring.r_inner:.0f}")
    for side, r in ("left", stems.left), ("right", stems.right):
        print(f"  stem_{side}: {r.length:.0f}x{r.width:.0f}px  angle={r.angle_deg:.1f}°")
    print(
        f"  partial_donut: centre=({base.cx:.0f},{base.flat_y:.0f}) "
        f"r_outer={base.r_outer:.0f} flat_y={base.flat_y:.0f}"
    )
    for side, sh in ("left", shoulders.left), ("right", shoulders.right):
        print(f"  shoulder_{side}: centre=({sh.cx:.0f},{sh.cy:.0f}) r={sh.r:.0f}")
    print(
        f"  d_cutout: centre=({d_cutout.cx:.0f},{d_cutout.cy:.0f}) r={d_cutout.r:.0f} "
        f"flat_y={d_cutout.flat_y:.0f} chord=[{d_cutout.x_left:.0f},{d_cutout.x_right:.0f}]"
    )
    print(f"  wrote {json_path}")

    if args.open:
        subprocess.run(["open", "-a", "Preview", str(out)], check=False)


if __name__ == "__main__":
    main()
