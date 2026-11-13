#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Turn the X1C chamber light on or off. Does not start, stop, or pause a print."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time

import paho.mqtt.client as mqtt

from creds import AC, IP, SERIAL


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", nargs="?", choices=("on", "off"), default="on")
    p.add_argument("--wait", type=int, default=15)
    args = p.parse_args(argv)

    ack = {}

    def on_connect(client, userdata, flags, rc, properties=None):
        print("connect rc", rc, flush=True)
        client.subscribe(f"device/{SERIAL}/report")
        cmd = {
            "system": {
                "sequence_id": str(int(time.time())),
                "command": "ledctrl",
                "led_node": "chamber_light",
                "led_mode": args.mode,
                "led_on_time": 500,
                "led_off_time": 500,
                "loop_times": 0,
                "interval_time": 0,
            }
        }
        result = client.publish(f"device/{SERIAL}/request", json.dumps(cmd))
        print("published ledctrl rc", result.rc, "mode", args.mode, flush=True)

    def on_message(client, userdata, message):
        payload = json.loads(message.payload)
        sysm = payload.get("system") or {}
        if sysm.get("command") == "ledctrl" or "result" in sysm:
            print(
                "ACK",
                {k: sysm.get(k) for k in ("command", "result", "reason", "sequence_id", "err_code")},
                flush=True,
            )
            ack.update(sysm)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set("bblp", AC)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(IP, 8883, 30)
    client.loop_start()
    try:
        deadline = time.time() + args.wait
        while time.time() < deadline and not ack:
            time.sleep(0.3)
    finally:
        client.loop_stop()
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
