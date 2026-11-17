"""End-to-end tests: start a real HTTP server on an ephemeral port and hit it."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from pidash.board import Board, PinConfig
from pidash.gpio import MockBackend, PinMode
from pidash.server import make_server

FAKE_VITALS = {"hostname": "testpi", "cpu_temp_c": 48.3, "uptime_s": 100.0, "load": [0.1, 0.2, 0.3], "memory_mb": None}


def _start(token=None):
    board = Board.from_configs(MockBackend(), [
        PinConfig(17, "LED", PinMode.OUTPUT),
        PinConfig(18, "Dimmer", PinMode.PWM),
        PinConfig(22, "Button", PinMode.INPUT),
    ])
    httpd = make_server(board, "127.0.0.1", 0, token=token, verbose=False, vitals=lambda: FAKE_VITALS)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


@pytest.fixture
def server():
    httpd, base = _start()
    yield base
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def secured():
    httpd, base = _start(token="s3cret")
    yield base
    httpd.shutdown()
    httpd.server_close()


def call(url, body=None, headers=None, raw=None, ctype="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, headers=headers or {})
    if data is not None:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def j(resp):
    return json.loads(resp[2])


def test_index_page_served(server):
    status, headers, body = call(server + "/")
    assert status == 200
    assert headers["Content-Type"].startswith("text/html")
    assert b"Pi Dashboard" in body


def test_list_pins(server):
    pins = j(call(server + "/api/pins"))
    assert [p["name"] for p in pins] == ["LED", "Dimmer", "Button"]


def test_toggle_and_set(server):
    assert j(call(server + "/api/pins/17/toggle", {}))["value"] is True
    assert j(call(server + "/api/pins/17", {"value": False}))["value"] is False
    assert j(call(server + "/api/pins/17"))["value"] is False


def test_pwm_duty(server):
    assert j(call(server + "/api/pins/18", {"duty": 75}))["duty"] == 75.0


def test_history_records_changes(server):
    call(server + "/api/pins/17/toggle", {})
    hist = j(call(server + "/api/history"))
    assert hist[0]["name"] == "LED" and hist[0]["action"] == "set"


def test_system_vitals(server):
    assert j(call(server + "/api/system"))["hostname"] == "testpi"


@pytest.mark.parametrize("path,body,code", [
    ("/api/pins/5/toggle", {}, 404),            # unconfigured pin
    ("/api/pins/22", {"value": True}, 400),     # input pin can't be set
    ("/api/pins/18", {"duty": 150}, 400),       # duty out of range
    ("/api/pins/17", {"value": "yes"}, 400),    # value must be a bool
    ("/api/nope", {}, 404),
])
def test_error_cases(server, path, body, code):
    resp = call(server + path, body)
    assert resp[0] == code
    assert "error" in j(resp)


def test_rejects_non_json_and_bad_json(server):
    assert call(server + "/api/pins/17", raw=b"value=1", ctype="application/x-www-form-urlencoded")[0] == 415
    assert call(server + "/api/pins/17", raw=b"{oops")[0] == 400


def test_body_size_limit(server):
    assert call(server + "/api/pins/17", raw=b" " * 5000)[0] == 413


def test_get_cannot_change_state(server):
    # A GET to the toggle URL must not flip anything (CSRF safety).
    assert call(server + "/api/pins/17/toggle")[0] == 404
    assert j(call(server + "/api/pins/17"))["value"] is False


def test_token_required(secured):
    assert call(secured + "/api/pins")[0] == 401
    assert call(secured + "/api/pins", headers={"Authorization": "Bearer wrong"})[0] == 401
    assert call(secured + "/api/pins", headers={"Authorization": "Bearer s3cret"})[0] == 200
    # The HTML shell itself is public; it holds no data.
    assert call(secured + "/")[0] == 200
