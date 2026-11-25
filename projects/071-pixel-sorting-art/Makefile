.PHONY: install test demo clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest

demo:
	PYTHONPATH=src python -m pixelsort.cli --demo plasma -o out/demo.png --key hue --interval threshold --lower 0.25 --upper 0.8 --angle 90

clean:
	rm -rf out build *.egg-info src/*.egg-info .pytest_cache
