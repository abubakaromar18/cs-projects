.PHONY: install test run eval clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest

run:
	PYTHONPATH=src python -m intentbot

eval:
	PYTHONPATH=src python -m intentbot --eval

clean:
	rm -rf .pytest_cache build dist src/*.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} +
