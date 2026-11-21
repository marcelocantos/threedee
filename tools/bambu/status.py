#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Print the X1C's current job status and AMS tray contents (read-only)."""

from __future__ import annotations

import json
import ssl
import sys
import time

import paho.mqtt.client as mqtt

from creds import AC, IP, SERIAL


def main(argv=None) -> int:
    got = {}

    def on_connect(client, userdata, flags, rc, properties=None):
        print("connect rc", rc)
        client.subscribe(f"device/{SERIAL}/report")
        client.publish(
            f"device/{SERIAL}/request",
            json.dumps({"pushing": {"sequence_id": "1", "command": "pushall"}}),
        )

    def on_message(client, userdata, message):
        payload = json.loads(message.payload)
        pr = payload.get("print", {})
        if pr:
            got.update(pr)

    if not AC:
        print("no access code for serial", file=sys.stderr)
        return 1

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set("bblp", AC)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(IP, 8883, 30)
    client.loop_start()
    try:
        deadline = time.time() + 25
        while time.time() < deadline and "ams" not in got:
            time.sleep(0.5)
    finally:
        client.loop_stop()

    keys = [
        "gcode_state", "subtask_name", "mc_percent", "print_error", "layer_num",
        "total_layer_num", "mc_remaining_time", "bed_temper", "nozzle_diameter",
        "nozzle_type", "fail_reason", "print_type", "sdcard", "hms", "home_flag",
        "stg_cur",
    ]
    print({k: got.get(k) for k in keys})
    ams = got.get("ams") or {}
    print("tray_now", ams.get("tray_now"), "ams_exist", ams.get("ams_exist_bits"))
    for unit in ams.get("ams", []):
        for tray in unit.get("tray", []):
            print(
                "ams", unit.get("id"),
                "tray", tray.get("id"),
                tray.get("tray_type"),
                tray.get("tray_sub_brands"),
                tray.get("tray_color"),
                tray.get("tray_info_idx"),
                "remain", tray.get("remain"),
            )
    vt = got.get("vt_tray") or {}
    print("vt_tray", {k: vt.get(k) for k in ("tray_type", "tray_color", "tray_info_idx")})
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(main())
