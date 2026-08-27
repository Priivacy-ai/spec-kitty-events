.DEFAULT_GOAL := help

.PHONY: help test-fast test-full lint

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# The whole suite runs in ~16s without coverage and ~34s with it (2308 tests),
# so no subset split is worth having: both targets run everything.
test-fast: ## Run the whole suite without coverage (~16s) — the implementer blast-radius run
	uv run pytest --no-cov -q $(ARGS)

test-full: ## Run the whole suite with the configured coverage report — what the CI agent runs
	uv run pytest $(ARGS)

# ruff format --check is intentionally not part of this target yet: the repo
# predates ruff and has never been run through its formatter (issue #12
# follow-up). `lint` covers the pinned, configured check gate only.
lint: ## Run the pinned, configured ruff check gate (see pyproject.toml [tool.ruff])
	uv run ruff check .
