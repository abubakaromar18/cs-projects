PYTHON ?= python3
RUN = PYTHONPATH=src $(PYTHON) -m spamfilter
UCI_URL = https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip

.PHONY: install dev test run demo data eval-full clean

install:          ## install the `spamfilter` command
	$(PYTHON) -m pip install .

dev:              ## editable install with test deps
	$(PYTHON) -m pip install -e '.[dev]'

test:             ## run the test suite
	$(PYTHON) -m pytest

run:              ## run from source, e.g. make run ARGS="predict 'free prize!'"
	$(RUN) $(ARGS)

demo:             ## cross-validate on the bundled sample and explain a message
	$(RUN) cv
	$(RUN) top -n 8
	$(RUN) explain "Congratulations! Text WIN to 80086 to claim your FREE £500 prize"

data:             ## download the full UCI SMS Spam Collection (5,574 messages)
	curl -fsSL -o data/smsspam.zip "$(UCI_URL)"
	cd data && unzip -o -q smsspam.zip SMSSpamCollection && rm smsspam.zip

eval-full: data/SMSSpamCollection   ## evaluate on the full dataset
	$(RUN) cv -d data/SMSSpamCollection -k 10

data/SMSSpamCollection:
	$(MAKE) data

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache model.json
	find . -name __pycache__ -type d -exec rm -rf {} +
