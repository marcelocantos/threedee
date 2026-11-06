# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""One-page section. Every dimension is taken from the measurement dict."""

from __future__ import annotations


def _num(text: str) -> float:
    return float(text)


def section_svg(measurement: dict) -> str:
    angle = float(measurement["male_angle_deg"])
    gap = float(measurement["flank_gap_mm"])
    tip = float(measurement["tip_gap_mm"])
    datum = float(measurement["datum_gap_mm"])
    neck = float(measurement["male_neck_mm"])
    tip_width = float(measurement["male_tip_mm"])
    points = measurement.get("section_xy") or []

    nums = [coord for pair in points for coord in pair]
    if nums:
        min_x, max_x = min(nums[0::2]), max(nums[0::2])
        min_y, max_y = min(nums[1::2]), max(nums[1::2])
    else:
        min_x, max_x, min_y, max_y = -10, 10, -5, 10
    pad = 8
    width = (max_x - min_x) + 2 * pad
    height = (max_y - min_y) + 2 * pad

    def xy(x, y):
        # SVG Y grows downward; the section's +Y is up.
        return x - min_x + pad, height - (y - min_y + pad)

    poly = ""
    if points:
        mapped = [f"{xy(x, y)[0]:.4f},{xy(x, y)[1]:.4f}" for x, y in points]
        poly = f'<polyline fill="none" stroke="#222" stroke-width="0.4" points="{" ".join(mapped)}"/>'

    labels = [
        ("flank-angle", f"{angle:.10f}", "deg"),
        ("flank-gap", f"{gap:.10f}", "mm"),
        ("tip-gap", f"{tip:.10f}", "mm"),
        ("datum-gap", f"{datum:.10f}", "mm"),
        ("neck", f"{neck:.10f}", "mm"),
        ("tip-width", f"{tip_width:.10f}", "mm"),
    ]
    texts = []
    for index, (kind, value, unit) in enumerate(labels):
        texts.append(
            f'<text data-kind="{kind}" data-unit="{unit}" x="2" y="{4 + index * 4}">{value} {unit}</text>'
        )
    body = "\n  ".join([poly, *texts])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.4f} {height:.4f}" '
        f'font-size="3" font-family="sans-serif">\n  {body}\n</svg>\n'
    )


def read_dimensions(svg: str) -> dict[str, float]:
    """Pull the dimension texts back out. Used to reject a hand-typed drawing."""
    found = {}
    for line in svg.splitlines():
        if "data-kind=" not in line:
            continue
        kind = line.split('data-kind="', 1)[1].split('"', 1)[0]
        raw = line.split(">", 1)[1].split("<", 1)[0].split()[0]
        found[kind] = _num(raw)
    return found
