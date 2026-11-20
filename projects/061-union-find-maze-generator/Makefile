.PHONY: test run svg clean

test:
	python3 -m pytest

run:
	PYTHONPATH=src python3 -m ufmaze -r 10 -c 20 -s 7 --solve astar --stats

svg:
	PYTHONPATH=src python3 -m ufmaze -r 30 -c 50 -s 7 --solve bfs --svg maze.svg > /dev/null

clean:
	rm -rf .pytest_cache build *.egg-info src/*.egg-info maze.svg
	find . -name __pycache__ -type d -exec rm -rf {} +
