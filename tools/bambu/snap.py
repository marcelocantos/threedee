#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Grab one still frame from the X1C LAN live view.

Credentials come from creds.py at runtime and are redacted from ffmpeg output.
Needs ffmpeg (Homebrew's /opt/homebrew/bin/ffmpeg is tried if it is not on PATH).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

from creds import AC, IP

FFMPEG_FALLBACK = Path("/opt/homebrew/bin/ffmpeg")
STREAM = "/streaming/live/1"
PORT = 322


def redact(text: str) -> str:
    if not text:
        return text
    secrets = {AC, urllib.parse.quote(AC, safe="")}
    for secret in secrets:
        if secret:
            text = text.replace(secret, "<redacted>")
    return text


def ffmpeg_bin() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    if FFMPEG_FALLBACK.is_file():
        return str(FFMPEG_FALLBACK)
    raise SystemExit("ffmpeg not found on PATH or at /opt/homebrew/bin/ffmpeg")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-o", "--output", type=Path, default=Path("snap.jpg"))
    p.add_argument("--timeout", type=int, default=30)
    args = p.parse_args(argv)

    userinfo = "bblp:" + urllib.parse.quote(AC, safe="")
    url = f"rtsps://{userinfo}@{IP}:{PORT}{STREAM}"
    cmd = [
        ffmpeg_bin(),
        "-hide_banner", "-loglevel", "error",
        "-tls_verify", "0",
        "-rtsp_transport", "tcp",
        "-y", "-i", url,
        "-frames:v", "1", "-q:v", "2",
        str(args.output),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
    except subprocess.TimeoutExpired as exc:
        print(f"ffmpeg timed out after {args.timeout}s", file=sys.stderr)
        err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        if out:
            print(redact(out), file=sys.stderr)
        if err:
            print(redact(err), file=sys.stderr)
        return 1
    except Exception as exc:
        print(redact(str(exc)), file=sys.stderr)
        return 1

    if proc.stdout:
        print(redact(proc.stdout), end="")
    if proc.stderr:
        print(redact(proc.stderr), end="", file=sys.stderr)
    if proc.returncode != 0:
        print(f"ffmpeg exited {proc.returncode}", file=sys.stderr)
        return proc.returncode
    if not args.output.is_file() or args.output.stat().st_size == 0:
        print("ffmpeg exited 0 but output file is missing or empty", file=sys.stderr)
        return 1
    print(f"wrote {args.output} ({args.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
