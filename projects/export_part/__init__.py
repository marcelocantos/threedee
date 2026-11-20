# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Shared STL, STEP and viewer calls.

Part scripts keep their own geometry. Keyword arguments are passed
through, so a caller that omits tolerance gets build123d's defaults.
"""

from __future__ import annotations

import build123d


def export_stl(shape, path, **kwargs):
    return build123d.export_stl(shape, path, **kwargs)


def export_step(shape, path, **kwargs):
    return build123d.export_step(shape, path, **kwargs)


def preview(*shapes):
    try:
        from ocp_vscode import show

        show(*shapes)
    except ImportError:
        return
