.PHONY: install lint test download-fundamentals format platform-tf-check

install:
	uv sync --frozen --group dev

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest --cov=investing --cov=credit --cov-branch --cov-report=term-missing

# Requires SEC_IDENTITY in the environment. See investing/docs/guides/download-fundamentals.md
download-fundamentals:
	uv run download-fundamentals --universe dow30

# formatting command
format:
	uv run ruff format .

# Terraform fmt + validate for credit CSS serve demo (no apply; no AWS creds required).
platform-tf-check:
	cd platform/terraform/credit-css-serve-demo && terraform fmt -check -recursive && terraform init -backend=false -input=false && terraform validate
