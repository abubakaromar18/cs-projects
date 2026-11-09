CC      ?= cc
CFLAGS  ?= -O2
override CFLAGS += -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Iinclude
LDLIBS  := -lm

BUILD   := build
LIB_SRC := src/sieve.c src/eratosthenes.c src/atkin.c src/segmented.c
LIB_OBJ := $(LIB_SRC:src/%.c=$(BUILD)/%.o)
HEADERS := include/sieve.h

.PHONY: all test sanitize bench clean

all: $(BUILD)/primes

$(BUILD)/primes: $(LIB_OBJ) $(BUILD)/main.o
	$(CC) $(CFLAGS) $^ -o $@ $(LDLIBS)

$(BUILD)/test_sieve: $(LIB_OBJ) tests/test_sieve.c $(HEADERS)
	$(CC) $(CFLAGS) $(LIB_OBJ) tests/test_sieve.c -o $@ $(LDLIBS)

$(BUILD)/%.o: src/%.c $(HEADERS) | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD):
	mkdir -p $@

test: $(BUILD)/test_sieve
	$(BUILD)/test_sieve

# Rebuilds from scratch with AddressSanitizer and UBSan enabled.
sanitize: clean
	$(MAKE) test CFLAGS="-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer"

bench: $(BUILD)/primes
	$(BUILD)/primes bench

clean:
	rm -rf $(BUILD)
