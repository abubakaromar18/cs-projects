CC      ?= cc
CFLAGS  ?= -std=c11 -Wall -Wextra -Wpedantic -O2 -g
CPPFLAGS = -Iinclude

BUILD   = build
LIBSRC  = src/compile.c src/vm.c
LIBOBJ  = $(LIBSRC:src/%.c=$(BUILD)/%.o)

.PHONY: all test examples bench sanitize valgrind clean

all: $(BUILD)/bf

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/%.o: src/%.c include/bf.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(BUILD)/bf: $(LIBOBJ) $(BUILD)/main.o
	$(CC) $(CFLAGS) $^ -o $@

$(BUILD)/test_bf: tests/test_bf.c $(LIBOBJ)
	$(CC) $(CPPFLAGS) $(CFLAGS) $^ -o $@

test: $(BUILD)/test_bf $(BUILD)/bf
	./$(BUILD)/test_bf
	./tests/cli_test.sh ./$(BUILD)/bf

examples: $(BUILD)/bf
	./$(BUILD)/bf examples/hello.bf
	echo "Hello, Brainfuck" | ./$(BUILD)/bf examples/reverse.bf

# Compare instruction counts and wall time across optimization levels.
bench: $(BUILD)/bf
	@for o in 0 1 2; do \
	  bash -c "time ./$(BUILD)/bf -O$$o -s examples/bench.bf > /dev/null" 2>&1 | grep -E 'bf:|real'; \
	done

sanitize: clean
	$(MAKE) test CFLAGS="-std=c11 -Wall -Wextra -g -fsanitize=address,undefined -fno-omit-frame-pointer"

valgrind: $(BUILD)/test_bf
	valgrind --leak-check=full --error-exitcode=1 -q ./$(BUILD)/test_bf

clean:
	rm -rf $(BUILD)
