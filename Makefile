.PHONY: install lint test download-fundamentals format platform-tf-check

install:
	poetry install --with dev

lint:
	poetry run ruff check .
	poetry run ruff format --check .

test:
	poetry run pytest --cov=smartwealthai --cov=credit --cov-branch --cov-report=term-missing

# Requires SEC_IDENTITY in the environment. See docs/mvp/guides/download-fundamentals.md
download-fundamentals:
	poetry run download-fundamentals --universe dow30

# formatting command
format:
	poetry run ruff format .

# Terraform fmt + validate for credit CSS serve demo (no apply; no AWS creds required).
platform-tf-check:
	cd platform/terraform/credit-css-serve-demo && terraform fmt -check -recursive && terraform init -backend=false -input=false && terraform validate