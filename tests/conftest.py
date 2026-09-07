# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Make the standalone part scripts in projects/ importable by the tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "projects"))
