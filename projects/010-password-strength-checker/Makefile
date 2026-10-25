PYTHON ?= python3

.PHONY: install dev test run clean

install:          ## install the `pwcheck` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite
	$(PYTHON) -m pytest

run:              ## run from source without installing, e.g. make run ARGS="--json"
	PYTHONPATH=src $(PYTHON) -m password_checker $(ARGS)

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
