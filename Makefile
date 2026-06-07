.PHONY: install lint test download-fundamentals

install:
	poetry install --with dev

lint:
	poetry run ruff check .
	poetry run ruff format --check .

test:
	poetry run pytest

# Requires SEC_IDENTITY in the environment. See docs/mvp/guides/download-fundamentals.md
download-fundamentals:
	poetry run download-fundamentals --universe dow30
