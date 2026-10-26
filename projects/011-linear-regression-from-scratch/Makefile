PYTHON ?= python3

.PHONY: install dev test run demo clean

install:          ## install the `linreg` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite
	$(PYTHON) -m pytest

run:              ## run from source, e.g. make run ARGS="--compare"
	PYTHONPATH=src $(PYTHON) -m linreg $(ARGS)

demo:             ## synthetic data, all solvers, plots into ./plots
	PYTHONPATH=src $(PYTHON) -m linreg --compare --plots plots

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache plots
	find . -name __pycache__ -type d -exec rm -rf {} +
