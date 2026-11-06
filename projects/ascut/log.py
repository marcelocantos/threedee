# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Measurement log. A mate may not cite a nominal that a reading replaced.

A feature with ``requires_reading`` does not export until a reading is
present. A reading records the instrument, the datum, the value, and an
absolute uncertainty in the same unit. Citing the nominal while that
reading exists is a stale citation. Citing a number outside
value ± uncertainty is refused. Citing any other number, even inside
the band, is refused too: the solid is rebuilt from the reading itself.
"""

from __future__ import annotations

import json
from pathlib import Path

import sympy as sp

INCH_MM = sp.Rational(254, 10)
READING_FIELDS = ("instrument", "datum", "value", "uncertainty", "unit")


class ExportRefused(Exception):
    def __init__(self, reason: str, feature: str):
        self.reason = reason
        self.feature = feature
        super().__init__(f"{feature}: {reason}")


class LogError(ValueError):
    pass


def _rational(text, label: str) -> sp.Rational:
    try:
        value = sp.Rational(str(text))
    except (TypeError, ValueError) as exc:
        raise LogError(f"{label} is not a rational") from exc
    if not value.is_finite:
        raise LogError(f"{label} is not finite")
    return value


class Quantity:
    def __init__(self, value: str, unit: str):
        self.value = str(value)
        self.unit = unit
        self.exact = _rational(self.value, "value")

    def as_dict(self) -> dict:
        return {"value": self.value, "unit": self.unit}


class Reading:
    def __init__(self, raw: dict):
        missing = [key for key in READING_FIELDS if key not in raw or raw[key] in ("", None)]
        if missing:
            raise LogError(f"reading missing {', '.join(missing)}")
        self.instrument = str(raw["instrument"])
        self.datum = str(raw["datum"])
        self.value = str(raw["value"])
        self.uncertainty = str(raw["uncertainty"])
        self.unit = str(raw["unit"])
        self.exact = _rational(self.value, "reading value")
        self.band = _rational(self.uncertainty, "uncertainty")
        if self.band < 0:
            raise LogError("uncertainty must be >= 0")


class Feature:
    def __init__(self, raw: dict):
        if "id" not in raw or "nominal" not in raw:
            raise LogError("feature needs an id and a nominal")
        self.id = str(raw["id"])
        self.nominal = Quantity(raw["nominal"]["value"], raw["nominal"]["unit"])
        self.requires_reading = bool(raw.get("requires_reading", False))
        reading = raw.get("reading")
        self.reading = None if reading is None else Reading(reading)
        if self.reading is not None and self.reading.unit != self.nominal.unit:
            raise LogError(f"{self.id}: reading unit {self.reading.unit} != nominal {self.nominal.unit}")


class Log:
    def __init__(self, raw: dict, path: Path | None = None):
        if "id" not in raw or "features" not in raw:
            raise LogError("log needs an id and features")
        self.id = str(raw["id"])
        self.citation = raw.get("citation", "")
        self.path = path
        self.features = [Feature(item) for item in raw["features"]]
        ids = [item.id for item in self.features]
        if len(ids) != len(set(ids)):
            raise LogError("duplicate feature id")
        self._by_id = {item.id: item for item in self.features}
        self.design = {}
        for key, item in raw.get("design", {}).items():
            self.design[key] = Quantity(item["value"], item["unit"])

    def feature(self, feature_id: str) -> Feature:
        try:
            return self._by_id[feature_id]
        except KeyError as exc:
            raise LogError(f"no feature {feature_id}") from exc

    def design_mm(self, key: str) -> sp.Rational:
        try:
            item = self.design[key]
        except KeyError as exc:
            raise LogError(f"no design value {key}") from exc
        return to_mm(item.exact, item.unit)


def load(path: Path | str) -> Log:
    path = Path(path)
    return Log(json.loads(path.read_text()), path)


def to_mm(value: sp.Rational, unit: str) -> sp.Rational:
    if unit == "mm":
        return sp.Rational(value)
    if unit == "in":
        return sp.Rational(value) * INCH_MM
    raise LogError(f"not a length unit: {unit}")


def default_citations(log: Log) -> dict:
    """Reading when one exists, otherwise the nominal."""
    citations = {}
    for feature in log.features:
        if feature.reading is None:
            citations[feature.id] = {
                "source": "nominal",
                "value": feature.nominal.value,
                "unit": feature.nominal.unit,
            }
        else:
            citations[feature.id] = {
                "source": "reading",
                "value": feature.reading.value,
                "unit": feature.reading.unit,
            }
    return citations


def bind(log: Log, feature_id: str, source: str, value: str, unit: str) -> Quantity:
    """Accept a citation or refuse it. Returns the quantity the solid may use."""
    feature = log.feature(feature_id)
    if feature.requires_reading and feature.reading is None:
        raise ExportRefused("uncalibrated", feature_id)
    if source == "nominal":
        if feature.reading is not None:
            raise ExportRefused("stale nominal citation", feature_id)
        cited = _rational(value, feature_id)
        if unit != feature.nominal.unit or cited != feature.nominal.exact:
            raise ExportRefused("nominal mismatch", feature_id)
        return Quantity(feature.nominal.value, feature.nominal.unit)
    if source != "reading":
        raise ExportRefused(f"unknown citation source {source}", feature_id)
    if feature.reading is None:
        raise ExportRefused("uncalibrated", feature_id)
    if unit != feature.reading.unit:
        raise ExportRefused("citation unit does not match the reading", feature_id)
    cited = _rational(value, feature_id)
    if abs(cited - feature.reading.exact) > feature.reading.band:
        raise ExportRefused("measurement outside uncertainty", feature_id)
    if cited != feature.reading.exact:
        raise ExportRefused("cited value is not the reading", feature_id)
    return Quantity(feature.reading.value, feature.reading.unit)


def require(log: Log, feature_ids: tuple[str, ...], citations: dict | None = None) -> dict[str, Quantity]:
    """Bind each feature. A required reading that is absent refuses export."""
    citations = default_citations(log) if citations is None else citations
    bound = {}
    for feature_id in feature_ids:
        feature = log.feature(feature_id)
        if feature.requires_reading and feature.reading is None:
            raise ExportRefused("uncalibrated", feature_id)
        try:
            citation = citations[feature_id]
        except KeyError as exc:
            raise ExportRefused("missing citation", feature_id) from exc
        bound[feature_id] = bind(
            log,
            feature_id,
            citation["source"],
            str(citation["value"]),
            citation["unit"],
        )
    return bound
