.PHONY: install lint test

install:
	poetry install --no-root --with dev

lint:
	poetry run ruff check .
	poetry run ruff format --check .

test:
	poetry run pytest
