PYTHON ?= python3

.PHONY: install dev test run demo clean

install:          ## install the `matcalc` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite
	$(PYTHON) -m pytest

run:              ## run from source, e.g. make run ARGS="det '[[1,2],[3,4]]' --steps"
	PYTHONPATH=src $(PYTHON) -m matcalc $(ARGS)

demo:             ## show every operation with steps on a sample matrix
	PYTHONPATH=src $(PYTHON) -m matcalc rref "2 1 -1 8; -3 -1 2 -11; -2 1 2 -3" --steps
	PYTHONPATH=src $(PYTHON) -m matcalc det "2 1 -1; -3 -1 2; -2 1 2" --steps
	PYTHONPATH=src $(PYTHON) -m matcalc inv "2 1 -1; -3 -1 2; -2 1 2" --steps

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
