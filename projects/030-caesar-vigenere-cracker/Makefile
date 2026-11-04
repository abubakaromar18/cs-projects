PYTHON ?= python3
RUN = PYTHONPATH=src $(PYTHON) -m cipherbreak

.PHONY: install dev test run demo clean

install:          ## install the `cipherbreak` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite
	$(PYTHON) -m pytest

run:              ## run from source, e.g. make run ARGS="crack-caesar -f examples/caesar.txt"
	$(RUN) $(ARGS)

demo:             ## crack both sample ciphertexts
	$(RUN) analyze -f examples/vigenere.txt
	$(RUN) crack-caesar -f examples/caesar.txt --top 3
	$(RUN) crack-vigenere -f examples/vigenere.txt --explain

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
