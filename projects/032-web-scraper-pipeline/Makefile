PYTHON ?= python3
RUN = PYTHONPATH=src $(PYTHON) -m scrapepipe

.PHONY: install dev test run demo serve clean

install:          ## install the `scrapepipe` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite (uses a local server on 127.0.0.1)
	$(PYTHON) -m pytest

run:              ## run from source, e.g. make run ARGS="stats"
	$(RUN) $(ARGS)

demo:             ## serve the demo site, scrape it 3 times, query the results
	$(RUN) demo

serve:            ## serve the demo bookstore on http://127.0.0.1:8000
	$(RUN) serve-demo --port 8000

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache *.db *.csv *.jsonl
	find . -name __pycache__ -type d -exec rm -rf {} +
