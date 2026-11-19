# Makefile for the wc clone.
#   make            build ./wc
#   make test       build and run unit + CLI tests
#   make valgrind   run unit tests under valgrind (if installed)
#   make clean

CC      ?= cc
CFLAGS  ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wno-sign-conversion
CPPFLAGS += -D_POSIX_C_SOURCE=200809L -Isrc

LIB_SRC  = src/counts.c src/options.c src/report.c
LIB_OBJ  = $(LIB_SRC:.c=.o)

.PHONY: all test unit cli valgrind clean

all: wc

wc: src/main.o $(LIB_OBJ)
	$(CC) $(CFLAGS) -o $@ $^

tests/test_unit: tests/test_unit.o $(LIB_OBJ)
	$(CC) $(CFLAGS) -o $@ $^

%.o: %.c src/*.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

test: unit cli

unit: tests/test_unit
	./tests/test_unit

cli: wc
	sh tests/cli_test.sh ./wc

valgrind: tests/test_unit wc
	valgrind --error-exitcode=1 --leak-check=full -q ./tests/test_unit
	printf 'a b\nc\n' | valgrind --error-exitcode=99 --leak-check=full -q ./wc - /nonexistent || test $$? -eq 1

clean:
	rm -f wc tests/test_unit src/*.o tests/*.o
