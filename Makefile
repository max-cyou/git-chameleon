.PHONY: install dev lint typecheck test run

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy src

test:
	pytest

run:
	git-chameleon