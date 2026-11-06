# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Export the as-cut dovetail pair and a calibrated thickness gauge.

    python ascut.py --out export

The mate is rebuilt from the measurement log. A nominal citation where
a reading exists, a gauge with no calibration, or a cited value outside
the reading's uncertainty refuses the export and writes nothing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import dovetail
import gauge
import log as logmod
import measure
import section_svg

HERE = Path(__file__).resolve().parent
DOVETAIL = HERE / "fixtures" / "dovetail.json"
GAUGE = HERE / "fixtures" / "gauge.json"


def export_all(out: Path, dovetail_log: Path, gauge_log: Path) -> None:
    dovetail_part = logmod.load(dovetail_log)
    gauge_part = logmod.load(gauge_log)
    # Resolve both logs before writing, so a refusal leaves the directory empty.
    dovetail.spec_from_log(dovetail_part)
    gauge.spec_from_log(gauge_part)
    mate = dovetail.export_mate(dovetail_part, out)
    gauge.export_gauge(gauge_part, out)
    reading = measure.measure_mate(mate["male_step"], mate["female_step"])
    (out / "section.svg").write_text(section_svg.section_svg(reading))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dovetail", type=Path, default=DOVETAIL)
    parser.add_argument("--gauge", type=Path, default=GAUGE)
    args = parser.parse_args(argv)
    try:
        export_all(args.out, args.dovetail, args.gauge)
    except logmod.ExportRefused as exc:
        print(f"{exc.feature}: {exc.reason}", file=sys.stderr)
        return 2
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
