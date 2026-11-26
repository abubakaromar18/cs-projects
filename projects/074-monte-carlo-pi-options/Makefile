.PHONY: install test demo clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest

demo:
	PYTHONPATH=src python -m montecarlo pi --samples 1000000 --seed 42
	PYTHONPATH=src python -m montecarlo option --spot 100 --strike 105 --rate 0.05 --vol 0.2 --maturity 1 --seed 42
	PYTHONPATH=src python -m montecarlo convergence --seed 7

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
