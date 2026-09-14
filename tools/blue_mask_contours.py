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
from math import atan2, cos, sin, sqrt
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
        theta = float(
            np.median(
                [
                    _sample_stem_angle(outer, tri, cx, side="left", y_top=y_top, y_bot=y_bot),
                    _sample_stem_angle(outer, tri, cx, side="right", y_top=y_top, y_bot=y_bot),
                ]
            )
        )
        return cls(
            left=_analytic_stem(ring, theta, flat_y, side="left"),
            right=_analytic_stem(ring, theta, flat_y, side="right"),
        )

    def to_json(self) -> dict:
        return {"kind": "stem_pair", "left": self.left.to_json(), "right": self.right.to_json()}


def render_overlay(
    rgb: np.ndarray,
    loops: list[np.ndarray],
    ring: RingDonut | None = None,
    stems: StemPair | None = None,
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
    if stems is not None:
        for rect in (stems.left, stems.right):
            pts = np.array(rect.corners, dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(vis, [pts], True, (255, 80, 255), 3, cv2.LINE_AA)
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
    stems = StemPair.from_contours(loops[0], triangle_hole(inners), ring, d_flat_y(slot))
    overlay = render_overlay(rgb, loops, ring, stems)

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
    json_path.write_text(json.dumps({"ring": ring.to_json(), "stems": stems.to_json()}, indent=2) + "\n")

    print(f"wrote {out}  ({len(loops)} contour loops)")
    for i, cnt in enumerate(loops):
        kind = "outer" if i == 0 else f"inner{i}"
        print(f"  {kind}: {len(cnt)} pts, area={cv2.contourArea(cnt):.0f} px²")
    print(f"  ring_donut: centre=({ring.cx:.0f},{ring.cy:.0f}) r_outer={ring.r_outer:.0f} r_inner={ring.r_inner:.0f}")
    for side, r in ("left", stems.left), ("right", stems.right):
        print(f"  stem_{side}: {r.length:.0f}x{r.width:.0f}px  angle={r.angle_deg:.1f}°")
    print(f"  wrote {json_path}")

    if args.open:
        subprocess.run(["open", "-a", "Preview", str(out)], check=False)


if __name__ == "__main__":
    main()
