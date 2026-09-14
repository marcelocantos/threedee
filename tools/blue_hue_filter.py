#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Blue / non-blue grayscale mask with brightness-adaptive blue criteria."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

DEFAULT_PHOTO = Path(
    "/Users/marcelo/.cursor/projects/Users-marcelo-work-github-com-marcelocantos-threedee/assets/image-1789347656020-0.jpg"
)
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "export" / "ring-hook-blue-hue.png"

# OpenCV hue: 0–179 (blue ≈ 100–130).
H_CENTER = 110


def hue_distance(h: np.ndarray, center: int) -> np.ndarray:
    """Circular distance on OpenCV's 0–179 hue wheel."""
    dh = np.abs(h.astype(np.int16) - center)
    return np.minimum(dh, 180 - dh)


def _lerp(dark: float, light: float, v_norm: np.ndarray) -> np.ndarray:
    """Interpolate between dark-region and light-region thresholds."""
    return dark + (light - dark) * v_norm


def blue_hue_grayscale(
    rgb: np.ndarray,
    *,
    h_center: int = H_CENTER,
    h_half_width_light: float = 18.0,
    h_half_width_dark: float = 7.0,
    s_min_light: float = 35.0,
    s_min_dark: float = 90.0,
    dominance_margin_light: float = 8.0,
    dominance_margin_dark: float = 28.0,
) -> np.ndarray:
    """Sharp blue/non-blue step; darker pixels need tighter hue, saturation, and B dominance."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1].astype(np.float32), hsv[:, :, 2].astype(np.float32)
    v_norm = v / 255.0

    h_half = _lerp(h_half_width_dark, h_half_width_light, v_norm)
    s_min = _lerp(s_min_dark, s_min_light, v_norm)
    margin = _lerp(dominance_margin_dark, dominance_margin_light, v_norm)

    hue_ok = hue_distance(h, h_center) <= h_half
    sat_ok = s >= s_min

    r, g, b = rgb[..., 0].astype(np.int16), rgb[..., 1].astype(np.int16), rgb[..., 2].astype(np.int16)
    dominance_ok = (b > r + margin) & (b > g + margin)

    blue = hue_ok & sat_ok & dominance_ok
    return blue.astype(np.uint8) * 255


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("photo", nargs="?", default=str(DEFAULT_PHOTO))
    p.add_argument("-o", "--output", default=str(DEFAULT_OUT))
    p.add_argument("--h-center", type=int, default=H_CENTER, help="OpenCV hue centre (0–179)")
    p.add_argument("--open", action="store_true", help="Open result in Preview")
    args = p.parse_args()

    rgb = np.array(Image.open(args.photo).convert("RGB"))
    gray = blue_hue_grayscale(rgb, h_center=args.h_center)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(gray, mode="L").save(out)
    print(f"wrote {out}  h_center={args.h_center}  (adaptive hue/sat/dominance)")

    if args.open:
        subprocess.run(["open", "-a", "Preview", str(out)], check=False)


if __name__ == "__main__":
    main()
