.PHONY: install lint test download-fundamentals

install:
	poetry install --with dev
	# ponytail: mlflow metadata pins pandas<3; logging/UI work with pandas 3 (fat pkg --no-deps)
	poetry run pip install "mlflow-skinny==2.22.5" -q
	poetry run pip install "mlflow==2.22.5" --no-deps -q

lint:
	poetry run ruff check .
	poetry run ruff format --check .

test:
	poetry run pytest --cov=smartwealthai --cov-report=term-missing

# Requires SEC_IDENTITY in the environment. See docs/mvp/guides/download-fundamentals.md
download-fundamentals:
	poetry run download-fundamentals --universe dow30

# formatting command
format:
	poetry run ruff format .