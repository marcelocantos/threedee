#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Ring hook as: ring + 2 stems + shoulders + half-ring (outer), ring hole + triangle + D (voids)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from math import atan2, cos, pi, sin, sqrt
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blue_hue_filter import DEFAULT_PHOTO
from ring_hook_mask import extract_loops, widget_mask

OUT = Path(__file__).resolve().parent.parent / "export" / "ring-hook-geometry.png"


@dataclass
class Circle:
    cx: float
    cy: float
    r: float


@dataclass
class Line:
    x0: float
    y0: float
    x1: float
    y1: float


def fit_circle(pts: np.ndarray) -> Circle:
    x, y = pts[:, 0].astype(float), pts[:, 1].astype(float)
    a = np.column_stack([2 * x, 2 * y, np.ones(len(x))])
    b = x * x + y * y
    cx, cy, c = np.linalg.lstsq(a, b, rcond=None)[0]
    r = sqrt(max(c + cx * cx + cy * cy, 1.0))
    return Circle(float(cx), float(cy), float(r))


def fit_line(pts: np.ndarray) -> Line:
    c = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
    d = vt[0]
    proj = (pts - c) @ d
    t0, t1 = proj.min(), proj.max()
    p0 = c + t0 * d
    p1 = c + t1 * d
    return Line(float(p0[0]), float(p0[1]), float(p1[0]), float(p1[1]))


def arc_points(c: Circle, a0: float, a1: float, n: int = 48) -> list[tuple[float, float]]:
    return [
        (c.cx + c.r * cos(a), c.cy + c.r * sin(a))
        for a in (a0 + (a1 - a0) * i / n for i in range(n + 1))
    ]


def line_points(ln: Line) -> list[tuple[float, float]]:
    return [(ln.x0, ln.y0), (ln.x1, ln.y1)]


def chain(*parts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for pts in parts:
        if out and pts and pts[0] == out[-1]:
            out.extend(pts[1:])
        else:
            out.extend(pts)
    return out


def _angle(c: Circle, x: float, y: float) -> float:
    return float(atan2(y - c.cy, x - c.cx))


def _on_circle(c: Circle, x: float, y: float) -> tuple[tuple[float, float], float]:
    a = _angle(c, x, y)
    return (c.cx + c.r * cos(a), c.cy + c.r * sin(a)), a


@dataclass
class RingHookGeometry:
    """Image pixels, y down. See module docstring for the five outer features + three voids."""

    cx: float
    ring: Circle
    ring_hole: Circle
    base: Circle
    base_flat_y: float
    stem_l: Line
    stem_r: Line
    shoulder_l: Circle
    shoulder_r: Circle
    d: Circle
    d_flat_y: float
    d_half: float
    tri_apex: tuple[float, float]
    tri_l: tuple[float, float]
    tri_r: tuple[float, float]

    @classmethod
    def from_mask(cls, _mask: np.ndarray, loops: list[np.ndarray]) -> RingHookGeometry:
        outer, ring_h, tri_h, slot_h = loops
        o = outer.reshape(-1, 2).astype(float)
        cx = float(np.median(o[:, 0]))

        ring_hole = fit_circle(ring_h.reshape(-1, 2))
        ring = fit_circle(o[o[:, 1] < ring_hole.cy + ring_hole.r * 1.5])

        tri = tri_h.reshape(-1, 2).astype(float)
        tri_apex = (cx, float(tri[:, 1].max()))
        tri_l = (float(tri[tri[:, 0] < cx, 0].max()), float(tri[:, 1].min()))
        tri_r = (float(tri[tri[:, 0] > cx, 0].min()), float(tri[:, 1].min()))
        y_stem_top = min(tri_l[1], tri_r[1])

        slot_pts = slot_h.reshape(-1, 2)
        d = fit_circle(slot_pts)
        d_flat_y = float(np.min(slot_pts[:, 1]))
        d_half = float(np.max(np.abs(slot_pts[:, 0] - d.cx)))

        bottom = o[o[:, 1] > float(o[:, 1].max()) - ring.r * 0.55]
        base = fit_circle(bottom)
        base_flat_y = float(np.min(bottom[:, 1]))

        side = o[(o[:, 1] > y_stem_top - 10) & (o[:, 1] < base_flat_y + 30)]
        stem_r = fit_line(side[side[:, 0] > cx + 40])
        stem_l = fit_line(side[side[:, 0] < cx - 40])

        shoulder_band = o[(o[:, 1] > base_flat_y - 100) & (o[:, 1] < base_flat_y + 15)]
        sr = shoulder_band[shoulder_band[:, 0] > cx + base.r * 0.3]
        sl = shoulder_band[shoulder_band[:, 0] < cx - base.r * 0.3]
        shoulder_r = fit_circle(sr) if len(sr) > 20 else Circle(cx + base.r * 0.72, base_flat_y - 35, 48)
        shoulder_l = fit_circle(sl) if len(sl) > 20 else Circle(cx - base.r * 0.72, base_flat_y - 35, 48)

        return cls(
            cx=cx,
            ring=ring,
            ring_hole=ring_hole,
            base=base,
            base_flat_y=base_flat_y,
            stem_l=stem_l,
            stem_r=stem_r,
            shoulder_l=shoulder_l,
            shoulder_r=shoulder_r,
            d=d,
            d_flat_y=d_flat_y,
            d_half=d_half,
            tri_apex=tri_apex,
            tri_l=tri_l,
            tri_r=tri_r,
        )

    def outer_loop(self) -> list[tuple[float, float]]:
        """Ring + 2 stems + shoulders + half-ring."""
        ring, base = self.ring, self.base
        sr, sl = self.shoulder_r, self.shoulder_l
        corner_r = (base.cx + base.r, self.base_flat_y)
        corner_l = (base.cx - base.r, self.base_flat_y)

        _, a_ring_l = _on_circle(ring, self.stem_l.x0, self.stem_l.y0)
        _, a_ring_r = _on_circle(ring, self.stem_r.x0, self.stem_r.y0)
        _, a_sr0 = _on_circle(sr, self.stem_r.x1, self.stem_r.y1)
        _, a_sr1 = _on_circle(sr, corner_r[0], corner_r[1])
        _, a_sl0 = _on_circle(sl, corner_l[0], corner_l[1])
        _, a_sl1 = _on_circle(sl, self.stem_l.x1, self.stem_l.y1)
        _, a_base_r = _on_circle(base, corner_r[0], corner_r[1])
        _, a_base_l = _on_circle(base, corner_l[0], corner_l[1])

        return chain(
            arc_points(ring, a_ring_l, a_ring_r),
            line_points(self.stem_r),
            arc_points(sr, a_sr0, a_sr1),
            [corner_r],
            arc_points(base, a_base_r, a_base_l),
            [corner_l],
            arc_points(sl, a_sl0, a_sl1),
            line_points(self.stem_l),
        )

    def ring_hole_loop(self) -> list[tuple[float, float]]:
        return arc_points(self.ring_hole, 0, 2 * pi, n=64)

    def between_stems_loop(self) -> list[tuple[float, float]]:
        """Triangle void: ring-hole arc + two inner stem edges."""
        rh = self.ring_hole
        top_l, a_l = _on_circle(rh, *self.tri_l)
        top_r, a_r = _on_circle(rh, *self.tri_r)
        if a_l < a_r:
            a_l += 2 * pi
        return chain(
            arc_points(rh, a_r, a_l),
            [top_l, self.tri_apex, top_r],
        )

    def d_loop(self) -> list[tuple[float, float]]:
        """D void: horizontal stem + half-ring."""
        left = (self.d.cx - self.d_half, self.d_flat_y)
        right = (self.d.cx + self.d_half, self.d_flat_y)
        _, a0 = _on_circle(self.d, *right)
        _, a1 = _on_circle(self.d, *left)
        if a0 > a1:
            a0, a1 = a1, a0
        return chain([left, right], arc_points(self.d, a0, a1))

    def inventory(self) -> list[str]:
        r, b, d = self.ring, self.base, self.d
        return [
            f"ring: centre ({r.cx:.0f},{r.cy:.0f}) r={r.r:.0f}",
            f"half-ring: centre ({b.cx:.0f},{b.cy:.0f}) r={b.r:.0f} flat y={self.base_flat_y:.0f}",
            f"stem L/R: nearly vertical lines",
            f"shoulders L/R: r≈{self.shoulder_l.r:.0f} / {self.shoulder_r.r:.0f}",
            f"D void: flat y={self.d_flat_y:.0f} ±{self.d_half:.0f}, arc r={d.r:.0f}",
            f"ring hole: r={self.ring_hole.r:.0f}",
        ]


def render(rgb: np.ndarray, geom: RingHookGeometry) -> np.ndarray:
    vis = rgb.copy()
    for pts, col in (
        (geom.outer_loop(), (0, 220, 255)),
        (geom.ring_hole_loop(), (120, 255, 120)),
        (geom.between_stems_loop(), (255, 120, 200)),
        (geom.d_loop(), (255, 200, 80)),
    ):
        arr = np.array(pts, dtype=np.int32).reshape(-1, 1, 2)
        if len(arr) >= 2:
            cv2.polylines(vis, [arr], True, col, 3, cv2.LINE_AA)
    return vis


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("photo", nargs="?", default=str(DEFAULT_PHOTO))
    p.add_argument("-o", "--output", default=str(OUT))
    p.add_argument("--open", action="store_true")
    args = p.parse_args()

    rgb = np.array(Image.open(args.photo).convert("RGB"))
    mask = widget_mask(rgb)
    geom = RingHookGeometry.from_mask(mask, extract_loops(mask))
    overlay = render(rgb, geom)

    h, w = rgb.shape[:2]
    gap = 16
    panel = np.full((h, w * 3 + gap * 2, 3), 255, np.uint8)
    panel[:, :w] = rgb
    panel[:, w + gap : w + gap + w] = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
    panel[:, w * 2 + gap * 2 :] = overlay

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(panel).save(out)
    print(f"wrote {out}")
    for line in geom.inventory():
        print(f"  {line}")

    if args.open:
        subprocess.run(["open", "-a", "Preview", str(out)], check=False)


if __name__ == "__main__":
    main()
