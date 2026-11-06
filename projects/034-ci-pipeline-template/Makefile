# Run the same steps locally that CI runs remotely.
.PHONY: install lint format test build ci clean actionlint

install:
	python -m pip install -e ".[test]" ruff build

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .
	ruff check --fix .

test:
	python -m pytest --cov=slugkit --cov-report=term-missing --cov-fail-under=90

build:
	python -m build

# Optional: statically check workflow files (https://github.com/rhysd/actionlint)
actionlint:
	actionlint .github/workflows/*.yml

ci: lint test build

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache .ruff_cache .coverage coverage.xml
