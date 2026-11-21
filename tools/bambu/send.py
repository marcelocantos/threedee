#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Start a print on the X1C over local MQTT from a file already on the SD card.

`ams_mapping` is a 0-based AMS tray id: slot 1 is 0, slot 2 is 1. By default
this refuses to send a .gcode.3mf whose plate gcode has no real `M620 S0A`
(a comment in the header is not enough). Use --check to inspect a file
without sending, or --force to skip the check.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import zipfile
from pathlib import Path

AMS_LOAD = "M620 S0A"


def plate_gcode_text(path: Path) -> str:
    if path.suffix == ".gcode":
        return path.read_text(errors="replace")
    with zipfile.ZipFile(path) as zf:
        names = [
            n for n in zf.namelist()
            if n.endswith(".gcode") and not n.endswith(".gcode.md5")
        ]
        if not names:
            raise SystemExit(f"no gcode in {path}")
        preferred = [n for n in names if n.endswith("plate_1.gcode") or n.endswith("/plate_1.gcode")]
        name = preferred[0] if preferred else names[0]
        return zf.read(name).decode("utf-8", errors="replace")


def has_ams_load(text: str) -> bool:
    command = AMS_LOAD.split()
    for line in text.splitlines():
        code = line.split(";", 1)[0]
        if code.split(maxsplit=2)[:2] == command:
            return True
    return False


def check_file(path: Path) -> bool:
    text = plate_gcode_text(path)
    ok = has_ams_load(text)
    print(f"{path}: {'found' if ok else 'MISSING'} {AMS_LOAD} in plate gcode")
    return ok


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file", type=Path, help="local .gcode.3mf to inspect and/or the name already on the SD card")
    p.add_argument(
        "--ams-tray",
        type=int,
        required=True,
        help="0-based AMS tray id (slot 1 = 0, slot 2 = 1)",
    )
    p.add_argument("--remote-name", default=None, help="filename on the SD card (defaults to the local name)")
    p.add_argument("--job-name", default=None, help="subtask_name shown on the printer")
    p.add_argument("--check", action="store_true", help="inspect the file for M620 S0A and exit")
    p.add_argument("--force", action="store_true", help="send even if M620 S0A is missing")
    p.add_argument("--wait", type=int, default=60, help="seconds to wait for a project_file ACK")
    args = p.parse_args(argv)

    if args.file.is_file():
        ok = check_file(args.file)
        if args.check:
            return 0 if ok else 1
        if not ok and not args.force:
            print(
                "refusing to send: plate gcode has no M620 S0A "
                "(flatten the full X1C profile, or pass --force)",
                file=sys.stderr,
            )
            return 1
    elif args.check:
        print(f"not a file: {args.file}", file=sys.stderr)
        return 1
    else:
        print(f"note: {args.file} is not a local file; skipping the M620 check", file=sys.stderr)

    from creds import AC, IP, SERIAL

    remote = args.remote_name or args.file.name
    job = args.job_name or Path(remote).stem.replace(".gcode", "")
    ack = {}
    last = {}

    def on_connect(client, userdata, flags, rc, properties=None):
        client.subscribe(f"device/{SERIAL}/report")
        cmd = {
            "print": {
                "sequence_id": str(int(time.time())),
                "command": "project_file",
                "param": "Metadata/plate_1.gcode",
                "url": f"ftp:///{remote}",
                "file": remote,
                "subtask_name": job,
                "project_id": "0",
                "profile_id": "0",
                "task_id": "0",
                "subtask_id": "0",
                "md5": "",
                "use_ams": True,
                "ams_mapping": [args.ams_tray],
                "timelapse": False,
                "bed_leveling": True,
                "flow_cali": False,
                "vibration_cali": False,
                "layer_inspect": True,
                "bed_type": "auto",
            }
        }
        result = client.publish(f"device/{SERIAL}/request", json.dumps(cmd))
        print("published rc", result.rc, "ams_mapping", [args.ams_tray], "file", remote, flush=True)

    def on_message(client, userdata, message):
        payload = json.loads(message.payload)
        pr = payload.get("print", {})
        if pr.get("command") == "project_file" or "result" in pr or "reason" in pr:
            info = {
                k: pr.get(k)
                for k in ("command", "result", "reason", "sequence_id", "err_code", "error_code")
                if k in pr
            }
            print("ACK", info, flush=True)
            ack.update(pr)
        keys = [
            "gcode_state", "subtask_name", "mc_print_stage", "stg_cur", "mc_percent",
            "layer_num", "total_layer_num", "mc_remaining_time", "print_error", "hms",
            "fail_reason", "bed_temper", "bed_target_temper", "nozzle_temper",
            "nozzle_target_temper",
        ]
        snap = {k: pr.get(k, last.get(k)) for k in keys}
        if pr:
            last.update({k: v for k, v in pr.items() if k in keys})
            if snap != last.get("_snap"):
                last["_snap"] = snap
                print(time.strftime("%H:%M:%S"), snap, flush=True)

    import paho.mqtt.client as mqtt

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
        while time.time() < deadline:
            if ack.get("command") == "project_file" and ack.get("result"):
                break
            time.sleep(0.2)
    finally:
        client.loop_stop()

    result = ack.get("result")
    print("done result", result, "reason", ack.get("reason"), "err", ack.get("err_code") or ack.get("error_code"))
    if result and result != "SUCCESS":
        return 1
    if not result:
        print("no project_file ACK before timeout", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
