# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Independent geometry for the 14.25° dovetail. No build123d.

The video ground a cutter to 15° and, by tramming the vise against a
face it had already cut, measured 14.25°. One side was also 0.020 in
past the common datum, and the design was widened 0.040 in.

    https://www.youtube.com/watch?v=uQQH8XzlgVU

This module is the referent those readings are judged against. The
solid is measured again after a STEP round-trip; it does not import
this file to decide its own shape.

Section frame
-------------
The slide axis is +Z. The tail centerline is +Y, and the shoulder
datum is the plane Y = 0. The signed flank angle α is the angle
between a flank plane and the YZ plane (slide and depth). Positive α
makes the tail wider at the tip than at the neck. 15° and 14.25° in
the video are this angle.

The male neck is the nominal neck plus the logged 0.040 in recovery.
The female flank is the male flank translated by the designed normal
clearance along the male flank's outward normal, (cos α, −sin α) on
the right-hand flank. Parallel flanks then stand a constant distance
apart, and that distance is the clearance. The socket floor sits one
designed tip clearance past the male tip. The shoulder and the socket
mouth both lie on Y = 0, so the datum gap is zero.

Depth, the nominal neck, the clearances, and the stock around the
joint are model choices. The video does not give them. The angle and
the 0.040 in widening are the video's numbers.
"""

from __future__ import annotations

import json
from pathlib import Path

import sympy as sp

INCH = sp.Rational(254, 10)  # millimetres in one inch

ANGLE_NOMINAL_DEG = sp.Integer(15)
ANGLE_MEASURED_DEG = sp.Rational(57, 4)  # 14.25
ANGLE_UNCERTAINTY_DEG = sp.Rational(1, 100)
OVERCUT_ONE_SIDE_IN = sp.Rational(1, 50)  # 0.020 in
WIDTH_RECOVERY_IN = sp.Rational(1, 25)  # 0.040 in
WIDTH_RECOVERY_UNCERTAINTY_IN = sp.Rational(1, 1000)

# Model choices, inches, except the gauge, which the video gives in millimetres.
NECK_IN = sp.Rational(1, 2)
DEPTH_IN = sp.Rational(1, 4)
LENGTH_IN = sp.Integer(1)
SHOULDER_IN = sp.Rational(1, 8)
BASE_IN = sp.Rational(1, 8)
WALL_IN = sp.Rational(1, 8)
FLOOR_IN = sp.Rational(1, 8)
FLANK_CLEARANCE_IN = sp.Rational(1, 500)  # 0.002 in, normal to the flank
TIP_CLEARANCE_IN = sp.Rational(1, 200)  # 0.005 in, along Y

GAUGE_LENGTH_MM = sp.Integer(75)
GAUGE_WIDTH_MM = sp.Integer(15)
GAUGE_NOMINAL_MM = sp.Rational(3, 2)  # the 1.5 mm step in the printed set
GAUGE_CALIBRATED_MM = sp.Rational(147, 100)  # synthetic micrometer reading
GAUGE_UNCERTAINTY_MM = sp.Rational(1, 50)

SOURCE = "https://www.youtube.com/watch?v=uQQH8XzlgVU"
GAUGE_SOURCE = "https://www.youtube.com/watch?v=uzqiwq_xQHU"

DIGITS = 40


def _mm(inches: sp.Expr) -> sp.Expr:
    return sp.simplify(inches * INCH)


def section():
    """Exact section quantities in millimetres and degrees."""
    alpha = sp.rad(ANGLE_MEASURED_DEG)
    neck = _mm(NECK_IN + WIDTH_RECOVERY_IN)
    depth = _mm(DEPTH_IN)
    clearance = _mm(FLANK_CLEARANCE_IN)
    tip_gap = _mm(TIP_CLEARANCE_IN)
    half = neck / 2
    cos_a = sp.cos(alpha)
    sin_a = sp.sin(alpha)
    # Right flank, outward of the male material.
    nx, ny = cos_a, -sin_a
    male_root = sp.Point(half, 0)
    female_root = sp.Point(half + clearance * nx, clearance * ny)
    gap = sp.simplify(nx * (female_root.x - male_root.x) + ny * (female_root.y - male_root.y))
    # Female outward normal points into the socket, opposite the male.
    fnx, fny = -nx, -ny
    tip_half = sp.simplify(half + depth * sp.tan(alpha))
    mouth_half = sp.simplify(half + clearance / cos_a)
    return {
        "alpha": alpha,
        "neck": neck,
        "depth": depth,
        "clearance": clearance,
        "tip_gap": tip_gap,
        "gap": gap,
        "nx": nx,
        "ny": ny,
        "fnx": fnx,
        "fny": fny,
        "tip": 2 * tip_half,
        "mouth": 2 * mouth_half,
        "half": half,
        "tip_half": tip_half,
    }


def prove() -> dict:
    """Identities the solid is not allowed to be the source of.

    The flank gap equals the designed clearance by the normal offset,
    not because a constant was copied into both places. The signed
    angle reduces to the measured 14.25°. Twice the 0.020 in overcut
    is the 0.040 in widening.
    """
    got = section()
    alpha = got["alpha"]
    if sp.simplify(got["gap"] - got["clearance"]) != 0:
        raise AssertionError("normal offset did not reproduce the clearance")
    # The outward normal is exactly (cos α, −sin α). atan2(sin α, cos α)
    # is α for this α, which is inside (−π, π). sympy will not reduce
    # that algebraic number to zero, so the component identities are the
    # exact claim and the atan2 difference is checked numerically.
    if sp.simplify(got["nx"] - sp.cos(alpha)) != 0 or sp.simplify(got["ny"] + sp.sin(alpha)) != 0:
        raise AssertionError("male normal is not (cos α, -sin α)")
    if sp.simplify(got["fnx"] + sp.cos(alpha)) != 0 or sp.simplify(got["fny"] - sp.sin(alpha)) != 0:
        raise AssertionError("female normal is not the opposite of the male normal")
    male_diff = sp.atan2(-got["ny"], got["nx"]) - alpha
    female_diff = sp.atan2(got["fny"], -got["fnx"]) - alpha
    if abs(sp.N(male_diff, 50)) > sp.Float("1e-40") or abs(sp.N(female_diff, 50)) > sp.Float("1e-40"):
        raise AssertionError("signed angle extraction missed 14.25°")
    if sp.simplify(2 * OVERCUT_ONE_SIDE_IN - WIDTH_RECOVERY_IN) != 0:
        raise AssertionError("0.040 in recovery is not twice the 0.020 in overcut")
    if not bool(sp.N(got["tip_half"] - got["half"]) > 0):
        raise AssertionError("positive angle does not widen the tip")
    neg_tip = got["half"] + got["depth"] * sp.tan(-alpha)
    if not bool(sp.N(neg_tip - got["half"]) < 0):
        raise AssertionError("sign error would not narrow the tip")
    if sp.simplify(ANGLE_NOMINAL_DEG - ANGLE_MEASURED_DEG) == 0:
        raise AssertionError("nominal and measured angles collapsed")
    return got


def _qty(value: sp.Expr, unit: str) -> dict:
    simplified = sp.together(sp.simplify(value))
    if simplified.is_rational:
        return {"unit": unit, "exact": str(sp.Rational(simplified))}
    # The closed form of tan(14.25°) is a long nested radical. The
    # decimal is what the solid is compared to; the formula names the
    # quantity so a sympy print change cannot rewrite the freeze.
    return {"unit": unit, "decimal": str(sp.N(simplified, DIGITS))}


def payload() -> dict:
    """JSON-ready freeze. Rationals stay exact; the tip width is decimal."""
    prove()
    got = section()
    return {
        "source": SOURCE,
        "gauge_source": GAUGE_SOURCE,
        "definition": (
            "alpha is the signed angle between the flank and the YZ plane; "
            "positive alpha widens the tip. The flank gap is the normal "
            "clearance. The datum gap on Y=0 is zero."
        ),
        "video": {
            "angle_nominal_deg": str(ANGLE_NOMINAL_DEG),
            "angle_measured_deg": str(ANGLE_MEASURED_DEG),
            "angle_uncertainty_deg": str(ANGLE_UNCERTAINTY_DEG),
            "overcut_one_side_in": str(OVERCUT_ONE_SIDE_IN),
            "width_recovery_in": str(WIDTH_RECOVERY_IN),
            "width_recovery_uncertainty_in": str(WIDTH_RECOVERY_UNCERTAINTY_IN),
        },
        "model_in": {
            "neck": str(NECK_IN),
            "depth": str(DEPTH_IN),
            "length": str(LENGTH_IN),
            "shoulder": str(SHOULDER_IN),
            "base": str(BASE_IN),
            "wall": str(WALL_IN),
            "floor": str(FLOOR_IN),
            "flank_clearance": str(FLANK_CLEARANCE_IN),
            "tip_clearance": str(TIP_CLEARANCE_IN),
        },
        "gauge": {
            "length_mm": str(GAUGE_LENGTH_MM),
            "width_mm": str(GAUGE_WIDTH_MM),
            "nominal_mm": str(GAUGE_NOMINAL_MM),
            "calibrated_mm": str(GAUGE_CALIBRATED_MM),
            "uncertainty_mm": str(GAUGE_UNCERTAINTY_MM),
            "note": (
                "75 by 15 mm and the 1.5 mm step are the printed-gauge video. "
                "1.47 mm is a synthetic calibration, not a reading from that video."
            ),
        },
        "derived": {
            "male_angle_deg": _qty(ANGLE_MEASURED_DEG, "deg"),
            "female_angle_deg": _qty(ANGLE_MEASURED_DEG, "deg"),
            "flank_gap_mm": _qty(got["gap"], "mm"),
            "tip_gap_mm": _qty(got["tip_gap"], "mm"),
            "datum_gap_mm": _qty(sp.Integer(0), "mm"),
            "male_neck_mm": _qty(got["neck"], "mm"),
            "male_tip_mm": _qty(got["tip"], "mm"),
            "female_mouth_mm": _qty(got["mouth"], "mm"),
            "contact": (
                "flanks parallel at the measured angle, normal gap equal to "
                "the clearance, tip clear of the floor, shoulder coincident "
                "with the socket mouth"
            ),
        },
    }


def write_freeze(path: Path | None = None) -> Path:
    path = path or Path(__file__).with_name("frozen_1425.json")
    path.write_text(json.dumps(payload(), indent=2) + "\n")
    return path


if __name__ == "__main__":
    written = write_freeze()
    print(written)
