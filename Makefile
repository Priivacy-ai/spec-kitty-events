.DEFAULT_GOAL := help

.PHONY: help test-fast test-full test-full-310 lint

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# The whole suite runs in ~16s without coverage and ~34s with it (2308 tests),
# so no subset split is worth having: both targets run everything.
test-fast: ## Run the whole suite without coverage (~16s) — the implementer blast-radius run
	uv run pytest --no-cov -q $(ARGS)

# requires-python floor is 3.10, but every other target runs on whatever the
# dev/CI machine's default `uv run` resolves to (3.12+ here) — datetime.fromisoformat
# grew looser trailing-'Z' and precision handling in 3.11, so a normalization bug that
# only breaks 3.10 is invisible to those targets (#141). This lane pins
# 3.10 for exactly the modules that hand-roll Z-suffix ISO-8601 normalization to work
# around that gap. --isolated keeps it off the default .venv used by test-fast/test-full.
TIMESTAMP_PARSING_TESTS := \
	tests/unit/test_strict.py \
	tests/unit/test_retrospective.py \
	tests/unit/test_zeitgeist_attrs.py \
	tests/test_timestamp_semantics_conformance.py \
	tests/test_zeitgeist_attrs_conformance.py

test-full-310: ## Run the timestamp-parsing tests on Python 3.10, the declared floor
	uv run --isolated --python 3.10.21 pytest --no-cov -q $(TIMESTAMP_PARSING_TESTS)

test-full: test-full-310 lint ## Run the whole suite with the configured coverage report — what the CI agent runs
	uv run pytest $(ARGS)

lint: ## Run the pinned ruff check gate plus the formatter check (see pyproject.toml [tool.ruff])
	uv run ruff check .
	uv run ruff format --check .
