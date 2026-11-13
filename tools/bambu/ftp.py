#!/usr/bin/env python3
# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Upload a file to the X1C SD card over implicit FTPS (port 990), or list it."""

from __future__ import annotations

import argparse
import ftplib
import socket
import ssl
import sys
from pathlib import Path

from creds import AC, IP


class ImplicitFTP_TLS(ftplib.FTP_TLS):
    def connect(self, host, port, timeout=30):
        self.host, self.port = host, port
        sock = socket.create_connection((host, port), timeout)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.context = ctx
        self.sock = ctx.wrap_socket(sock, server_hostname=host)
        self.af = self.sock.family
        self.file = self.sock.makefile("r", encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        conn = self.context.wrap_socket(
            conn, server_hostname=self.host, session=self.sock.session
        )
        return conn, size


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file", nargs="?", type=Path, help="local file to upload to the SD card root")
    p.add_argument("--name", default=None, help="remote filename (defaults to the local name)")
    args = p.parse_args(argv)

    ftp = ImplicitFTP_TLS()
    ftp.connect(IP, 990)
    ftp.login("bblp", AC)
    ftp.prot_p()
    try:
        if args.file is not None:
            if not args.file.is_file():
                print(f"not a file: {args.file}", file=sys.stderr)
                return 1
            name = args.name or args.file.name
            with args.file.open("rb") as fh:
                print(ftp.storbinary("STOR " + name, fh))
        print(ftp.nlst()[:40])
    finally:
        ftp.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
