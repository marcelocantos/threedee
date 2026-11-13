# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Load Bambu X1C LAN credentials at runtime.

The MQTT/FTPS user is always `bblp`. The access code and printer serial
are read from Bambu Studio's config:

    ~/Library/Application Support/BambuStudio/BambuStudio.conf

Nothing in this file is a secret, and this module must never hard-code an
access code.

The printer's LAN IP is not stored in that config when Studio is in LAN
Only mode (there is no selected machine). Set `BAMBU_IP`, or put the
address alone on the first line of `ip.local` next to this file
(gitignored).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

STUDIO_CONF = Path.home() / "Library/Application Support/BambuStudio/BambuStudio.conf"
IP_LOCAL = Path(__file__).resolve().parent / "ip.local"


def _load() -> tuple[str, str, str]:
    if not STUDIO_CONF.is_file():
        raise SystemExit(f"Bambu Studio config not found: {STUDIO_CONF}")
    conf = json.loads(STUDIO_CONF.read_text())
    access = conf.get("access_code") or {}
    if not isinstance(access, dict) or not access:
        raise SystemExit(f"no access_code entries in {STUDIO_CONF}")
    serial = (conf.get("app") or {}).get("user_last_selected_machine") or ""
    ac = access.get(serial) if serial else None
    if not ac:
        if len(access) == 1:
            serial, ac = next(iter(access.items()))
        else:
            raise SystemExit(
                "no access code for the selected machine; Studio has "
                f"{len(access)} saved codes and no selected serial"
            )
    ip = os.environ.get("BAMBU_IP", "").strip()
    if not ip and IP_LOCAL.is_file():
        line = IP_LOCAL.read_text().splitlines()[0].strip()
        if line and not line.startswith("#"):
            ip = line.split("=", 1)[1].strip() if line.lower().startswith("ip=") else line
    if not ip:
        raise SystemExit(
            "printer LAN IP is not in BambuStudio.conf; set BAMBU_IP or write "
            f"the address to {IP_LOCAL} (gitignored)"
        )
    return serial, ac, ip


SERIAL, AC, IP = _load()
