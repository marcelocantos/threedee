#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Close adaptive blue mask, extract outer + hole contours, overlay on photo."""

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

OUT = Path(__file__).resolve().parent.parent / "export" / "ring-hook-contours.png"
MIN_HOLE_AREA = 5000


def extract_loops(mask: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
    """Return binary mask and [outer, ...holes] contours (hole areas descending)."""
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=1)
    contours, hierarchy = cv2.findContours(closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
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
    return closed, [outer, *holes]


def _loop_label(i: int) -> str:
    return ("outer", "ring hole", "triangle", "base slot")[i]


def render_overlay(rgb: np.ndarray, loops: list[np.ndarray]) -> np.ndarray:
    vis = rgb.copy()
    colours = [(0, 220, 255), (140, 255, 120), (255, 120, 200), (255, 200, 80)]
    for i, cnt in enumerate(loops):
        col = colours[i % len(colours)]
        cv2.drawContours(vis, [cnt], -1, col, 2)
    return vis


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("photo", nargs="?", default=str(DEFAULT_PHOTO))
    p.add_argument("-o", "--output", default=str(OUT))
    p.add_argument("--open", action="store_true")
    args = p.parse_args()

    rgb = np.array(Image.open(args.photo).convert("RGB"))
    mask = blue_hue_grayscale(rgb)
    closed, loops = extract_loops(mask)
    overlay = render_overlay(rgb, loops)

    h, w = rgb.shape[:2]
    gap = 16
    panel = np.full((h, w * 3 + gap * 2, 3), 255, np.uint8)
    panel[:, :w] = rgb
    panel[:, w + gap : w + gap + w] = cv2.cvtColor(closed, cv2.COLOR_GRAY2RGB)
    panel[:, w * 2 + gap * 2 :] = overlay

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(panel).save(out)

    print(f"wrote {out}")
    for i, cnt in enumerate(loops):
        label = _loop_label(i) if i < 4 else f"hole{i}"
        print(f"  {label}: {len(cnt)} pts, area={cv2.contourArea(cnt):.0f} px²")

    if args.open:
        subprocess.run(["open", "-a", "Preview", str(out)], check=False)


if __name__ == "__main__":
    main()
