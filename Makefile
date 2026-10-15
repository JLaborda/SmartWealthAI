.PHONY: install install-credit install-investing lint test test-credit test-investing download-fundamentals format platform-tf-check

install:
	uv sync --frozen --group dev

install-credit:
	uv sync --frozen --package credit --group dev

install-investing:
	uv sync --frozen --package investing --group dev

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest --cov=investing --cov=credit --cov-branch --cov-report=term-missing

# uv run without --package re-syncs the full workspace (root depends on both
# members). Keep --package so credit-only / investing-only envs stay lean.
# Optional: make test-credit COV_ARGS='--cov-report=xml' (CI)
test-credit:
	uv run --frozen --package credit --group dev pytest credit/tests --cov=credit --cov-branch --cov-report=term-missing $(COV_ARGS)

test-investing:
	uv run --frozen --package investing --group dev pytest investing/tests --cov=investing --cov-branch --cov-report=term-missing $(COV_ARGS)

# Requires SEC_IDENTITY in the environment. See investing/docs/guides/download-fundamentals.md
download-fundamentals:
	uv run download-fundamentals --universe dow30

# formatting command
format:
	uv run ruff format .

# Terraform fmt + validate for credit CSS serve demo (no apply; no AWS creds required).
platform-tf-check:
	cd platform/terraform/credit-css-serve-demo && terraform fmt -check -recursive && terraform init -backend=false -input=false && terraform validate
