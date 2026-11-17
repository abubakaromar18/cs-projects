import json

import pytest

from pidash.board import Board, PinConfig
from pidash.gpio import GPIOError, MockBackend, PinMode, make_backend


@pytest.fixture
def board():
    backend = MockBackend()
    cfgs = [
        PinConfig(17, "LED", PinMode.OUTPUT),
        PinConfig(18, "Dimmer", PinMode.PWM),
        PinConfig(22, "Button", PinMode.INPUT, pull_up=True),
    ]
    return Board.from_configs(backend, cfgs, history_size=3)


# --- MockBackend ------------------------------------------------------------

def test_invalid_pin_rejected():
    with pytest.raises(GPIOError):
        MockBackend().setup(1, PinMode.OUTPUT)
    with pytest.raises(GPIOError):
        MockBackend().setup(28, PinMode.OUTPUT)


def test_write_requires_setup_and_output_mode():
    b = MockBackend()
    with pytest.raises(GPIOError, match="not been set up"):
        b.write(17, True)
    b.setup(17, PinMode.INPUT)
    with pytest.raises(GPIOError, match="input mode"):
        b.write(17, True)


def test_input_pull_up_rests_high_and_can_be_driven():
    b = MockBackend()
    b.setup(22, PinMode.INPUT, pull_up=True)
    assert b.read(22) is True
    b.simulate_input(22, False)
    assert b.read(22) is False


@pytest.mark.parametrize("duty", [-1, 100.5, "lots", None])
def test_bad_duty_rejected(duty):
    b = MockBackend()
    b.setup(18, PinMode.PWM)
    with pytest.raises(GPIOError):
        b.set_duty(18, duty)


def test_factory():
    assert make_backend("mock").name == "mock"
    with pytest.raises(GPIOError):
        make_backend("arduino")


# --- Board ------------------------------------------------------------------

def test_snapshot_sorted_and_shaped(board):
    snap = board.snapshot()
    assert [p["pin"] for p in snap] == [17, 18, 22]
    assert snap[0] == {"pin": 17, "name": "LED", "mode": "output", "value": False}
    assert snap[1]["duty"] == 0.0
    assert snap[2]["value"] is True  # pull-up


def test_set_and_toggle(board):
    assert board.set(17, True)["value"] is True
    assert board.toggle(17)["value"] is False
    assert board.toggle(17)["value"] is True


def test_cannot_set_input_pin(board):
    with pytest.raises(GPIOError, match="input pin"):
        board.set(22, True)


def test_unknown_pin_is_keyerror(board):
    with pytest.raises(KeyError):
        board.toggle(5)


def test_pwm_duty_and_value(board):
    state = board.set_duty(18, 40)
    assert state["duty"] == 40.0 and state["value"] is True
    assert board.set_duty(18, 0)["value"] is False


def test_history_is_bounded_ring_buffer_newest_first(board):
    for _ in range(5):
        board.toggle(17)
    hist = board.history()
    assert len(hist) == 3
    assert [h["value"] for h in hist] == [True, False, True]
    assert hist[0]["timestamp"] >= hist[-1]["timestamp"]


def test_duplicate_pin_rejected():
    b = Board(MockBackend())
    b.add_pin(PinConfig(17, "a", PinMode.OUTPUT))
    with pytest.raises(GPIOError, match="twice"):
        b.add_pin(PinConfig(17, "b", PinMode.OUTPUT))


def test_from_json_file(tmp_path):
    path = tmp_path / "pins.json"
    path.write_text(json.dumps({"pins": [{"pin": 4, "mode": "pwm"}, {"pin": 5, "name": "Btn", "mode": "input"}]}))
    board = Board.from_json_file(MockBackend(), path)
    assert board.pins[4].name == "GPIO4"
    assert board.pins[5].mode is PinMode.INPUT


def test_bad_config_entry():
    with pytest.raises(GPIOError):
        PinConfig.from_dict({"pin": 17, "mode": "analog"})
    with pytest.raises(GPIOError):
        PinConfig.from_dict({"name": "no pin"})
