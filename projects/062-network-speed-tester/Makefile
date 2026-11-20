.PHONY: test demo serve clean

test:
	python3 -m pytest

demo:
	PYTHONPATH=src python3 -m netspeed demo -t 1

serve:
	PYTHONPATH=src python3 -m netspeed serve

clean:
	rm -rf .pytest_cache build *.egg-info src/*.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} +
