# DKR-M1-02-EVENTS reproducible local Docker image contract for spec-kitty-events.
#
# GOVERNANCE (HIC-BOOT-012a out-of-fabric M1 prework):
#   Network access for build supply is authorized by HIC-M1-DOCKER-SUPPLY
#   (docs/decisions/HIC-M1-DOCKER-SUPPLY.md): "You can use network for anything
#   other than pushing code to the checked out repos." Base pulls and PyPI
#   installs are therefore normal `docker build` operations here - no
#   --pull=never / --network=none restriction applies to this build. The one
#   hard prohibition carried forward is: never git push/fetch/pull to a
#   checked-out product repo (structurally enforced elsewhere: zero remotes +
#   deny-push hooks).
#
#   Base is pinned by the pullable RepoDigest recorded in
#   docs/bootstrap/DKR-M1-01-DIGEST-CORRECTION.json for python:3.12-slim-bookworm
#   (sha256:46cb7cc2877e60fbd5e21a9ae6115c30ace7a077b9f8772da879e4590c18c2e3).
#
#   Runtime + dev/test dependencies (pydantic, python-ulid, jsonschema, pytest,
#   pytest-cov, hypothesis, mypy) are installed from PyPI via the project's own
#   ".[dev,conformance]" extras - no cross-image local-supply workaround is
#   needed now that network is authorized. hypothesis is available and the
#   property-based test files (tests/property/*.py + reducer/key tests) are
#   collected and run for real inside this build.

FROM python:3.12-slim-bookworm@sha256:46cb7cc2877e60fbd5e21a9ae6115c30ace7a077b9f8772da879e4590c18c2e3 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml LICENSE README.md CHANGELOG.md COMPATIBILITY.md RELEASE_NOTES.md SECURITY-POSITION.md ./
COPY src ./src
COPY tests ./tests
COPY contracts ./contracts

# Install the project with its full dev+conformance extras (pytest, pytest-cov,
# hypothesis, mypy, jsonschema) reproducibly from PyPI. requires-python>=3.10 is
# satisfied by the pinned 3.12 base; the extras versions are governed by the
# ranges declared in pyproject.toml [project.optional-dependencies].
RUN python3 -m pip install --no-deps -e . \
    && python3 -m pip install "pydantic>=2.0.0,<3.0.0" "python-ulid>=1.1.0" \
       "pytest>=7.0.0" "pytest-cov>=4.0.0" "hypothesis>=6.0.0" "mypy>=1.0.0" \
       "jsonschema>=4.21.0,<5.0.0" \
    && python3 -c "import spec_kitty_events, pydantic, pydantic_core, ulid, jsonschema, pytest, pytest_cov, coverage, hypothesis, mypy; print('import-check OK')"

# Freeze the resolved dependency closure for the handoff manifest.
RUN mkdir -p /app/docker && python3 -m pip freeze > /app/docker/dependency-manifest.txt

# Native gate: run the project's own pytest suite exactly as configured in
# pyproject.toml [tool.pytest.ini_options] (bare `pytest`, coverage addopts
# included). hypothesis is present, so the property-based suites run for real.
RUN python3 -m pytest

CMD ["python3", "-m", "pytest"]
