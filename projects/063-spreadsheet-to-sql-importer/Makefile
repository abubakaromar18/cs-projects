.PHONY: test run dry-run clean

test:
	python3 -m pytest

run:
	PYTHONPATH=src python3 -m sheet2sql examples/employees.csv --db example.db --if-exists replace

dry-run:
	PYTHONPATH=src python3 -m sheet2sql examples/employees.csv --dry-run

clean:
	rm -rf .pytest_cache build *.egg-info src/*.egg-info example.db
	find . -name __pycache__ -type d -exec rm -rf {} +
