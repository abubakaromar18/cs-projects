PYTHON ?= python3

.PHONY: install dev test run demo sample clean

install:          ## install the `covid-dash` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite
	$(PYTHON) -m pytest

run:              ## run from source, e.g. make run ARGS="--summary"
	PYTHONPATH=src $(PYTHON) -m covid_dash $(ARGS)

demo:             ## build a dashboard from the bundled synthetic sample
	PYTHONPATH=src $(PYTHON) -m covid_dash --input examples/sample_covid.csv --summary --out out/dashboard.html

sample:           ## regenerate examples/sample_covid.csv (deterministic)
	PYTHONPATH=src $(PYTHON) -m covid_dash.sample examples/sample_covid.csv

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache out dashboard.html
	find . -name __pycache__ -type d -exec rm -rf {} +
