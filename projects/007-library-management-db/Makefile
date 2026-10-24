PYTHON ?= python3
DB ?= library.db

.PHONY: install dev test demo run schema clean

install:          ## install the `library-db` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite
	$(PYTHON) -m pytest

run:              ## run from source, e.g. make run ARGS="catalog"
	PYTHONPATH=src $(PYTHON) -m library_db --db $(DB) $(ARGS)

demo:             ## fresh database with sample data, then a few reports
	rm -f $(DB)
	PYTHONPATH=src $(PYTHON) -m library_db --db $(DB) seed
	PYTHONPATH=src $(PYTHON) -m library_db --db $(DB) catalog
	PYTHONPATH=src $(PYTHON) -m library_db --db $(DB) overdue
	PYTHONPATH=src $(PYTHON) -m library_db --db $(DB) popular

schema:           ## print the DDL
	cat src/library_db/schema.sql

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache $(DB)
	find . -name __pycache__ -type d -exec rm -rf {} +
