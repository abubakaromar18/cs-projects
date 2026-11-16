PY ?= python3

.PHONY: test run examples clean

test:
	$(PY) -m pytest

run:
	PYTHONPATH=src $(PY) -m lsystem fern -o fern.svg

examples:
	for p in fern bush weed tree random-shrub; do PYTHONPATH=src $(PY) -m lsystem $$p -o examples/$$p.svg; done

clean:
	rm -rf .pytest_cache build *.egg-info src/*.egg-info fern.svg
