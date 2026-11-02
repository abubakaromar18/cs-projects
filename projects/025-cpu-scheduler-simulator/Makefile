PYTHON ?= python3

.PHONY: install dev test run demo compare clean

install:          ## install the `cpusched` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite
	$(PYTHON) -m pytest

run:              ## run from source, e.g. make run ARGS="run examples/classic.csv -a rr -q 2"
	PYTHONPATH=src $(PYTHON) -m cpusched $(ARGS)

demo:             ## Round Robin and MLFQ on the sample workload
	PYTHONPATH=src $(PYTHON) -m cpusched run examples/classic.csv -a rr -q 2
	PYTHONPATH=src $(PYTHON) -m cpusched run examples/classic.csv -a mlfq --quanta 2,4,0 --boost 20

compare:          ## side-by-side metrics for every algorithm
	PYTHONPATH=src $(PYTHON) -m cpusched compare examples/classic.csv -q 2

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache *.svg
	find . -name __pycache__ -type d -exec rm -rf {} +
