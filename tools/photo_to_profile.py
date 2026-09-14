#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Photo → parametric profile pipeline (calibrate, segment, fit, gate).

Classical 2D vision extracts lines and arcs; the code model consumes the
primitive table, not pixels. See docs/photo-to-profile-rubric.md.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import asdict, dataclass, field
from math import atan2, cos, degrees, hypot, pi, sin, sqrt
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from PIL import Image

# Frame: millimetres, X right, Y down (photo frame). Origin at part bbox top-left.
DEFAULT_PHOTO = Path(
    "/Users/marcelo/.cursor/projects/Users-marcelo-work-github-com-marcelocantos-threedee/assets/image-1789347656020-0.jpg"
)
FIT_TOL_MM = 0.25


@dataclass
class Calibration:
    px_per_mm: float
    method: str
    residual: float | None = None
    note: str = ""

    def to_block(self) -> str:
        lines = [
            "# CALIBRATION",
            f"px_per_mm: {self.px_per_mm:.4f}",
            f"method: {self.method}",
        ]
        if self.residual is not None:
            lines.append(f"residual: {self.residual:.4f}")
        if self.note:
            lines.append(f"note: {self.note}")
        return "\n".join(lines)


@dataclass
class Segment:
    kind: Literal["line", "arc"]
    label: str = ""
    n: int = 0
    maxres_mm: float = 0.0
    # line
    length_mm: float | None = None
    angle_deg: float | None = None
    x0_mm: float | None = None
    y0_mm: float | None = None
    x1_mm: float | None = None
    y1_mm: float | None = None
    # arc
    cx_mm: float | None = None
    cy_mm: float | None = None
    r_mm: float | None = None
    a0_deg: float | None = None
    a1_deg: float | None = None


@dataclass
class PrimitiveTable:
    frame: str = "mm, X right, Y down, origin at part bbox top-left"
    calibration: Calibration = field(default_factory=lambda: Calibration(1.0, "unset"))
    bbox_mm: tuple[float, float] = (0.0, 0.0)
    outer: list[Segment] = field(default_factory=list)
    holes: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        out = [self.calibration.to_block(), "", f"bbox: {self.bbox_mm[0]:.1f} x {self.bbox_mm[1]:.1f} mm", ""]
        out.append(f"outer: {sum(s.n for s in self.outer)} pts -> {len(self.outer)} segments")
        for seg in self.outer:
            out.append(f"  {seg.label or seg.kind}: {_seg_line(seg)}")
        for i, hole in enumerate(self.holes, 1):
            out.append(f"hole{i} ({hole.get('label', '?')}):")
            for seg in hole["segments"]:
                out.append(f"  {_seg_line(seg)}")
        return "\n".join(out)


def _seg_line(seg: Segment) -> str:
    if seg.kind == "line":
        return (
            f"line len={seg.length_mm:.1f}mm angle={seg.angle_deg:.1f}° "
            f"n={seg.n} maxres={seg.maxres_mm:.2f}mm"
        )
    return (
        f"arc r={seg.r_mm:.2f}mm centre=({seg.cx_mm:.2f}, {seg.cy_mm:.2f}) "
        f"n={seg.n} maxres={seg.maxres_mm:.2f}mm"
    )


def blue_mask(rgb: np.ndarray) -> np.ndarray:
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return (
        (b > 100)
        & (b.astype(int) > r.astype(int) + 15)
        & (b.astype(int) > g.astype(int) + 10)
    ).astype(np.uint8) * 255


def segment_mask(mask: np.ndarray, margin: int = 24) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """Largest connected component bbox + margin."""
    close = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)
    contours, _ = cv2.findContours(close, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise RuntimeError("no object found in mask")
    cnt = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(cnt)
    x0 = max(0, x - margin)
    y0 = max(0, y - margin)
    x1 = min(mask.shape[1], x + w + margin)
    y1 = min(mask.shape[0], y + h + margin)
    crop = close[y0:y1, x0:x1]
    return crop, (x0, y0, x1, y1)


def calibrate_from_height(mask: np.ndarray, height_mm: float) -> Calibration:
    ys = np.where(mask > 0)[0]
    px_h = float(ys.max() - ys.min() + 1)
    return Calibration(px_per_mm=px_h / height_mm, method="known_height", note=f"height={height_mm}mm")


def calibrate_ruler_ticks(rgb: np.ndarray) -> Calibration | None:
    """Regression over detected horizontal tick rows in the ruler strip."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    ruler = gray[:, int(w * 0.72) :]
    edges = cv2.Canny(cv2.GaussianBlur(ruler, (3, 3), 0), 40, 120)
    proj = edges.sum(axis=1).astype(float)
    if proj.max() < 20:
        return None
    thresh = 0.35 * proj.max()
    rows = np.where(proj > thresh)[0]
    if len(rows) < 8:
        return None
    # Cluster adjacent rows into tick bands.
    bands: list[list[int]] = [[rows[0]]]
    for r in rows[1:]:
        if r - bands[-1][-1] <= 2:
            bands[-1].append(r)
        else:
            bands.append([r])
    tick_y = np.array([float(np.mean(b)) for b in bands if len(b) >= 1])
    if len(tick_y) < 6:
        return None
    # Assume 1 mm between consecutive ticks in the mm band.
    idx = np.argsort(tick_y)
    tick_y = tick_y[idx]
    mm = np.arange(len(tick_y), dtype=float)
    a, b = np.polyfit(tick_y, mm, 1)
    if abs(a) < 1e-6:
        return None
    px_per_mm = 1.0 / abs(a)
    pred = a * tick_y + b
    residual = float(np.sqrt(np.mean((pred - mm) ** 2)))
    return Calibration(px_per_mm=px_per_mm, method="ruler_regression", residual=residual)


def px_to_mm(pts: np.ndarray, origin: tuple[float, float], px_per_mm: float) -> np.ndarray:
    ox, oy = origin
    out = pts.astype(float).copy()
    out[:, 0] = (out[:, 0] - ox) / px_per_mm
    out[:, 1] = (out[:, 1] - oy) / px_per_mm
    return out


def _fit_line(pts: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Return unit direction, point on line, max residual."""
    c = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
    d = vt[0]
    d = d / np.linalg.norm(d)
    rel = pts - c
    perp = rel - (rel @ d)[:, None] * d
    res = np.linalg.norm(perp, axis=1)
    return d, c, float(res.max())


def _fit_circle(pts: np.ndarray) -> tuple[float, float, float, float]:
    x, y = pts[:, 0], pts[:, 1]
    a = np.column_stack([2 * x, 2 * y, np.ones(len(x))])
    b = x * x + y * y
    cx, cy, c = np.linalg.lstsq(a, b, rcond=None)[0]
    r = sqrt(max(c + cx * cx + cy * cy, 1e-9))
    dist = np.hypot(x - cx, y - cy)
    return float(cx), float(cy), float(r), float(np.abs(dist - r).max())


def _arc_angles(cx: float, cy: float, pts: np.ndarray) -> tuple[float, float]:
    angs = [degrees(atan2(p[1] - cy, p[0] - cx)) for p in pts[[0, -1]]]
    return angs[0], angs[1]


def _plausible_arc(cx: float, cy: float, r: float, run: np.ndarray, bbox: tuple[float, float]) -> bool:
    """Reject spurious huge-radius fits on partial contours."""
    w, h = bbox
    if r > 2.5 * max(w, h):
        return False
    # Centre should lie near the arc — not kilometres away.
    mid = run[len(run) // 2]
    if hypot(cx - mid[0], cy - mid[1]) > r * 1.35:
        return False
    return True


def walk_contour(pts_mm: np.ndarray, tol_mm: float) -> list[Segment]:
    """Split a closed contour into line and arc runs."""
    n = len(pts_mm)
    if n < 8:
        return []
    bbox = (float(pts_mm[:, 0].max() - pts_mm[:, 0].min()), float(pts_mm[:, 1].max() - pts_mm[:, 1].min()))
    segs: list[Segment] = []
    i = 0
    min_run = 8
    max_span = max(min_run, n // 4)
    while i < n:
        best: Segment | None = None
        best_end = i + min_run
        best_score = float("inf")
        for end in range(i + min_run, min(n, i + max_span) + 1):
            run = pts_mm[i:end]
            candidates: list[tuple[float, Segment]] = []
            d, c, lres = _fit_line(run)
            if lres <= tol_mm:
                p0 = c - d * 1e3
                p1 = c + d * 1e3
                t0 = np.dot(run[0] - p0, p1 - p0) / np.dot(p1 - p0, p1 - p0)
                t1 = np.dot(run[-1] - p0, p1 - p0) / np.dot(p1 - p0, p1 - p0)
                q0 = p0 + t0 * (p1 - p0)
                q1 = p0 + t1 * (p1 - p0)
                ang = degrees(atan2(q1[1] - q0[1], q1[0] - q0[0])) % 180
                seg = Segment(
                    kind="line",
                    n=end - i,
                    maxres_mm=lres,
                    length_mm=float(hypot(q1[0] - q0[0], q1[1] - q0[1])),
                    angle_deg=float(ang),
                    x0_mm=float(q0[0]),
                    y0_mm=float(q0[1]),
                    x1_mm=float(q1[0]),
                    y1_mm=float(q1[1]),
                )
                candidates.append((lres - 0.02 * (end - i), seg))
            cx, cy, r, cres = _fit_circle(run)
            if cres <= tol_mm and _plausible_arc(cx, cy, r, run, bbox):
                a0, a1 = _arc_angles(cx, cy, run)
                seg = Segment(
                    kind="arc",
                    n=end - i,
                    maxres_mm=cres,
                    cx_mm=cx,
                    cy_mm=cy,
                    r_mm=r,
                    a0_deg=a0,
                    a1_deg=a1,
                )
                # Prefer longer runs; slight bonus for compact arcs.
                candidates.append((cres - 0.02 * (end - i) + 0.01 * min(r, 20), seg))
            if not candidates:
                continue
            score, seg = min(candidates, key=lambda item: item[0])
            if score < best_score:
                best_score = score
                best = seg
                best_end = end
        if best is None:
            i += 1
            continue
        segs.append(best)
        i = best_end
    return merge_adjacent_arcs(segs)


def merge_adjacent_arcs(segs: list[Segment]) -> list[Segment]:
    if not segs:
        return segs
    out: list[Segment] = []
    for seg in segs:
        if (
            out
            and seg.kind == "arc"
            and out[-1].kind == "arc"
            and out[-1].r_mm is not None
            and seg.r_mm is not None
            and abs(out[-1].r_mm - seg.r_mm) < 0.4
            and hypot(out[-1].cx_mm - seg.cx_mm, out[-1].cy_mm - seg.cy_mm) < 0.6
        ):
            prev = out[-1]
            prev.n += seg.n
            prev.maxres_mm = max(prev.maxres_mm, seg.maxres_mm)
            prev.a1_deg = seg.a1_deg
            continue
        out.append(seg)
    return out


def label_outer_segments(segs: list[Segment]) -> None:
    """Heuristic labels for the ring-hook silhouette."""
    arcs = [s for s in segs if s.kind == "arc"]
    lines = [s for s in segs if s.kind == "line"]
    if arcs:
        top = min(arcs, key=lambda s: s.cy_mm or 0)
        top.label = "ring outer"
        bottom = max(arcs, key=lambda s: s.cy_mm or 0)
        bottom.label = "base semicircle"
        ears = [a for a in arcs if a is not top and a is not bottom and (a.r_mm or 0) < 6]
        ears.sort(key=lambda s: s.cx_mm or 0)
        for i, ear in enumerate(ears[:2]):
            ear.label = "left ear" if i == 0 else "right ear"
        mid_ring = [a for a in arcs if a is not top and (a.r_mm or 0) < (top.r_mm or 99) * 0.85]
        for a in mid_ring:
            if not a.label:
                a.label = "ring chamfer/inner edge"
    for ln in sorted(lines, key=lambda s: s.x0_mm or 0):
        if ln.angle_deg and 75 <= ln.angle_deg <= 105:
            ln.label = "neck"
        elif ln.angle_deg and (ln.angle_deg < 15 or ln.angle_deg > 165):
            ln.label = "flat"


def extract(
    photo: Path,
    *,
    px_per_mm: float | None = None,
    known_height_mm: float | None = None,
    tol_mm: float = FIT_TOL_MM,
) -> tuple[PrimitiveTable, np.ndarray, np.ndarray]:
    rgb = np.array(Image.open(photo).convert("RGB"))
    mask_full = blue_mask(rgb)
    crop, (x0, y0, x1, y1) = segment_mask(mask_full)

    cands: list[Calibration] = []
    if px_per_mm is not None:
        cands.append(Calibration(px_per_mm=px_per_mm, method="cli"))
    ruler = calibrate_ruler_ticks(rgb)
    if ruler:
        cands.append(ruler)
    if known_height_mm is not None:
        cands.append(calibrate_from_height(crop, known_height_mm))
    if not cands:
        cands.append(calibrate_from_height(crop, 42.3))
    # Prefer ruler regression when explicit scale not given.
    if px_per_mm is None and ruler is not None:
        cal = ruler
    else:
        cal = cands[0]
    if len(cands) > 1:
        ref = cands[0].px_per_mm
        for other in cands[1:]:
            if abs(other.px_per_mm - ref) / ref > 0.02:
                print(
                    f"warning: calibration disagreement {ref:.2f} vs {other.px_per_mm:.2f} px/mm "
                    f"({other.method})",
                    file=sys.stderr,
                )

    contours, hierarchy = cv2.findContours(crop, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise RuntimeError("no contours in crop")
    outer_i = int(np.argmax([cv2.contourArea(c) for c in contours]))
    outer_pts = contours[outer_i].reshape(-1, 2)
    origin = (0.0, 0.0)
    outer_mm = px_to_mm(outer_pts, origin, cal.px_per_mm)
    outer_segs = walk_contour(outer_mm, tol_mm)
    label_outer_segments(outer_segs)

    holes: list[dict] = []
    if hierarchy is not None:
        child = hierarchy[0][outer_i][2]
        hole_idx = 0
        while child >= 0:
            hole_pts = contours[child].reshape(-1, 2)
            hole_mm = px_to_mm(hole_pts, origin, cal.px_per_mm)
            hsegs = walk_contour(hole_mm, tol_mm)
            cx = float(hole_mm[:, 0].mean())
            cy = float(hole_mm[:, 1].mean())
            if hole_idx == 0:
                label = "ring hole"
            elif len(hsegs) >= 3:
                label = "triangle"
            else:
                label = "D-slot"
            for s in hsegs:
                s.label = label
            holes.append({"label": label, "centre_mm": (cx, cy), "segments": hsegs})
            child = hierarchy[0][child][0]
            hole_idx += 1

    h_mm = crop.shape[0] / cal.px_per_mm
    w_mm = crop.shape[1] / cal.px_per_mm
    table = PrimitiveTable(
        calibration=cal,
        bbox_mm=(w_mm, h_mm),
        outer=outer_segs,
        holes=holes,
    )
    crop_rgb = rgb[y0:y1, x0:x1]
    return table, crop_rgb, crop


def render_overlay(crop_rgb: np.ndarray, table: PrimitiveTable) -> np.ndarray:
    vis = crop_rgb.copy()
    ppm = table.calibration.px_per_mm

    def draw_seg(seg: Segment, color: tuple[int, int, int], thick: int = 2) -> None:
        if seg.kind == "line":
            p0 = (int(seg.x0_mm * ppm), int(seg.y0_mm * ppm))
            p1 = (int(seg.x1_mm * ppm), int(seg.y1_mm * ppm))
            cv2.line(vis, p0, p1, color, thick)
        elif seg.r_mm and seg.cx_mm is not None and seg.cy_mm is not None:
            cv2.circle(
                vis,
                (int(seg.cx_mm * ppm), int(seg.cy_mm * ppm)),
                int(seg.r_mm * ppm),
                color,
                thick,
            )

    for seg in table.outer:
        draw_seg(seg, (0, 180, 255), 3)
    for hole in table.holes:
        for seg in hole["segments"]:
            draw_seg(seg, (255, 120, 200), 2)
    return vis


def table_to_json(table: PrimitiveTable) -> dict:
    def seg_dict(s: Segment) -> dict:
        return {k: v for k, v in asdict(s).items() if v is not None}

    return {
        "frame": table.frame,
        "calibration": asdict(table.calibration),
        "bbox_mm": list(table.bbox_mm),
        "outer": [seg_dict(s) for s in table.outer],
        "holes": [
            {"label": h["label"], "centre_mm": h["centre_mm"], "segments": [seg_dict(s) for s in h["segments"]]}
            for h in table.holes
        ],
    }


def gate(profile_path: Path, photo: Path, *, known_height_mm: float = 42.3) -> int:
    """Score a profile module against the segmented photo mask."""
    spec = importlib.util.spec_from_file_location("profile_mod", profile_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {profile_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    if not hasattr(mod, "profile_loops"):
        raise RuntimeError(f"{profile_path} has no profile_loops()")

    table, crop_rgb, crop_mask = extract(photo, known_height_mm=known_height_mm)
    ppm = table.calibration.px_per_mm
    h, w = crop_rgb.shape[:2]

    # Rasterise profile outer loop at calibrated scale.
    loops = mod.profile_loops()
    outer = loops["outer"]
    xs = [p[0] for p in outer]
    ys = [p[1] for p in outer]
    pad = 1.0
    x0_mm, x1_mm = min(xs) - pad, max(xs) + pad
    y0_mm, y1_mm = min(ys) - pad, max(ys) + pad

    model = np.zeros((h, w), bool)
    for y_px in range(h):
        y_mm = y_px / ppm
        for x_px in range(w):
            x_mm = x_px / ppm
            if x0_mm <= x_mm <= x1_mm and y0_mm <= y_mm <= y1_mm:
                # Point-in-polygon for outer; exclude holes.
                if _point_in_poly(x_mm, y_mm, outer):
                    inside_hole = any(_point_in_poly(x_mm, y_mm, loops[k]) for k in loops if k != "outer")
                    model[y_px, x_px] = not inside_hole

    target = crop_mask > 0
    inter = (model & target).sum()
    union = (model | target).sum()
    iou = inter / union if union else 0.0

    # Boundary residual via distance transform (mm).
    dist = cv2.distanceTransform((~target).astype(np.uint8), cv2.DIST_L2, 3)
    boundary = model & (~cv2.erode(target.astype(np.uint8), np.ones((3, 3), np.uint8)))
    bpx = dist[boundary]
    bmm = bpx / ppm if len(bpx) else np.array([0.0])
    p95 = float(np.percentile(bmm, 95)) if len(bmm) else 0.0
    mx = float(bmm.max()) if len(bmm) else 0.0

    ok_iou = iou >= 0.985
    ok_p95 = p95 <= 0.2
    ok_max = mx <= 0.4
    status = "PASS" if ok_iou and ok_p95 and ok_max else "FAIL"
    print(f"gate: {status}")
    print(f"  IoU={iou:.4f} (>=0.985: {'PASS' if ok_iou else 'FAIL'})")
    print(f"  boundary p95={p95:.3f}mm max={mx:.3f}mm")
    print(f"  px_per_mm={ppm:.3f} ({table.calibration.method})")
    return 0 if status == "PASS" else 1


def _point_in_poly(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if ((y0 > y) != (y1 > y)) and (x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0):
            inside = not inside
    return inside


def cmd_extract(args: argparse.Namespace) -> int:
    table, crop_rgb, _ = extract(
        Path(args.photo),
        px_per_mm=args.px_per_mm,
        known_height_mm=args.known_height_mm,
        tol_mm=args.tolerance,
    )
    print(table.summary())
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "primitives.json"
    json_path.write_text(json.dumps(table_to_json(table), indent=2) + "\n")
    overlay = render_overlay(crop_rgb, table)
    png_path = out_dir / "primitives-overlay.png"
    Image.fromarray(np.hstack([crop_rgb, overlay])).save(png_path)
    print(f"\nwrote {json_path}\nwrote {png_path}")
    if args.open:
        import subprocess

        subprocess.run(["open", "-a", "Preview", str(png_path)], check=False)
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    return gate(Path(args.profile), Path(args.photo), known_height_mm=args.known_height_mm or 42.3)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("extract", help="calibrate, segment, fit primitives")
    ex.add_argument("photo", nargs="?", default=str(DEFAULT_PHOTO))
    ex.add_argument("-o", "--output-dir", default="export/photo-profile")
    ex.add_argument("--px-per-mm", type=float, default=None)
    ex.add_argument("--known-height-mm", type=float, default=42.3)
    ex.add_argument("--tolerance", type=float, default=FIT_TOL_MM)
    ex.add_argument("--open", action="store_true")
    ex.set_defaults(func=cmd_extract)

    gt = sub.add_parser("gate", help="score profile module vs photo mask")
    gt.add_argument("profile", help="profile .py with profile_loops()")
    gt.add_argument("photo", nargs="?", default=str(DEFAULT_PHOTO))
    gt.add_argument("--known-height-mm", type=float, default=42.3)
    gt.set_defaults(func=cmd_gate)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
