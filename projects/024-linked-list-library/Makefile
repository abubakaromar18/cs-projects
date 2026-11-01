CC      ?= cc
CFLAGS  ?= -std=c11 -Wall -Wextra -Wpedantic -O2 -g
CPPFLAGS = -Iinclude
AR      ?= ar

BUILD   = build
SRC     = src/ll_common.c src/slist.c src/dlist.c
OBJ     = $(SRC:src/%.c=$(BUILD)/%.o)
LIB     = $(BUILD)/liblinkedlist.a

.PHONY: all lib test demo valgrind sanitize clean

all: lib demo

lib: $(LIB)

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/%.o: src/%.c include/*.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(LIB): $(OBJ)
	$(AR) rcs $@ $^

$(BUILD)/test_%: tests/test_%.c tests/test_util.h $(LIB)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LIB) -o $@

$(BUILD)/demo: examples/demo.c $(LIB)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LIB) -o $@

demo: $(BUILD)/demo
	./$(BUILD)/demo

test: $(BUILD)/test_slist $(BUILD)/test_dlist
	./$(BUILD)/test_slist
	./$(BUILD)/test_dlist

# Run the test binaries under valgrind to catch leaks and invalid accesses.
valgrind: $(BUILD)/test_slist $(BUILD)/test_dlist
	valgrind --leak-check=full --error-exitcode=1 -q ./$(BUILD)/test_slist
	valgrind --leak-check=full --error-exitcode=1 -q ./$(BUILD)/test_dlist

# Rebuild everything with AddressSanitizer + UBSan and run the tests.
sanitize: clean
	$(MAKE) test CFLAGS="-std=c11 -Wall -Wextra -g -fsanitize=address,undefined -fno-omit-frame-pointer"

clean:
	rm -rf $(BUILD)
