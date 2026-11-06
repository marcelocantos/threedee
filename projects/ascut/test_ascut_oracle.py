# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""As-Cut oracle.

The sympy referent is frozen in frozen_1425.json before it is compared
to a STEP solid that was written and read back. Planted mates — the
nominal 15° angle, and the measured angle with the sign flipped — must
fail that comparison.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import sympy as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dovetail  # noqa: E402
import gauge  # noqa: E402
import log as logmod  # noqa: E402
import measure  # noqa: E402
import oracle_expect  # noqa: E402
import section_svg  # noqa: E402
from build123d import export_step  # noqa: E402

FROZEN_PATH = HERE / "frozen_1425.json"
DOVETAIL_PATH = HERE / "fixtures" / "dovetail.json"
GAUGE_PATH = HERE / "fixtures" / "gauge.json"
UNCALIBRATED_PATH = HERE / "fixtures" / "gauge-uncalibrated.json"


def _frozen():
    return json.loads(FROZEN_PATH.read_text())


def _expected():
    numbers = {}
    for key, item in _frozen()["derived"].items():
        if not isinstance(item, dict):
            continue
        if "exact" in item:
            numbers[key] = float(sp.Rational(item["exact"]))
        else:
            numbers[key] = float(item["decimal"])
    return numbers


def _mate_files(directory: Path, spec: dict) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    male, female = dovetail.build_pair(spec)
    male_path = directory / "male.step"
    female_path = directory / "female.step"
    export_step(male, male_path)
    export_step(female, female_path)
    return male_path, female_path


def test_frozen_file_matches_the_sympy_referent():
    oracle_expect.prove()
    assert _frozen() == oracle_expect.payload()
    video = _frozen()["video"]
    assert video["angle_measured_deg"] == "57/4"
    assert video["angle_nominal_deg"] == "15"
    assert video["width_recovery_in"] == "1/25"
    assert video["overcut_one_side_in"] == "1/50"
    assert _frozen()["derived"]["flank_gap_mm"]["exact"] == "127/2500"
    assert _frozen()["derived"]["datum_gap_mm"]["exact"] == "0"


def test_fixture_log_carries_the_video_readings_and_the_model_choices():
    part = logmod.load(DOVETAIL_PATH)
    frozen = _frozen()
    angle = part.feature("tail.flank_angle")
    assert angle.nominal.value == frozen["video"]["angle_nominal_deg"]
    assert angle.reading.value == frozen["video"]["angle_measured_deg"]
    assert angle.reading.uncertainty == frozen["video"]["angle_uncertainty_deg"]
    assert angle.reading.instrument
    assert angle.reading.datum
    recovery = part.feature("tail.width_recovery")
    assert recovery.reading.value == frozen["video"]["width_recovery_in"]
    for key, value in frozen["model_in"].items():
        assert part.design[key].value == value
        assert part.design[key].unit == "in"


def test_stale_nominal_citation_is_refused():
    part = logmod.load(DOVETAIL_PATH)
    citations = logmod.default_citations(part)
    citations["tail.flank_angle"] = {"source": "nominal", "value": "15", "unit": "deg"}
    with tempfile.TemporaryDirectory() as tmp:
        try:
            dovetail.export_mate(part, tmp, citations)
        except logmod.ExportRefused as exc:
            assert exc.reason == "stale nominal citation"
            assert exc.feature == "tail.flank_angle"
        else:
            raise AssertionError("nominal citation was exported")
        assert list(Path(tmp).iterdir()) == []


def test_value_outside_uncertainty_is_refused():
    part = logmod.load(DOVETAIL_PATH)
    citations = logmod.default_citations(part)
    # 14.27° is 0.02° off the reading; the band is ±0.01°.
    citations["tail.flank_angle"] = {"source": "reading", "value": "1427/100", "unit": "deg"}
    try:
        logmod.require(part, ("tail.flank_angle", "tail.width_recovery"), citations)
    except logmod.ExportRefused as exc:
        assert exc.reason == "measurement outside uncertainty"
        assert exc.feature == "tail.flank_angle"
    else:
        raise AssertionError("out-of-band citation was accepted")


def test_in_band_value_that_is_not_the_reading_is_refused():
    part = logmod.load(DOVETAIL_PATH)
    citations = logmod.default_citations(part)
    # 14.26° sits on the edge of the ±0.01° band and is not the reading.
    citations["tail.flank_angle"] = {"source": "reading", "value": "713/50", "unit": "deg"}
    try:
        logmod.bind(part, "tail.flank_angle", "reading", "713/50", "deg")
    except logmod.ExportRefused as exc:
        assert exc.reason == "cited value is not the reading"
    else:
        raise AssertionError("a nearby in-band value replaced the reading")


def test_uncalibrated_gauge_is_refused():
    part = logmod.load(UNCALIBRATED_PATH)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            gauge.export_gauge(part, tmp)
        except logmod.ExportRefused as exc:
            assert exc.reason == "uncalibrated"
            assert exc.feature == "blade.thickness"
        else:
            raise AssertionError("uncalibrated gauge was exported")
        assert list(Path(tmp).iterdir()) == []


def test_reimported_mate_matches_the_frozen_geometry():
    part = logmod.load(DOVETAIL_PATH)
    with tempfile.TemporaryDirectory() as tmp:
        paths = dovetail.export_mate(part, tmp)
        measured = measure.measure_mate(paths["male_step"], paths["female_step"])
        problems = measure.judge_mate(measured, _expected())
        assert problems == []
        assert measure.mesh_agrees(paths["male_step"], paths["male_stl"]) == []
        assert measure.mesh_agrees(paths["female_step"], paths["female_stl"]) == []
        drawn = section_svg.read_dimensions(section_svg.section_svg(measured))
        assert abs(drawn["flank-angle"] - measured["male_angle_deg"]) < 1e-8
        assert abs(drawn["flank-angle"] - 15) > 0.5
        assert abs(drawn["flank-gap"] - measured["flank_gap_mm"]) < 1e-8


def test_planted_nominal_and_sign_mutants_fail():
    part = logmod.load(DOVETAIL_PATH)
    spec = dovetail.spec_from_log(part)
    expected = _expected()
    with tempfile.TemporaryDirectory() as tmp:
        nominal = dict(spec)
        nominal["angle_deg"] = sp.Integer(15)
        male, female = _mate_files(Path(tmp) / "nominal", nominal)
        nominal_problems = measure.judge_mate(measure.measure_mate(male, female), expected)
        assert nominal_problems, "nominal 15° mate passed the oracle"

        signed = dict(spec)
        signed["angle_deg"] = -spec["angle_deg"]
        male, female = _mate_files(Path(tmp) / "sign", signed)
        sign_problems = measure.judge_mate(measure.measure_mate(male, female), expected)
        assert sign_problems, "sign-flipped mate passed the oracle"
        assert any("angle" in item for item in sign_problems)


def test_calibrated_gauge_exports_the_reading_not_the_label():
    part = logmod.load(GAUGE_PATH)
    frozen = _frozen()["gauge"]
    calibrated = float(sp.Rational(frozen["calibrated_mm"]))
    nominal = float(sp.Rational(frozen["nominal_mm"]))
    length = float(sp.Rational(frozen["length_mm"]))
    width = float(sp.Rational(frozen["width_mm"]))
    assert abs(calibrated - nominal) > 0.02
    with tempfile.TemporaryDirectory() as tmp:
        paths = gauge.export_gauge(part, tmp)
        measured = measure.measure_gauge(paths["step"], paths["stl"])
        problems = measure.judge_gauge(measured, calibrated, length, width)
        assert problems == []
        assert abs(measured["stl_thickness_mm"] - nominal) > 0.02


def test_cli_writes_a_mate_the_oracle_accepts():
    with tempfile.TemporaryDirectory() as tmp:
        completed = subprocess.run(
            [sys.executable, str(HERE / "ascut.py"), "--out", tmp],
            cwd=HERE,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
        out = Path(tmp)
        measured = measure.measure_mate(out / "male.step", out / "female.step")
        assert measure.judge_mate(measured, _expected()) == []
        drawn = section_svg.read_dimensions((out / "section.svg").read_text())
        assert abs(drawn["flank-angle"] - measured["male_angle_deg"]) < 1e-8
        gauge_reading = measure.measure_gauge(out / "gauge.step", out / "gauge.stl")
        calibrated = float(sp.Rational(_frozen()["gauge"]["calibrated_mm"]))
        assert abs(gauge_reading["stl_thickness_mm"] - calibrated) <= measure.STL_TOL_MM


def test_svg_dimensions_come_from_the_measurement_it_is_given():
    fake = {
        "male_angle_deg": 15.0,
        "flank_gap_mm": 1.25,
        "tip_gap_mm": 0.5,
        "datum_gap_mm": 0.0,
        "male_neck_mm": 10.0,
        "male_tip_mm": 12.0,
        "section_xy": [],
    }
    drawn = section_svg.read_dimensions(section_svg.section_svg(fake))
    assert drawn["flank-angle"] == 15.0
    assert drawn["flank-gap"] == 1.25


def test_cli_refuses_an_uncalibrated_gauge():
    with tempfile.TemporaryDirectory() as tmp:
        completed = subprocess.run(
            [
                sys.executable,
                str(HERE / "ascut.py"),
                "--out",
                tmp,
                "--gauge",
                str(UNCALIBRATED_PATH),
            ],
            cwd=HERE,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 2
        assert "uncalibrated" in completed.stderr
        assert list(Path(tmp).iterdir()) == []


def test_fourteen_point_two_six_is_the_band_edge():
    # 57/4 + 1/100 = 713/50 = 14.26. Documents the rational used above.
    assert sp.Rational(57, 4) + sp.Rational(1, 100) == sp.Rational(713, 50)
