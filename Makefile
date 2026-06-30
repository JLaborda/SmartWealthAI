.PHONY: install lint test download-fundamentals docker-build

install:
	poetry install --with dev

lint:
	poetry run ruff check .
	poetry run ruff format --check .

test:
	poetry run pytest --cov=smartwealthai --cov-report=term-missing

docker-build:
	docker build -f Dockerfile -t smartwealthai-pipeline .

# Requires SEC_IDENTITY in the environment. See docs/mvp/guides/download-fundamentals.md
download-fundamentals:
	poetry run download-fundamentals --universe dow30

# formatting command
format:
	poetry run ruff format .