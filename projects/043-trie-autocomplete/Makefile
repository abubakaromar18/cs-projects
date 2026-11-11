PYTHON ?= python3

.PHONY: install dev test run demo clean

install:          ## install the `autocomplete` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite
	$(PYTHON) -m pytest

run:              ## run from source, e.g. make run ARGS="suggest th"
	PYTHONPATH=src $(PYTHON) -m trie_autocomplete $(ARGS)

demo:             ## interactive prompt over the bundled sample corpus
	PYTHONPATH=src $(PYTHON) -m trie_autocomplete --corpus data/sample.txt repl

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
