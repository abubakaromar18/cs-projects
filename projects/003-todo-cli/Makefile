PYTHON ?= python3

.PHONY: install dev test run clean

install:          ## install the `todo` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite
	$(PYTHON) -m pytest

run:              ## run from source without installing, e.g. make run ARGS="add hi"
	PYTHONPATH=src $(PYTHON) -m todo_cli $(ARGS)

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
