PY ?= python3

.PHONY: test run run-pi clean

test:
	$(PY) -m pytest

# Simulated pins - works on any machine.
run:
	PYTHONPATH=src $(PY) -m pidash --config examples/pins.json

# Real hardware (on a Raspberry Pi with RPi.GPIO installed).
run-pi:
	PYTHONPATH=src $(PY) -m pidash --backend rpi --config examples/pins.json

clean:
	rm -rf .pytest_cache build *.egg-info src/*.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
