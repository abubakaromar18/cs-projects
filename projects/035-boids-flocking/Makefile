# Boids Flocking — convenience targets.
SKETCH := $(CURDIR)/BoidsFlocking

.PHONY: run export test clean

run:            ## open the sketch window (needs processing-java on PATH)
	processing-java --sketch=$(SKETCH) --run

export:         ## build a standalone app into ./out
	processing-java --sketch=$(SKETCH) --output=$(CURDIR)/out --force --export

test:           ## unit-test the simulation core with JUnit 5
	mvn -q test

clean:
	rm -rf target out
