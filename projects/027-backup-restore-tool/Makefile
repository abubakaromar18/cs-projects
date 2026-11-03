# Makefile for bkp. Everything is plain bash; no build step is needed.
PREFIX ?= $(HOME)/.local
SHELL_FILES := bin/bkp lib/*.sh tests/*.sh

.PHONY: test lint check install uninstall demo

test:            ## run the test suite
	@tests/run_tests.sh

lint:            ## static analysis (requires shellcheck)
	shellcheck -x $(SHELL_FILES)

check: lint test

install:         ## install to $(PREFIX)/share/bkp and symlink bin/bkp
	mkdir -p $(PREFIX)/share/bkp $(PREFIX)/bin
	cp -R bin lib $(PREFIX)/share/bkp/
	ln -sf $(PREFIX)/share/bkp/bin/bkp $(PREFIX)/bin/bkp

uninstall:
	rm -rf $(PREFIX)/share/bkp $(PREFIX)/bin/bkp
