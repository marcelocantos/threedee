#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Isolate Hough line/circle primitives from the ring-hook reference photo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

REF_PHOTO = Path(
    "/Users/marcelo/.cursor/projects/Users-marcelo-work-github-com-marcelocantos-threedee/assets/image-1789347656020-0.jpg"
)
OUT = Path(__file__).resolve().parent.parent / "export" / "ring-hook-hough-isolated.png"


@dataclass
class Circle:
    cx: float
    cy: float
    r: float


@dataclass
class Segment:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def length(self) -> float:
        return float(np.hypot(self.x2 - self.x1, self.y2 - self.y1))

    @property
    def angle_deg(self) -> float:
        return float(np.degrees(np.arctan2(self.y2 - self.y1, self.x2 - self.x1)) % 180)

    @property
    def mx(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def my(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def ymin(self) -> float:
        return min(self.y1, self.y2)

    @property
    def ymax(self) -> float:
        return max(self.y1, self.y2)


def blue_crop(ref: np.ndarray, margin: int = 24) -> tuple[np.ndarray, np.ndarray]:
    r, g, b = ref[..., 0], ref[..., 1], ref[..., 2]
    blue = (b > 100) & (b.astype(int) > r.astype(int) + 15) & (b.astype(int) > g.astype(int) + 10)
    ys, xs = np.where(blue)
    y0, y1 = max(0, int(ys.min()) - margin), min(ref.shape[0], int(ys.max()) + margin)
    x0, x1 = max(0, int(xs.min()) - margin), min(ref.shape[1], int(xs.max()) + margin)
    crop = ref[y0:y1, x0:x1]
    crop_blue = blue[y0:y1, x0:x1].astype(np.uint8) * 255
    return crop, crop_blue


def refine_base_circle(crop_blue: np.ndarray, hough_base: Circle) -> Circle:
    h, w = crop_blue.shape
    contours, _ = cv2.findContours(crop_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnt = max(contours, key=cv2.contourArea)
    pts_all = cnt.reshape(-1, 2)
    cx_obj = w / 2
    bottom_pts = pts_all[pts_all[:, 1] > np.quantile(pts_all[:, 1], 0.55)]
    left_arc = bottom_pts[(bottom_pts[:, 0] < cx_obj - 20) & (bottom_pts[:, 1] > 0.75 * h)]
    right_arc = bottom_pts[(bottom_pts[:, 0] > cx_obj + 20) & (bottom_pts[:, 1] > 0.75 * h)]
    left_arc = left_arc[left_arc[:, 1] > np.quantile(left_arc[:, 1], 0.3)]
    right_arc = right_arc[right_arc[:, 1] > np.quantile(right_arc[:, 1], 0.3)]

    best: tuple[float, float, float, float] | None = None
    for dcx in range(-5, 35):
        for dr in range(-5, 20):
            cx, cy, rad = hough_base.cx + dcx, hough_base.cy, hough_base.r + dr
            dl = np.hypot(left_arc[:, 0] - cx, left_arc[:, 1] - cy) - rad
            dr_ = np.hypot(right_arc[:, 0] - cx, right_arc[:, 1] - cy) - rad
            cost = abs(dl.mean()) + abs(dr_.mean()) + dl.std() * 0.3 + dr_.std() * 0.3
            if best is None or cost < best[0]:
                best = (cost, cx, cy, rad)
    assert best is not None
    return Circle(best[1], best[2], best[3])


def near_base_outer_arc(seg: Segment, base: Circle) -> bool:
    mx, my = (seg.x1 + seg.x2) / 2, (seg.y1 + seg.y2) / 2
    d = np.hypot(mx - base.cx, my - base.cy)
    if my < base.cy - base.r * 0.15:
        return False
    if abs(d - base.r) > base.r * 0.25:
        return False
    ang = seg.angle_deg
    return ang < 35 or ang > 145


def is_bottom_slot_chord(seg: Segment, base: Circle, h: int) -> bool:
    horiz = seg.angle_deg < 12 or seg.angle_deg > 168
    if not horiz or seg.length > 220:
        return False
    if seg.ymin < 0.72 * h:
        return False
    return abs(seg.mx - base.cx) <= base.r * 0.55


def is_triangle_apex_fragment(seg: Segment) -> bool:
    """Short extra hit below the main inner-right triangle edge."""
    return 93 < seg.angle_deg < 100 and 350 < seg.mx < 420 and seg.ymin > 950 and seg.length < 200


def is_base_cutout_stray(seg: Segment) -> bool:
    """Short vertical phantom inside the base slot on the right."""
    return 93 < seg.angle_deg < 100 and seg.mx > 460 and seg.ymin > 850 and seg.length < 160


def drop_coincident_twins(lines: list[Segment]) -> list[Segment]:
    """Remove the lower of two nearly identical Hough hits on the same edge."""
    drop: set[int] = set()
    for i, a in enumerate(lines):
        for j, b in enumerate(lines):
            if j <= i:
                continue
            if abs(a.angle_deg - b.angle_deg) > 2 or abs(a.mx - b.mx) > 14:
                continue
            if abs(a.length - b.length) > 18:
                continue
            overlap = min(a.ymax, b.ymax) - max(a.ymin, b.ymin)
            if overlap < 50:
                continue
            drop.add(j if lines[j].my > lines[i].my else i)
    return [ln for i, ln in enumerate(lines) if i not in drop]


def drop_short_subsegments(lines: list[Segment]) -> list[Segment]:
    """Remove short Hough fragments stacked on a longer colinear segment."""
    drop: set[int] = set()
    for i, a in enumerate(lines):
        for j, b in enumerate(lines):
            if i == j:
                continue
            short, long = (i, j) if lines[i].length < lines[j].length else (j, i)
            a, b = lines[short], lines[long]
            if a.length >= b.length * 0.45:
                continue
            if abs(a.angle_deg - b.angle_deg) > 4 or abs(a.mx - b.mx) > 22:
                continue
            overlap = min(a.ymax, b.ymax) - max(a.ymin, b.ymin)
            if overlap >= 0.55 * (a.ymax - a.ymin):
                drop.add(short)
    return [ln for i, ln in enumerate(lines) if i not in drop]


def collapse_edge_stack(
    lines: list[Segment], *, angle_lo: float, angle_hi: float, mx_lo: float, mx_hi: float
) -> list[Segment]:
    """Keep the longest Hough span for one diagonal edge; drop stacked fragments."""
    matches = [(i, ln) for i, ln in enumerate(lines) if angle_lo <= ln.angle_deg <= angle_hi and mx_lo <= ln.mx <= mx_hi]
    if len(matches) <= 1:
        return lines
    best_i, best = max(matches, key=lambda item: item[1].length)
    drop: set[int] = set()
    for i, ln in matches:
        if i == best_i:
            continue
        if abs(ln.mx - best.mx) > 45:
            continue
        overlap = min(ln.ymax, best.ymax) - max(ln.ymin, best.ymin)
        if overlap > 25 or ln.ymax <= best.ymax + 30:
            drop.add(i)
    return [ln for i, ln in enumerate(lines) if i not in drop]


def filter_lines(lines: list[Segment], base: Circle, h: int) -> list[Segment]:
    kept = [ln for ln in lines if not near_base_outer_arc(ln, base)]
    kept = [
        ln
        for ln in kept
        if not is_bottom_slot_chord(ln, base, h)
        and not is_triangle_apex_fragment(ln)
        and not is_base_cutout_stray(ln)
    ]
    kept = drop_coincident_twins(kept)
    kept = drop_short_subsegments(kept)
    # Hough splits the inner triangle edges into many colinear fragments.
    kept = collapse_edge_stack(kept, angle_lo=93, angle_hi=100, mx_lo=350, mx_hi=450)
    kept = collapse_edge_stack(kept, angle_lo=78, angle_hi=84, mx_lo=240, mx_hi=330)
    return kept


def _unit_dir(seg: Segment) -> tuple[np.ndarray, np.ndarray]:
    p = np.array([seg.x1, seg.y1], dtype=float)
    d = np.array([seg.x2 - seg.x1, seg.y2 - seg.y1], dtype=float)
    d /= np.linalg.norm(d)
    return p, d


def _line_intersection(p1: np.ndarray, d1: np.ndarray, p2: np.ndarray, d2: np.ndarray) -> np.ndarray:
    t, _s = np.linalg.solve(np.column_stack([d1, -d2]), p2 - p1)
    return p1 + t * d1


def _line_circle_hits(p: np.ndarray, d: np.ndarray, circle: Circle) -> list[np.ndarray]:
    c = np.array([circle.cx, circle.cy], dtype=float)
    f = p - c
    a = float(np.dot(d, d))
    b = 2.0 * float(np.dot(f, d))
    cc = float(np.dot(f, f)) - circle.r**2
    disc = b * b - 4 * a * cc
    if disc < 0:
        return []
    sd = np.sqrt(disc)
    return [p + t * d for t in ((-b - sd) / (2 * a), (-b + sd) / (2 * a))]


def _is_inner_left(seg: Segment) -> bool:
    return 78 <= seg.angle_deg <= 84 and 240 <= seg.mx <= 330


def _is_inner_right(seg: Segment) -> bool:
    return 93 <= seg.angle_deg <= 100 and 350 <= seg.mx <= 450


def extend_inner_triangle(lines: list[Segment], ring: Circle) -> list[Segment]:
    """Extend inner void edges to meet the ring circle at the top and each other at the apex."""
    left_candidates = [ln for ln in lines if _is_inner_left(ln)]
    right_candidates = [ln for ln in lines if _is_inner_right(ln)]
    if not left_candidates or not right_candidates:
        return lines

    left = max(left_candidates, key=lambda ln: ln.length)
    right = max(right_candidates, key=lambda ln: ln.length)
    p_l, d_l = _unit_dir(left)
    p_r, d_r = _unit_dir(right)
    apex = _line_intersection(p_l, d_l, p_r, d_r)

    def ring_touch(seg: Segment, p: np.ndarray, d: np.ndarray) -> np.ndarray:
        hits = _line_circle_hits(p, d, ring)
        below_ring = [h for h in hits if h[1] > ring.cy]
        if not below_ring:
            below_ring = hits
        return min(below_ring, key=lambda h: h[1])

    top_l = ring_touch(left, p_l, d_l)
    top_r = ring_touch(right, p_r, d_r)

    extended = [
        Segment(float(top_l[0]), float(top_l[1]), float(apex[0]), float(apex[1])),
        Segment(float(top_r[0]), float(top_r[1]), float(apex[0]), float(apex[1])),
    ]
    rest = [ln for ln in lines if not _is_inner_left(ln) and not _is_inner_right(ln)]
    return rest + extended


def pick_circles(circles: list[Circle], crop_blue: np.ndarray, h: int) -> list[Circle]:
    bottom = [c for c in circles if c.cy > 0.62 * h]
    base_hough = max(bottom, key=lambda c: c.r)
    base = refine_base_circle(crop_blue, base_hough)

    left_ears = [c for c in bottom if c.cx < base.cx - base.r * 0.2 and 0.25 * base.r < c.r < 0.55 * base.r]
    ear_l = max(left_ears, key=lambda c: c.r)
    right_ears = [c for c in bottom if c.cx > base.cx + base.r * 0.15 and abs(c.r - ear_l.r) <= ear_l.r * 0.25]
    if not right_ears:
        right_ears = [c for c in bottom if c.cx > base.cx + base.r * 0.1 and 0.25 * base.r < c.r < 0.55 * base.r]
    ear_r = min(right_ears, key=lambda c: abs(c.r - ear_l.r))

    top_band = [c for c in circles if c.cy < 0.25 * h and c.r > 150]
    ring_candidates = [c for c in top_band if 200 <= c.r <= 250 and 310 <= c.cx <= 360 and 0.14 * h <= c.cy <= 0.20 * h]
    ring = max(ring_candidates, key=lambda c: c.r)
    return [base, ear_l, ear_r, ring]


def detect(crop: np.ndarray, crop_blue: np.ndarray) -> tuple[list[Segment], list[Circle]]:
    h, w = crop.shape[:2]
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blur, 35, 110)
    edges = cv2.dilate(edges, np.ones((2, 2), np.uint8), iterations=1)

    raw_lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 40, minLineLength=int(0.06 * h), maxLineGap=12)
    lines = [Segment(*line[0]) for line in raw_lines] if raw_lines is not None else []

    raw_circles = cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=int(0.08 * w),
        param1=80,
        param2=28,
        minRadius=int(0.04 * w),
        maxRadius=int(0.45 * w),
    )
    circles = [Circle(*c) for c in raw_circles[0]] if raw_circles is not None else []

    base_hough = max([c for c in circles if c.cy > 0.62 * h], key=lambda c: c.r)
    base = refine_base_circle(crop_blue, base_hough)
    kept_lines = filter_lines(lines, base, h)
    kept_circles = pick_circles(circles, crop_blue, h)
    kept_lines = extend_inner_triangle(kept_lines, kept_circles[3])
    return kept_lines, kept_circles


def render(crop: np.ndarray, lines: list[Segment], circles: list[Circle]) -> np.ndarray:
    h, w = crop.shape[:2]
    vis = crop.copy()
    for ln in lines:
        cv2.line(vis, (int(ln.x1), int(ln.y1)), (int(ln.x2), int(ln.y2)), (0, 180, 255), 3)
    for c, col in zip(circles, [(255, 120, 0), (255, 200, 0), (255, 200, 0), (255, 80, 180)]):
        cv2.circle(vis, (int(c.cx), int(c.cy)), int(c.r), col, 3)
        cv2.circle(vis, (int(c.cx), int(c.cy)), 4, (0, 255, 0), -1)
    panel = np.full((h, w * 2 + 24, 3), 255, np.uint8)
    panel[:, :w] = crop
    panel[:, w + 24 :] = vis
    return panel


def main() -> None:
    ref = np.array(Image.open(REF_PHOTO))
    crop, crop_blue = blue_crop(ref)
    lines, circles = detect(crop, crop_blue)
    panel = render(crop, lines, circles)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(panel).save(OUT)
    print(f"lines kept: {len(lines)}")
    print(f"circles: base r={circles[0].r:.0f} ring r={circles[3].r:.0f}")
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
