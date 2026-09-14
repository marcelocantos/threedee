#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Adaptive blue mask → closed silhouette → raw contour edges (no object labels)."""

from __future__ import annotations

import argparse
import subprocess
import sys
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


def render_overlay(rgb: np.ndarray, loops: list[np.ndarray]) -> np.ndarray:
    vis = rgb.copy()
    for i, cnt in enumerate(loops):
        col = (0, 220, 255) if i == 0 else (255, 180, 80)
        cv2.drawContours(vis, [cnt], -1, col, 2, cv2.LINE_AA)
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
    overlay = render_overlay(rgb, loops)

    h, w = rgb.shape[:2]
    gap = 16
    panel = np.full((h, w * 3 + gap * 2, 3), 255, np.uint8)
    panel[:, :w] = rgb
    panel[:, w + gap : w + gap + w] = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
    panel[:, w * 2 + gap * 2 :] = overlay

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(panel).save(out)

    print(f"wrote {out}  ({len(loops)} loops)")
    for i, cnt in enumerate(loops):
        kind = "outer" if i == 0 else f"inner{i}"
        print(f"  {kind}: {len(cnt)} pts, area={cv2.contourArea(cnt):.0f} px²")

    if args.open:
        subprocess.run(["open", "-a", "Preview", str(out)], check=False)


if __name__ == "__main__":
    main()
