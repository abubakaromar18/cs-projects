PYTHON ?= python3

.PHONY: install dev test run demo clean

install:          ## install the `pagesim` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite
	$(PYTHON) -m pytest

run:              ## run from source, e.g. make run ARGS="compare -f 3"
	PYTHONPATH=src $(PYTHON) -m page_replacement $(ARGS)

demo:             ## classic textbook string, step-by-step LRU trace + comparison
	PYTHONPATH=src $(PYTHON) -m page_replacement trace -a lru -f 3
	PYTHONPATH=src $(PYTHON) -m page_replacement compare -f 3
	PYTHONPATH=src $(PYTHON) -m page_replacement belady

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
