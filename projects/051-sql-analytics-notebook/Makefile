PY ?= python3

.PHONY: install run db notebook lab test clean

install:
	$(PY) -m pip install -e ".[dev,notebook]"

run:            ## print every analysis as a text table
	$(PY) -m analytics

db:             ## write penguins.sqlite for use with the sqlite3 CLI
	$(PY) -m analytics --db penguins.sqlite 01 >/dev/null && echo "wrote penguins.sqlite"

notebook:       ## regenerate and execute notebook.ipynb from sql/
	$(PY) build_notebook.py --execute

lab:
	jupyter lab notebook.ipynb

test:
	$(PY) -m pytest -q

clean:
	rm -rf penguins.sqlite .pytest_cache __pycache__ */__pycache__ *.egg-info .ipynb_checkpoints
