VENV   ?= .venv
PYTHON ?= $(VENV)/bin/python

.PHONY: install test run openapi clean

$(VENV):
	python3 -m venv $(VENV)

install: $(VENV)
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

run:
	$(PYTHON) -m todo_api

# Write the OpenAPI document to openapi.json without starting a server.
openapi:
	$(PYTHON) -c "import json; from todo_api.main import app; print(json.dumps(app.openapi(), indent=2))" > openapi.json

clean:
	rm -rf $(VENV) .pytest_cache build *.egg-info src/*.egg-info openapi.json *.db
	find . -name __pycache__ -type d -exec rm -rf {} +
