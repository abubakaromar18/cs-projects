# Host build for the portable core: unit tests and a desktop simulator.
# The Arduino sketch itself is built with arduino-cli (see `make arduino`).

CXX      ?= g++
CXXFLAGS ?= -std=c++11 -O2 -Wall -Wextra -Wpedantic -Werror
SRC_DIR  := SensorLogger/src
BUILD    := build
CORE_SRC := $(wildcard $(SRC_DIR)/*.cpp)
HEADERS  := $(wildcard $(SRC_DIR)/*.h)
FQBN     ?= arduino:avr:uno
PORT     ?= /dev/ttyACM0

.PHONY: all test test-cpp test-py sim arduino upload clean

all: test

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/tests: tests/test_main.cpp $(CORE_SRC) $(HEADERS) | $(BUILD)
	$(CXX) $(CXXFLAGS) -I$(SRC_DIR) tests/test_main.cpp $(CORE_SRC) -o $@ -lm

$(BUILD)/simulate: tools/simulate.cpp $(CORE_SRC) $(HEADERS) | $(BUILD)
	$(CXX) $(CXXFLAGS) -I$(SRC_DIR) tools/simulate.cpp $(CORE_SRC) -o $@ -lm

test: test-cpp test-py

test-cpp: $(BUILD)/tests
	./$(BUILD)/tests

test-py:
	python3 -m unittest discover -s tests -p 'test_*.py' -v

sim: $(BUILD)/simulate
	./$(BUILD)/simulate 10

# Cross-compile for a real board (requires arduino-cli and the AVR core:
#   arduino-cli core install arduino:avr).
arduino:
	arduino-cli compile --fqbn $(FQBN) SensorLogger

upload: arduino
	arduino-cli upload --fqbn $(FQBN) --port $(PORT) SensorLogger

clean:
	rm -rf $(BUILD)
