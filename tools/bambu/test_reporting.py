# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def bambu_command(monkeypatch):
    """Load a command with fake credentials, MQTT transport and clock."""
    def load(command, *reports):
        class Client:
            def __init__(self, *_):
                self.stopped = False

            def username_pw_set(self, *args):
                pass

            def tls_set(self, **kwargs):
                pass

            def tls_insecure_set(self, *args):
                pass

            def connect(self, *args):
                pass

            def subscribe(self, *args):
                pass

            def publish(self, *args):
                return SimpleNamespace(rc=0)

            def loop_start(self):
                self.on_connect(self, None, None, 0)
                for report in reports:
                    self.on_message(self, None, SimpleNamespace(payload=json.dumps(report)))

            def loop_stop(self):
                self.stopped = True

        client = Client()
        paho = ModuleType("paho")
        paho.mqtt = ModuleType("paho.mqtt")
        mqtt = paho.mqtt.client = ModuleType("paho.mqtt.client")
        mqtt.Client = lambda _version: client
        mqtt.CallbackAPIVersion = SimpleNamespace(VERSION2=2)
        for module in (paho, paho.mqtt, mqtt):
            monkeypatch.setitem(sys.modules, module.__name__, module)
        monkeypatch.setitem(
            sys.modules, "creds", SimpleNamespace(AC="fake-access", IP="127.0.0.1", SERIAL="fake-serial")
        )

        now = 10_000.0

        def advance(seconds):
            nonlocal now
            now += seconds

        spec = importlib.util.spec_from_file_location(command, Path(__file__).with_name(f"{command}.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.time = SimpleNamespace(time=lambda: now, sleep=advance)
        return module, client

    return load


@pytest.mark.parametrize("state, expected", [("FAILED", 1), ("FINISH", 0)])
def test_monitor_returns_held_print_outcome(bambu_command, capsys, state, expected):
    monitor, client = bambu_command("monitor", {"print": {"gcode_state": state, "mc_percent": 12}})

    code = monitor.main(["--interval", "0", "--hold", "2", "--max-hours", "0.02"])

    output = capsys.readouterr().out
    assert f"terminal state {state} held; exiting" in output
    assert "monitor stopped" in output
    assert client.stopped
    assert code == expected


@pytest.mark.parametrize(
    "report, expected, state",
    [
        ({}, 1, None),
        ({"print": {"gcode_state": "IDLE"}}, 0, "IDLE"),
        ({"print": {"gcode_state": "RUNNING", "ams": {"tray_now": "0"}}}, 0, "RUNNING"),
    ],
    ids=["no-print-report", "report-without-ams", "report-with-ams"],
)
def test_status_returns_failure_without_a_print_report(bambu_command, capsys, report, expected, state):
    reports = (report,) if report else ()
    status, client = bambu_command("status", *reports)

    code = status.main([])

    output = capsys.readouterr().out
    assert f"'gcode_state': {state!r}" in output
    assert "vt_tray " in output
    assert client.stopped
    assert code == expected


@pytest.mark.parametrize("acknowledged", [False, True], ids=["missing-ack", "received-ack"])
def test_light_returns_failure_without_an_ack(bambu_command, capsys, acknowledged):
    reports = ({"system": {"command": "ledctrl", "result": "success"}},) if acknowledged else ()
    light, client = bambu_command("light", *reports)

    code = light.main(["on", "--wait", "1"])

    output = capsys.readouterr().out
    assert "published ledctrl rc 0 mode on" in output
    assert ("ACK " in output) == acknowledged
    assert output.endswith("done\n")
    assert client.stopped
    assert code == (0 if acknowledged else 1)


@pytest.mark.parametrize(
    "instant, expected",
    [
        (datetime(2026, 4, 4, 15, 59, 59, tzinfo=timezone.utc), "2026-04-05 02:59:59 AEDT"),
        (datetime(2026, 4, 4, 16, 0, 0, tzinfo=timezone.utc), "2026-04-05 02:00:00 AEST"),
    ],
    ids=["before-fall-back", "after-fall-back"],
)
def test_monitor_timestamp_uses_the_zone_at_the_instant(bambu_command, monkeypatch, instant, expected):
    monitor, _ = bambu_command("monitor")
    clock = SimpleNamespace(now=instant.astimezone)
    monkeypatch.setattr(monitor, "datetime", clock)

    assert monitor.ts() == expected
