.PHONY: check compile test lint install uninstall

check: compile lint test

compile:
	python3 -m compileall -q src

lint:
	python3 -m ruff check src tests

test:
	PYTHONPATH=src python3 -m unittest discover -s tests

install:
	./install.sh

uninstall:
	./uninstall.sh
