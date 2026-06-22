<!-- Copyright (c) 2026 @wimwian -->
<!-- SPDX-License-Identifier: MIT -->
<!-- https://github.com/wimwian-org/t2t -->
# Tooling

Minimum versions required to work on this project. Pinned versions reflect what is running in CI.

---

## Runtime

| Tool | Minimum | Notes |
|------|---------|-------|
| Python | **3.15** | `requires-python = ">=3.15"` in `pyproject.toml`; `tomllib` and other stdlib features used |
| uv | **0.11** | Package manager, virtualenv, lock-file management — do not use pip or poetry |

Install Python via [pyenv](https://github.com/pyenv/pyenv) or [asdf](https://asdf-vm.com). uv manages the `.venv` automatically; never activate it manually.

---

## Build toolchain

| Tool | Minimum | Role |
|------|---------|------|
| uv | **0.11** | `uv build` produces the sdist + wheel via setuptools backend |
| setuptools | **70** | Build backend declared in `pyproject.toml` |
| Node.js | **22** | Required only for `npx prettier` post-processing of CSS output |
| npx / prettier | **3.8** | Formats the four emitted CSS files after conversion; skipped with a warning if absent |

`uv build` is the only supported build command. Do not call `python -m build` or `pip wheel` directly.

---

## Linting & formatting

t2t has no mandatory Python linter configured today. The project relies on test coverage and code review rather than a linter gate.

| Tool | Minimum | Role |
|------|---------|------|
| prettier | **3.8** | Formats CSS output at runtime (not a dev-time linter) |

When a linter is added (e.g. ruff), it will be declared in `[dependency-groups] dev` and wired into CI alongside pytest.

---

## Testing

| Tool | Minimum | Role |
|------|---------|-------|
| pytest | **8** | Test runner |
| pytest-cov | **7.1** | Coverage plugin; enforces `--cov-fail-under=100` |
| coverage | **7** | Underlying measurement engine used by pytest-cov |

Run the full suite:

```bash
uv run pytest                              # coverage enforced
uv run pytest --cov-report=term-missing   # show uncovered lines
```

See [testing.md](testing.md) for conventions and pass criteria.

---

## Release & changelog

| Tool | Minimum | Role |
|------|---------|------|
| towncrier | **25.8** | Compiles `changelog.d/*.md` fragments into `CHANGELOG.md` at release time |
| git-flow | **0.4** | Branch workflow automation (`git flow feature/release/hotfix`) |
| gh (GitHub CLI) | — | Creating releases, setting branch defaults; no minimum pinned |

Changelog fragments go in `changelog.d/` with the naming convention `<issue>.<type>.md` where `<type>` is one of `feature`, `bugfix`, `doc`, `removal`.

See [gitflow.md](gitflow.md) for the full release process.

---

## Application dependencies

| Package | Minimum | Role |
|---------|---------|------|
| csscompressor | **0.9.5** | Minifies CSS output; pure-Python, no native extensions |

Runtime dependencies are intentionally minimal. t2t uses only the Python standard library and `csscompressor`. New runtime dependencies require explicit justification — prefer stdlib or inline implementation.
