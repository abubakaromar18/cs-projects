.PHONY: install test demo bench clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest

# Solve the bundled "hard" puzzle and show search statistics.
demo:
	PYTHONPATH=src python -m sudoku solve puzzles/hard.txt --stats

# Compare plain backtracking against constraint propagation.
bench:
	PYTHONPATH=src python -m sudoku bench puzzles/

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
