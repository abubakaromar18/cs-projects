PYTHON ?= python3

.PHONY: install dev test run cli stats clean

install:          ## install the `tictactoe` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite (headless: pygame uses a dummy video driver)
	SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy $(PYTHON) -m pytest

run:              ## open the pygame window
	PYTHONPATH=src $(PYTHON) -m tictactoe $(ARGS)

cli:              ## play in the terminal
	PYTHONPATH=src $(PYTHON) -m tictactoe --cli $(ARGS)

stats:            ## minimax vs alpha-beta node counts
	PYTHONPATH=src $(PYTHON) -m tictactoe --stats

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
