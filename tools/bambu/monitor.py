#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Read-only X1C print watcher. Subscribes to status only; never sends pause/stop/print."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import paho.mqtt.client as mqtt

from creds import AC, IP, SERIAL

TZ = ZoneInfo("Australia/Melbourne")
TERMINAL = {"FINISH", "FAILED"}


def ts() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S %Z")


def redact(text: str) -> str:
    if not text:
        return text
    secrets = {AC, urllib.parse.quote(AC, safe="")}
    for secret in secrets:
        if secret:
            text = text.replace(secret, "<redacted>")
    return text


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--interval", type=int, default=60, help="seconds between status lines")
    p.add_argument("--max-hours", type=float, default=3, help="exit after this many hours")
    p.add_argument("--hold", type=int, default=90, help="seconds a terminal state must hold before exit")
    p.add_argument("--log", type=Path, default=None, help="append status lines here")
    p.add_argument("--latest", type=Path, default=None, help="overwrite this file with the latest line")
    args = p.parse_args(argv)

    if not AC:
        print("no access code for serial", file=sys.stderr)
        return 1

    got = {}

    def line() -> str:
        ams = got.get("ams") or {}
        return (
            f"{ts()} state={got.get('gcode_state')} job={got.get('subtask_name')} "
            f"pct={got.get('mc_percent')} layer={got.get('layer_num')}/{got.get('total_layer_num')} "
            f"remain_min={got.get('mc_remaining_time')} nozzle={got.get('nozzle_temper')} "
            f"bed={got.get('bed_temper')} tray_now={ams.get('tray_now')} tray_tar={ams.get('tray_tar')} "
            f"print_error={got.get('print_error')} hms={got.get('hms')} stg_cur={got.get('stg_cur')}"
        )

    def write(msg: str) -> None:
        msg = redact(msg)
        print(msg, flush=True)
        if args.log:
            with args.log.open("a") as fh:
                fh.write(msg + "\n")
        if args.latest:
            args.latest.write_text(msg + "\n")

    def on_connect(client, userdata, flags, rc, properties=None):
        write(f"{ts()} mqtt connect rc={rc}")
        client.subscribe(f"device/{SERIAL}/report")
        client.publish(
            f"device/{SERIAL}/request",
            json.dumps({"pushing": {"sequence_id": "1", "command": "pushall"}}),
        )

    def on_message(client, userdata, message):
        payload = json.loads(message.payload)
        pr = payload.get("print") or {}
        if pr:
            got.update(pr)

    def on_disconnect(client, userdata, rc, properties=None, reason=None):
        write(f"{ts()} mqtt disconnect rc={rc}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set("bblp", AC)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.connect(IP, 8883, 30)
    client.loop_start()

    start = time.time()
    last_periodic = 0.0
    seen_terminal_at = None
    write(f"{ts()} monitor started")
    try:
        while time.time() - start < args.max_hours * 3600:
            now = time.time()
            if now - last_periodic >= args.interval and got:
                write(line())
                last_periodic = now
                state = got.get("gcode_state")
                hms = got.get("hms")
                if hms:
                    write(f"{ts()} HMS_PRESENT {hms}")
                if state in TERMINAL:
                    if seen_terminal_at is None:
                        seen_terminal_at = now
                    elif now - seen_terminal_at >= args.hold:
                        write(f"{ts()} terminal state {state} held; exiting")
                        return 1 if state == "FAILED" else 0
                else:
                    seen_terminal_at = None
            if now - start > 30 and not got and int(now - start) % 30 == 0:
                client.publish(
                    f"device/{SERIAL}/request",
                    json.dumps({"pushing": {"sequence_id": "1", "command": "pushall"}}),
                )
            time.sleep(1)
    except Exception as exc:
        write(f"{ts()} monitor error: {exc}")
        raise
    finally:
        client.loop_stop()
        write(f"{ts()} monitor stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
