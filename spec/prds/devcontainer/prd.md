# PRD: Development Container for SmartWealthAI

## Problem Statement

SmartWealthAI development currently depends on the developer's local machine configuration (macOS, Homebrew packages, Python version, Poetry, AWS CLI, etc.). This creates two problems:

1. **Environment drift**: there is no guarantee that a fresh clone produces a working dev environment without manual setup steps.
2. **Cloud portability**: the architecture targets AWS (S3, ECS Fargate, ECR, Secrets Manager). The developer wants to be able to spin up an EC2 instance, clone the repo, open it in Cursor via SSH, and land in a fully functional dev environment identical to the local one -- with zero manual tool installation.

## Solution

Create a `.devcontainer/` configuration that packages the entire development toolchain (Python 3.11, Poetry, Docker, AWS CLI, GitHub CLI, system utilities, Cursor extensions) into a reproducible container. The developer opens the repo in Cursor (locally or via SSH to EC2), the container builds automatically, and all dependencies are ready.

This is a **development-only** image. A separate, minimal production Dockerfile will be created later for ECS Fargate tasks.

## User Stories

1. As a developer, I want to open the repo in Cursor and have all Python dependencies installed automatically, so that I can start coding immediately without running setup scripts.
2. As a developer, I want the same dev environment on my Mac and on a remote EC2 instance, so that I never debug environment-specific issues.
3. As a developer, I want Docker available inside my dev container, so that I can build and test production Docker images locally before pushing to ECR.
4. As a developer, I want the AWS CLI pre-installed, so that I can interact with S3, ECR, Secrets Manager, and other AWS services during development.
5. As a developer, I want the GitHub CLI pre-installed, so that I can create PRs, manage issues, and check CI status from the terminal.
6. As a developer, I want `make`, `jq`, and `ripgrep` available, so that I have standard dev utilities for task automation, JSON inspection, and fast code search.
7. As a developer, I want Cursor to auto-detect the Poetry virtualenv as the Python interpreter, so that I never have to manually select the right Python.
8. As a developer, I want linting and formatting (Ruff) configured out of the box, so that code quality is enforced from day one.
9. As a developer, I want pytest available, so that I can run tests inside the container.
10. As a developer, I want Jupyter notebook support in Cursor, so that I can work with the existing `.ipynb` files in `notebooks/`.
11. As a developer, I want Streamlit (8501) and MLflow (5000) ports forwarded automatically, so that I can access dashboards from my browser when working remotely.
12. As a developer, I want AWS credentials handled via `~/.aws` mount (local) or IAM Instance Profile (EC2), so that no secrets are baked into the container image.
13. As a developer, I want to rebuild the container after changing its config and land in an updated environment, so that the setup evolves with the project.
14. As a developer, I want the container to use bash as the default shell, so that scripts behave consistently across dev and CI environments.

## Implementation Decisions

### Image strategy

- **Dev-only container.** The devcontainer is not reused for CI/CD or production. A separate slim Dockerfile will be created later for ECS Fargate.
- **Base image:** `mcr.microsoft.com/devcontainers/python:3.11`. Provides a non-root `vscode` user, common utilities (git, curl, ssh, sudo), and native Cursor/VS Code remote compatibility.

### Devcontainer features (pre-built add-ons)

| Feature | Purpose |
|---|---|
| `ghcr.io/devcontainers/features/docker-in-docker` | Build and run Docker images inside the container |
| `ghcr.io/devcontainers/features/aws-cli` | Interact with AWS services (S3, ECR, Secrets Manager, etc.) |
| `ghcr.io/devcontainers/features/github-cli` | PR creation, issue management, CI status checks |

### System packages (via Dockerfile)

Installed on top of the base image via `apt-get`:

- `make` -- task automation
- `jq` -- JSON processing (SEC EDGAR data, AWS CLI output)
- `ripgrep` -- fast codebase search

### Python tooling

- **Poetry** installed via `pipx` (already available in the MS base image).
- `poetry config virtualenvs.in-project true` so `.venv` lives inside the workspace.
- `poetry install` runs as `postCreateCommand` to auto-install all dependencies on container creation.
- **pytest** and **ruff** added as dev dependencies in `pyproject.toml`.

### Cursor / VS Code customizations

**Extensions:**

| Extension ID | Purpose |
|---|---|
| `ms-python.python` | Python language support, IntelliSense, test discovery |
| `charliermarsh.ruff` | Linting + formatting |
| `ms-toolsai.jupyter` | Notebook support |

**Settings:**

| Setting | Value | Reason |
|---|---|---|
| `python.defaultInterpreterPath` | `${workspaceFolder}/.venv/bin/python` | Auto-select the Poetry venv |
| `python.terminal.activateEnvironment` | `true` | Auto-activate venv in terminals |

### Port forwarding

| Port | Service |
|---|---|
| 8501 | Streamlit dashboard |
| 5000 | MLflow tracking UI |

### Credentials strategy

- **Local (macOS):** mount `~/.aws` into the container (devcontainer mount config).
- **EC2:** IAM Instance Profile attached to the instance; AWS CLI picks it up via the metadata service automatically.
- **No secrets baked into the image.** Ever.

### Shell

- bash (Debian default). No zsh/oh-my-zsh customization.

### Data directory

- No special volume or mount config. `data/` is gitignored and stays empty on fresh clones. Data lives in S3 per the architecture; local `data/` is populated on demand by ETL bootstrap scripts.

## Testing Decisions

This is an infrastructure/tooling PRD, not a feature module. There is no application logic to unit-test. Validation is manual:

- **Smoke test:** build the container locally (`Dev Containers: Rebuild Container` in Cursor), verify Python version, Poetry venv, installed tools (`docker --version`, `aws --version`, `gh --version`, `make --version`, `jq --version`, `rg --version`), and that `pytest` and `ruff` are importable.
- **EC2 test:** spin up an EC2 instance, install Docker, clone the repo, open via Cursor SSH, verify the same smoke checks pass.
- **Extension test:** confirm Cursor shows the correct Python interpreter and that Ruff linting is active on `.py` files.

## Out of Scope

- **Production Dockerfile.** That is a separate effort aligned with the ECS Fargate runtime decision in the architecture doc.
- **CI/CD integration.** GitHub Actions has its own runner environment; the devcontainer is not used there.
- **Data provisioning.** No EBS volumes, S3 sync scripts, or seed data in the container.
- **GPU support.** Not needed for the MVP (no ML training workloads).
- **Custom shell (zsh/oh-my-zsh).** Can be added later if desired.
- **Prefect / MLflow server setup.** Those are runtime services, not dev environment concerns.
- **Ruff / pytest configuration** (rules, pyproject sections). Adding the packages is in scope; configuring them is a follow-up.

## Further Notes

- The devcontainer config is fully version-controlled under `.devcontainer/` and evolves with the project. Any team member (or the developer on a new machine) gets the same environment by opening the repo.
- The architecture doc (`spec/constitution/mission.md`) references GitHub Actions + ECR for Docker image builds. The devcontainer's Docker-in-Docker feature allows local testing of those images before pushing.
- This PRD does not create a feature spec under `spec/features/` because the devcontainer is developer tooling, not an MVP feature module. It is tracked as a standalone PRD.

## Files to Create or Modify

| File | Action |
|---|---|
| `.devcontainer/devcontainer.json` | Create -- main devcontainer configuration |
| `.devcontainer/Dockerfile` | Create -- system packages on top of MS base image |
| `pyproject.toml` | Modify -- add `pytest` and `ruff` as dev dependencies |
