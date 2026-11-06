# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Printable Haberdasher. The tray and tiles are built by the shared cabinet generator.

Coordinates come from pieces.json, written by geometry.py from Dudeney's
1907 construction. Run from this directory's export folder, as the other
threedee projects do:

    mkdir -p export && cd export && python ../haberdasher.py --no-preview
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "dissections"))

from tray import build_print  # noqa: E402


def load_dissection():
    doc = json.loads((ROOT / "pieces.json").read_text())
    return next(item for item in doc["dissections"] if item["id"] == "haberdasher")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--kerf", type=float, default=None, help="Override the JSON kerf (mm)")
    args = parser.parse_args()
    build_print(
        load_dissection(),
        kerf=args.kerf,
        preview=not args.no_preview,
        stem="haberdasher",
    )


if __name__ == "__main__":
    main()
