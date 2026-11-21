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
import shutil
import sys
import tempfile
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
    # Resolve both logs before building either solid.
    dovetail.spec_from_log(dovetail_part)
    gauge.spec_from_log(gauge_part)

    # Stage in the nearest existing ancestor, on the destination filesystem.
    # Existing exports are untouched, and missing directories are not
    # created, until both parts and the section have been built successfully.
    staging_parent = out
    while not staging_parent.is_dir():
        staging_parent = staging_parent.parent
    with tempfile.TemporaryDirectory(prefix=".ascut-", dir=staging_parent) as directory:
        staged = Path(directory)
        mate = dovetail.export_mate(dovetail_part, staged)
        gauge.export_gauge(gauge_part, staged)
        reading = measure.measure_mate(mate["male_step"], mate["female_step"])
        (staged / "section.svg").write_text(section_svg.section_svg(reading))
        out.mkdir(parents=True, exist_ok=True)
        for path in staged.iterdir():
            destination = out / path.name
            if destination.is_file():
                shutil.copymode(destination, path)
            path.replace(destination)


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
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
