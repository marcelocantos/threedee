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
from math import sqrt
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blue_hue_filter import DEFAULT_PHOTO, blue_hue_grayscale

OUT = Path(__file__).resolve().parent.parent / "export" / "ring-hook-edges.png"
MIN_AREA = 5000


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
        dist = np.hypot(outer_pts[:, 0] - cx, outer_pts[:, 1] - cy)
        # Outer ring band: above the neck, just outside the hole radius.
        band = outer_pts[
            (outer_pts[:, 1] < cy + r_inner * 1.35)
            & (dist > r_inner * 0.92)
            & (dist < r_inner * 2.2)
        ]
        if len(band) < 20:
            band = outer_pts[outer_pts[:, 1] < cy + r_inner * 1.5]
        _, _, r_outer_fit = fit_circle(band)
        r_outer = float(np.percentile(np.hypot(band[:, 0] - cx, band[:, 1] - cy), 88))
        if r_outer < r_inner * 1.05:
            r_outer = r_outer_fit
        return cls(cx=cx, cy=cy, r_outer=r_outer, r_inner=r_inner)

    def to_json(self) -> dict:
        return {"kind": "ring_donut", **asdict(self)}


def render_overlay(rgb: np.ndarray, loops: list[np.ndarray], ring: RingDonut | None = None) -> np.ndarray:
    vis = rgb.copy()
    for i, cnt in enumerate(loops):
        col = (0, 220, 255) if i == 0 else (255, 180, 80)
        cv2.drawContours(vis, [cnt], -1, col, 2, cv2.LINE_AA)
    if ring is not None:
        c = (int(ring.cx), int(ring.cy))
        cv2.circle(vis, c, int(round(ring.r_outer)), (60, 255, 120), 3, cv2.LINE_AA)
        cv2.circle(vis, c, int(round(ring.r_inner)), (60, 255, 120), 3, cv2.LINE_AA)
        cv2.circle(vis, c, 4, (40, 200, 80), -1, cv2.LINE_AA)
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
    ring = RingDonut.from_loops(loops[0], loops[1:])
    overlay = render_overlay(rgb, loops, ring)

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
    json_path.write_text(json.dumps({"ring": ring.to_json()}, indent=2) + "\n")

    print(f"wrote {out}  ({len(loops)} contour loops)")
    for i, cnt in enumerate(loops):
        kind = "outer" if i == 0 else f"inner{i}"
        print(f"  {kind}: {len(cnt)} pts, area={cv2.contourArea(cnt):.0f} px²")
    print(f"  ring_donut: centre=({ring.cx:.0f},{ring.cy:.0f}) r_outer={ring.r_outer:.0f} r_inner={ring.r_inner:.0f}")
    print(f"  wrote {json_path}")

    if args.open:
        subprocess.run(["open", "-a", "Preview", str(out)], check=False)


if __name__ == "__main__":
    main()
