PY ?= python3

.PHONY: install run test gui-test clean
install:
	$(PY) -m pip install -e ".[dev]"
run:
	PYTHONPATH=src $(PY) -m colorpick
test:
	$(PY) -m pytest
# Run the GUI smoke tests on a virtual display (Linux, needs xvfb).
gui-test:
	xvfb-run -a $(PY) -m pytest tests/test_gui.py -v
clean:
	rm -rf build dist *.egg-info .pytest_cache src/*.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} +
