#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Blue / non-blue grayscale mask from HSV hue alone."""

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
H_HALF_WIDTH = 18


def hue_distance(h: np.ndarray, center: int) -> np.ndarray:
    """Circular distance on OpenCV's 0–179 hue wheel."""
    dh = np.abs(h.astype(np.int16) - center)
    return np.minimum(dh, 180 - dh)


def blue_hue_grayscale(
    rgb: np.ndarray,
    *,
    h_center: int = H_CENTER,
    h_half_width: int = H_HALF_WIDTH,
) -> np.ndarray:
    """Sharp blue/non-blue step from hue alone (0 = not blue, 255 = blue)."""
    h = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[:, :, 0]
    blue = hue_distance(h, h_center) <= h_half_width
    return blue.astype(np.uint8) * 255


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("photo", nargs="?", default=str(DEFAULT_PHOTO))
    p.add_argument("-o", "--output", default=str(DEFAULT_OUT))
    p.add_argument("--h-center", type=int, default=H_CENTER, help="OpenCV hue centre (0–179)")
    p.add_argument("--h-half-width", type=int, default=H_HALF_WIDTH, help="Hue half-width in degrees")
    p.add_argument("--open", action="store_true", help="Open result in Preview")
    args = p.parse_args()

    rgb = np.array(Image.open(args.photo).convert("RGB"))
    gray = blue_hue_grayscale(rgb, h_center=args.h_center, h_half_width=args.h_half_width)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(gray, mode="L").save(out)
    print(f"wrote {out}  h_center={args.h_center}  h_half_width={args.h_half_width}")

    if args.open:
        subprocess.run(["open", "-a", "Preview", str(out)], check=False)


if __name__ == "__main__":
    main()
