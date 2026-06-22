<!-- Copyright (c) 2026 @wimwian -->
<!-- SPDX-License-Identifier: MIT -->
<!-- https://github.com/wimwian-org/t2t -->
# Git Flow + Worktree Process

## Branch model

| Branch | Lives for | Cut from | Merges into | Notes |
|--------|-----------|----------|-------------|-------|
| `master` | Forever | — | — | Production. Every commit tagged. |
| `dev` | Forever | `master` (once) | — | Integration. Default working branch. |
| `feature/<slug>` | A feature | `dev` | `dev` | Standard development work. |
| `bugfix/<slug>` | A fix during release | `release/*` | `release/*` | Only while a release branch exists. |
| `release/vX.Y.Z` | Until released | `dev` | `master` + `dev` | Where version bump runs. |
| `hotfix/vX.Y.Z` | Until released | `master` | `master` + `dev` | Emergency patch on production. |

Branch names: `feature/dsl-alpha-support`, `hotfix/v0.2.1`, `release/v0.3.0`. Tag names use `v` prefix.

## Branch protection

### Rules (enforced on GitHub)

| Branch | Push | PR required | Force-push | Delete |
|--------|------|-------------|------------|--------|
| `master` | Owner only via fast-forward from `dev` | No — fast-forward push | Never | Never |
| `dev` | Owner only via PR merge | Yes | Never | Never |

**Never push directly to `master` or `dev`.** Both branches are protected with admin enforcement on — no one bypasses, including the repo owner, except through the defined flows below.

### How each branch advances

**`dev`** — merges only from `feature/*`, `bugfix/*`, `release/*`, or `hotfix/*` via PR. The PR must pass CI (all tests, 100% coverage) before merge. Direct commits to `dev` are blocked.

**`master`** — fast-forwarded from `dev` only, never via PR (a PR merge commit would make `master` one commit ahead of `dev`, breaking the invariant). After a release is tagged on `master`, push with:

```bash
git push origin dev:master   # fast-forward only; rejected if master is not an ancestor of dev
git push origin --tags       # push the version tag
```

### Do's and don'ts

**Do:**
- Always branch from `dev` for new work: `git flow feature start <slug>`
- Commit on `feature/*`, push to remote, open a PR to `dev`
- Run `uv run pytest` locally before pushing — CI will catch failures but fast feedback is better
- Use `git flow feature finish` only from the primary checkout (where `dev` lives), not from a worktree
- Delete merged branches after the PR closes

**Don't:**
- `git push origin master` — direct push to master is rejected; use the fast-forward flow
- `git push --force` to any branch — ever
- Commit directly on `dev` or `master`
- Open a PR from `feature/*` directly to `master`
- Rebase a branch that has already been pushed and shared — creates diverged history for anyone who pulled it
- Merge without a passing CI run

### CI gate (what must pass before merge to `dev`)

```
uv run pytest          # 100% coverage required (enforced by --cov-fail-under=100)
```

---

## Day-to-day: features

```bash
# Start
git flow feature start dsl-alpha-support
# (plain git: git switch -c feature/dsl-alpha-support dev)

# Work, commit, repeat
git add t2t/dsl.py tests/test_dsl.py
git commit -m "feat: support alpha in ramp() DSL"

# Finish — merges into dev, deletes the branch
git flow feature finish dsl-alpha-support
# (plain git: git switch dev && git merge --no-ff feature/dsl-alpha-support && git branch -d feature/dsl-alpha-support)
```

## Releases

```bash
git flow release start v0.3.0
# (plain git: git switch -c release/v0.3.0 dev)

# Compile changelog fragments into CHANGELOG.md, bump version in pyproject.toml, run tests
uv run towncrier build --version 0.3.0
# edit pyproject.toml: version = "0.3.0"
uv run pytest
git commit -am "chore(release): v0.3.0"

git flow release finish v0.3.0
# (plain git: git switch master && git merge --no-ff release/v0.3.0 && git tag -a v0.3.0 -m "v0.3.0"
#             git switch dev && git merge --no-ff release/v0.3.0 && git branch -d release/v0.3.0)

git push origin master dev --tags
# The v* tag push triggers .github/workflows/release.yml → builds and publishes to PyPI
```

## Hotfixes

```bash
git flow hotfix start v0.2.1
# fix the issue, add a changelog.d/<issue>.bugfix.md fragment
uv run towncrier build --version 0.2.1
# edit pyproject.toml: version = "0.2.1"
uv run pytest
git commit -am "chore(release): v0.2.1"
git flow hotfix finish v0.2.1
git push origin master dev --tags
# The v* tag push triggers .github/workflows/release.yml → builds and publishes to PyPI
```

---

## Worktrees for parallel / multi-agent sessions

Multiple Claude Code sessions on the same checkout collide on `HEAD`. One session does `git switch feature/foo`, another does `git switch feature/bar`, and now neither knows which branch they're on — files get committed to the wrong branch.

The fix is **git worktrees**: separate working directories that share one `.git`. Each session pins its own branch.

### Layout

```
t2t/                          ← primary checkout (this repo)
│   └── .git/                 ← the one real git dir
t2t.worktrees/                ← sibling directory — all session worktrees live here
    ├── dsl-alpha/            ← worktree on feature/dsl-alpha-support
    └── gamut-fix/            ← worktree on feature/gamut-fix
```

Keeping worktrees **outside** the repo avoids them appearing in `git status` and confusing IDE indexers.

### Helper: `bin/wt`

```bash
# Start a new feature in its own worktree (cuts feature/dsl-alpha from dev)
bin/wt feature dsl-alpha
cd ../t2t.worktrees/dsl-alpha
uv sync          # .venv is per-worktree; uv's shared cache makes this fast

# Pick up an existing branch
bin/wt start feature/gamut-fix
cd ../t2t.worktrees/gamut-fix
uv sync

# List all worktrees
bin/wt list

# Remove a worktree when done (BEFORE git flow feature finish)
bin/wt rm dsl-alpha
```

### Multi-agent session pattern

```bash
# Terminal 1 — primary checkout, stays on dev
# (used for git flow finish operations and quick checks)
cd /path/to/t2t
claude

# Terminal 2 — agent working on feature/dsl-alpha
bin/wt feature dsl-alpha
cd ../t2t.worktrees/dsl-alpha
uv sync
claude

# Terminal 3 — agent working on feature/gamut-fix
bin/wt feature gamut-fix
cd ../t2t.worktrees/gamut-fix
uv sync
claude
```

Each session has its own `HEAD`, its own `.venv`, and its own working directory. They cannot reset each other.

When spawning **sub-agents** from inside a Claude Code session, prefer the built-in `isolation: "worktree"` option on the Agent tool — the harness creates and cleans up a temp worktree automatically. Use `bin/wt` for top-level sessions you manage by hand.

### Finishing a worktree session

Order matters:

```bash
# 1. Push from the worktree
cd ../t2t.worktrees/dsl-alpha
git push origin feature/dsl-alpha

# 2. Move to primary (where dev lives)
cd /path/to/t2t

# 3. Remove the worktree FIRST — git flow finish deletes the branch,
#    which fails if the branch is still checked out in any worktree
bin/wt rm dsl-alpha

# 4. Finish from primary
git flow feature finish dsl-alpha
```

### Constraints

1. **A branch can only be checked out in one worktree at a time.** If `feature/foo` is in the primary checkout, `bin/wt start feature/foo` fails. Switch primary to `dev` first.
2. **Keep `dev` and `master` in the primary checkout.** `git flow … finish` checks out `dev`/`master` to merge. If they're pinned to a worktree, the finish fails.
3. **One `.venv` per worktree.** uv's content-addressable cache makes this nearly free (packages are hardlinked), but `uv sync` must run once in each new worktree.
4. **Don't open two sessions on the same worktree.** That's the original problem in miniature.

### Recovery

```bash
git worktree list           # see every worktree and its branch
git worktree prune          # drop stale entries for manually-deleted directories
git worktree remove <path>  # correct way to delete (refuses if uncommitted changes)
```

## Quick reference

```bash
# new feature (in a worktree)
bin/wt feature <slug>
cd ../t2t.worktrees/<slug> && uv sync
# … work, commit, push …
cd /path/to/t2t
bin/wt rm <slug>
git flow feature finish <slug>

# release
git flow release start vX.Y.Z
uv run towncrier build --version X.Y.Z
# edit pyproject.toml version
uv run pytest
git commit -am "chore(release): vX.Y.Z"
git flow release finish vX.Y.Z
git push origin master dev --tags   # tag push triggers PyPI publish

# hotfix
git flow hotfix start vX.Y.Z
# … fix, add changelog.d/<issue>.bugfix.md …
uv run towncrier build --version X.Y.Z
# edit pyproject.toml version
git commit -am "chore(release): vX.Y.Z"
git flow hotfix finish vX.Y.Z
git push origin master dev --tags   # tag push triggers PyPI publish
```
