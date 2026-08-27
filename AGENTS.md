# Agent Guide: EXPERIMENTAL-spec-kitty-events

This repo is part of the `EXPERIMENTAL-spec-kitty-*` programme. There is no pre-programme
branch ladder here: **`main` IS the integration branch** — every PR targets `main`,
nothing deploys on merge, and nothing on GitHub enforces anything (no branch protection,
no required reviews; there is no `.github/workflows/` directory — GitHub Actions are not used).
The binding process is the programme constitution —
[`EXPERIMENTAL-spec-kitty-planning/PROGRAM.md`](https://github.com/spec-kitty/EXPERIMENTAL-spec-kitty-planning/blob/main/PROGRAM.md) §5–§9:

- One issue → one branch (`issue-<n>-<slug>`, cut from `main`) → one PR targeting `main`.
  Never push to `main`; implementers never merge (§9).
- Run every test you write or change plus your blast radius, and record the commands and
  counts in the PR (§6). Do **not** run a whole-repo suite before opening the PR — that is
  the CI agent's job (`make test-full`).
- Exactly one adversarial-squad review per PR; `[MAJOR]` findings block, minors become
  issues (§7). On exe.dev VMs use `gh api repos/<owner>/<repo>/...`, not `gh pr` /
  `gh issue` (`bin/GH-API.md` in the planning repo).

## Commands

| Purpose | Command |
|---|---|
| Implementer blast-radius baseline | `make test-fast` |
| Whole suite with coverage — CI agent only | `make test-full` |
| Packaged conformance gate — every PR | `uv run pytest --pyargs spec_kitty_events.conformance` |
| Lint (whole repo, part of "Tests run") | `ruff check . && ruff format --check .` |

The conformance gate is the packaged contract other repos consume; the in-repo suite does
not collect it, so run it explicitly on every PR.
