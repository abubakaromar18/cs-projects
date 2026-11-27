.PHONY: install test demo clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest

# Builds a throwaway messy folder and previews how it would be organized.
demo:
	rm -rf /tmp/fileorg-demo && mkdir -p /tmp/fileorg-demo
	cd /tmp/fileorg-demo && touch photo.JPG notes.txt report.pdf song.mp3 script.py archive.zip mystery.xyz
	PYTHONPATH=src python -m fileorg organize /tmp/fileorg-demo --by type --dry-run

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
