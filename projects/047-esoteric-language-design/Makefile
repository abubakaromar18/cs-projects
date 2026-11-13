PYTHON ?= python3

.PHONY: install dev test run repl demo clean

install:          ## install the `pebble` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite
	$(PYTHON) -m pytest

run:              ## run a program from source, e.g. make run ARGS=examples/hello.pbl
	PYTHONPATH=src $(PYTHON) -m pebble $(ARGS)

repl:             ## interactive prompt
	PYTHONPATH=src $(PYTHON) -m pebble

demo:             ## run every bundled example
	@for f in hello fizzbuzz factorial fibonacci primes; do \
		echo "== $$f"; PYTHONPATH=src $(PYTHON) -m pebble examples/$$f.pbl; done
	@echo "== sum"; echo "1 2 3 4" | PYTHONPATH=src $(PYTHON) -m pebble examples/sum.pbl

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
