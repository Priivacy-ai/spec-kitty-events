---
name: spec-kitty-worktree-guide
description: Hard-won lessons for working with spec-kitty worktrees, merges, and Python editable installs. Use whenever implementing, reviewing, or merging spec-kitty work packages.
user-invocable: false
---

# Spec-Kitty Worktree Survival Guide

Lessons learned from real spec-kitty feature implementations. These are problems you WILL hit — follow these rules to avoid them.

## 1. Editable Installs Break in Worktrees

**Problem:** Worktrees are fresh git checkouts — they do NOT inherit `pip install -e` from the main repo. Tests fail with `ModuleNotFoundError`.

**Rule:** After creating any worktree, immediately install the package:

```bash
cd .worktrees/<feature>-WP##/
python3.11 -m pip install -e ".[dev]"
```

**Also applies post-merge:** When worktrees are deleted during merge cleanup, the editable install still points to the deleted worktree path. You MUST reinstall from main after every merge:

```bash
cd /path/to/main/repo
python3.11 -m pip install -e ".[dev]"
```

## 2. Subtasks Must Be Marked Done Before Moving WP

**Problem:** `spec-kitty agent tasks move-task WP## --to for_review` fails if any subtasks (T001, T002...) are still unchecked.

**Rule:** Mark all subtasks done first:

```bash
spec-kitty agent tasks mark-status T001 T002 T003 --status done
```

## 3. Marking Subtasks Puts Worktree Behind Main

**Problem:** Marking subtasks as done commits to main. The worktree branch is now behind main. spec-kitty rejects status moves on stale branches.

**Rule:** Rebase after marking subtasks and before every status move:

```bash
cd .worktrees/<feature>-WP##/
git stash
git rebase main
git stash pop  # only if you had uncommitted changes
```

Expect to do this 2-3 times per WP lifecycle.

## 4. `.gitignore` Modifications Block Everything

**Problem:** If `.gitignore` was modified on main outside the workflow, worktrees inherit this as an uncommitted change. spec-kitty's pre-flight checks reject all status transitions.

**Rule:** Use `--force` when you know the only dirty file is `.gitignore`:

```bash
spec-kitty agent tasks move-task WP## --to for_review --force --note "..."
```

Or clean it manually:

```bash
git checkout -- .gitignore
```

## 5. Merge Pre-flight Requires Pristine State EVERYWHERE

**Problem:** `spec-kitty merge` checks ALL worktrees AND the main repo. It fails if ANY have uncommitted or untracked changes. Common offenders:
- Modified `.gitignore` in worktrees
- `.hypothesis/` directory from property tests
- Untracked files in main: `.claudeignore`, `.kittify/`, `.claude/`, `.codex/`

**Rule — Clean ALL worktrees first:**

```bash
# For each worktree
cd .worktrees/<feature>-WP##/
git checkout -- .gitignore
rm -rf .hypothesis/
```

**Rule — Clean main repo:**

```bash
cd /path/to/main/repo
git checkout -- .gitignore
git stash --include-untracked -m "temp stash for merge"
```

Note: plain `git stash` does NOT capture untracked files. You MUST use `--include-untracked`.

After merge succeeds:

```bash
git stash pop
```

## 6. WP Dependencies Require `--base` Flag

**Problem:** Implementing a WP that depends on another WP fails without specifying the base.

**Rule:**

```bash
spec-kitty agent workflow implement WP02 --base WP01 --agent <name>
```

## 7. Do NOT Automate Bulk Code Modifications

**Problem:** Scripts to bulk-modify source files (regex-based or AST-based) are fragile and have corrupted entire test suites. Regex matches too broadly (hits imports, other function calls). AST unparsing loses formatting.

**Rule:** Write each file individually. It takes longer but succeeds on the first try. Use parallel Write tool calls for efficiency — you can write all files in a single message.

If you must restore after a failed script:

```bash
git checkout -- tests/
```

## 8. Hypothesis Property Tests Need `deadline=None`

**Problem:** Hypothesis property tests that construct Pydantic models with `uuid.uuid4()` intermittently fail under pytest-cov coverage instrumentation. The default 200ms deadline is exceeded by Pydantic validation overhead.

**Rule:** Always add `@settings(deadline=None)` to property-based tests:

```python
from hypothesis import given, strategies as st, settings

@settings(deadline=None)
@given(st.lists(my_strategy(), min_size=1, max_size=10))
def test_my_property(self, items):
    ...
```

## 9. Add `.hypothesis/` to `.gitignore`

Running Hypothesis tests creates a `.hypothesis/` cache directory. If not gitignored, it shows up as an untracked file and blocks merge pre-flight.

Add to `.gitignore`:

```
# Hypothesis
.hypothesis/
```

## 10. Python Version Awareness

**Problem:** Multiple Python versions may be installed (e.g., 3.11 and 3.14). The default `python` may not be the one with your editable install.

**Rule:** Always use the explicit version:

```bash
python3.11 -m pytest tests/
python3.11 -m pip install -e ".[dev]"
```

Never use bare `python` or `python3`.

## Quick Reference: WP Lifecycle Checklist

```
[ ] Create worktree: spec-kitty agent workflow implement WP## --agent <name>
[ ] cd into worktree
[ ] Install: python3.11 -m pip install -e ".[dev]"
[ ] Implement changes
[ ] Run tests: python3.11 -m pytest tests/ -v
[ ] Commit: git add -A && git commit -m "feat(WP##): ..."
[ ] Mark subtasks: spec-kitty agent tasks mark-status T0## --status done
[ ] Rebase: git rebase main
[ ] Move to review: spec-kitty agent tasks move-task WP## --to for_review --note "..."
    (use --force if .gitignore is the only dirty file)
```

## Quick Reference: Merge Checklist

```
[ ] All WPs in "done" lane
[ ] Clean each worktree: git checkout -- .gitignore && rm -rf .hypothesis/
[ ] Clean main: git checkout -- .gitignore
[ ] Stash main untracked: git stash --include-untracked
[ ] Verify: git status --short shows empty in main AND all worktrees
[ ] Merge: spec-kitty merge --feature <feature-slug>
[ ] Pop stash: git stash pop
[ ] Reinstall: python3.11 -m pip install -e ".[dev]"
[ ] Verify: python3.11 -m pytest tests/ -v
```
