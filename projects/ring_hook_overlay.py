#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Render ring-hook profile overlay aligned to the reference photo."""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch
from PIL import Image

from ring_hook_profile import profile_loops

REF_PHOTO = Path(
    "/Users/marcelo/.cursor/projects/Users-marcelo-work-github-com-marcelocantos-threedee/assets/image-1789347656020-0.jpg"
)
OUT = Path(__file__).resolve().parent.parent / "export" / "ring-hook-overlay.png"

# Manual widget crop in reference photo pixels (excludes ruler)
CROP = (600, 260, 1020, 1680)
PHOTO_HEIGHT_MM = 42.3
BLUE = "#2f74c0"


def photo_crop() -> tuple[Image.Image, float]:
    full = Image.open(REF_PHOTO).crop(CROP)
    arr = np.array(full)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mask = ((b.astype(int) - np.maximum(r, g).astype(int)) > 25) & (b > 100)
    rows = np.where(mask.any(axis=1))[0]
    top = align_top_row_from_mask(mask)
    bottom = rows[-1]
    crop = full.crop((0, top, full.size[0], bottom + 1))
    px_per_mm = crop.size[1] / PHOTO_HEIGHT_MM
    return crop, px_per_mm


def align_top_row_from_mask(mask: np.ndarray) -> int:
    for row in range(mask.shape[0]):
        cols = np.where(mask[row])[0]
        if len(cols) >= 40 and (cols.max() - cols.min()) >= 280:
            return max(0, row - 1)
    return 0


def patch(pts: list[tuple[float, float]], **kw) -> PathPatch:
    codes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(pts) - 2) + [MplPath.CLOSEPOLY]
    return PathPatch(MplPath(pts, codes), **kw)


def _figure_for_profile(
    loops: dict[str, list[tuple[float, float]]],
    px_per_mm: float,
    y_offset_mm: float,
    w_px: int,
    h_px: int,
    *,
    transparent: bool,
):
    outer = loops["outer"]
    xs = [p[0] for p in outer]
    pad_mm = 1.0
    x_half_mm = max(abs(min(xs)), abs(max(xs))) + pad_mm
    dpi = 200
    fig, ax = plt.subplots(figsize=(w_px / dpi, h_px / dpi), dpi=dpi)
    shifted = lambda pts: [(x, y + y_offset_mm) for x, y in pts]
    face = BLUE if transparent else "black"
    ax.add_patch(patch(shifted(outer), facecolor=face, edgecolor=face, linewidth=0))
    for hole in ("ring_hole", "triangle", "base_cutout"):
        ax.add_patch(patch(shifted(loops[hole]), facecolor="white", edgecolor="white", linewidth=0))
    ax.set_xlim(-x_half_mm, x_half_mm)
    ax.set_ylim(PHOTO_HEIGHT_MM + pad_mm, -pad_mm)
    ax.set_position([0, 0, 1, 1])
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    if transparent:
        fig.patch.set_alpha(0)
        ax.patch.set_alpha(0)
    else:
        fig.patch.set_facecolor("white")
    return fig, ax


def rasterize_profile(px_per_mm: float, y_offset_mm: float, w_px: int, h_px: int) -> np.ndarray:
    loops = profile_loops()
    fig, _ = _figure_for_profile(loops, px_per_mm, y_offset_mm, w_px, h_px, transparent=False)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return np.array(Image.open(buf).convert("L")) < 128


def photo_mask() -> np.ndarray:
    photo, _ = photo_crop()
    arr = np.array(photo)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    return ((b.astype(int) - np.maximum(r, g).astype(int)) > 25) & (b > 100)


def best_y_offset(px_per_mm: float, w_px: int, h_px: int) -> float:
    target = photo_mask()
    best_score, best_dy = -1.0, 0.0
    for dy in np.linspace(-1.0, 1.0, 41):
        model = rasterize_profile(px_per_mm, dy, w_px, h_px)
        m = model
        inter = (m & target).sum()
        union = (m | target).sum()
        score = inter / union if union else 0
        if score > best_score:
            best_score, best_dy = score, dy
    return best_dy


def render_rgba(px_per_mm: float, y_offset_mm: float, w_px: int, h_px: int) -> Image.Image:
    loops = profile_loops()
    fig, _ = _figure_for_profile(loops, px_per_mm, y_offset_mm, w_px, h_px, transparent=True)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, transparent=True)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


def main() -> None:
    photo, px_per_mm = photo_crop()
    w_px, h_px = photo.size
    dy = best_y_offset(px_per_mm, w_px, h_px)
    model = render_rgba(px_per_mm, dy, w_px, h_px)

    gap = 32
    side = Image.new("RGB", (photo.size[0] + gap + model.size[0], photo.size[1]), "white")
    side.paste(photo, (0, 0))
    side.paste(model.convert("RGB"), (photo.size[0] + gap, 0))

    over_base = photo.convert("RGBA")
    layer = Image.new("RGBA", photo.size, (255, 255, 255, 0))
    layer.paste(model, (0, 0), model)
    overlay = Image.alpha_composite(over_base, layer).convert("RGB")

    out_h = side.size[1] + overlay.size[1] + 28
    panel = Image.new("RGB", (max(side.size[0], overlay.size[0]), out_h), "white")
    panel.paste(side, (0, 0))
    panel.paste(overlay, ((panel.size[0] - overlay.size[0]) // 2, side.size[1] + 28))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    panel.save(OUT)
    vs = OUT.with_name("ring-hook-vs-photo.png")
    side.save(vs)
    print(f"wrote {OUT} and {vs}  y_offset={dy:.2f}mm")


if __name__ == "__main__":
    main()
