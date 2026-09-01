.DEFAULT_GOAL := help

.PHONY: help test-fast test-full test-floor lint

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# The whole suite runs in ~16s without coverage and ~34s with it (2308 tests),
# so no subset split is worth having: both targets run everything.
test-fast: ## Run the whole suite without coverage (~16s) — the implementer blast-radius run
	uv run pytest --no-cov -q $(ARGS)

# GitHub Actions are off programme-wide (PROGRAM.md §2), so the .github/workflows/ci.yml
# 3.10/3.11/3.12 matrix never runs anywhere. test-floor is the one lane that actually
# exercises the `requires-python = ">=3.10"` floor pyproject.toml promises — without it,
# a version-sensitive guard (e.g. a trailing-Z datetime normalization that 3.12 accepts
# unaided) can pass on the default interpreter while being dead code on 3.10
# (spec-kitty-events#123). `uv run --python 3.10` downloads and caches the interpreter
# on first use. It is pinned to its own UV_PROJECT_ENVIRONMENT (.venv-floor) so it never
# replaces the default-interpreter `.venv` that test-full's own recipe line relies on —
# sharing .venv let `uv run --python 3.10` silently downgrade test-full's coverage run to
# 3.10 as well, dropping default-interpreter coverage entirely (squad finding on PR #130).
test-floor: ## Run the whole suite on the declared support floor (Python 3.10)
	UV_PROJECT_ENVIRONMENT=.venv-floor uv run --python 3.10.21 pytest --no-cov -q $(ARGS)

test-full: test-floor lint ## Run the whole suite with the configured coverage report — what the CI agent runs
	uv run pytest $(ARGS)

lint: ## Run the pinned ruff check gate, the formatter check, and the version-amendment guard
	uv run ruff check .
	uv run ruff format --check .
	uv run python scripts/check_version_not_amended.py
