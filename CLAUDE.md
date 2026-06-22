<!-- Copyright (c) 2026 @wimwian -->
<!-- SPDX-License-Identifier: MIT -->
<!-- https://github.com/wimwian-org/t2t -->
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Child docs:

- [.claude/karpathy.md](.claude/karpathy.md) — Behavioral guidelines (think before coding, minimal changes)
- [.claude/process.md](.claude/process.md) — Plan-before-execute discipline
- [.claude/testing.md](.claude/testing.md) — pytest conventions and coverage
- [.claude/gitflow.md](.claude/gitflow.md) — Branching model + worktree workflow for parallel/multi-agent sessions
- [.claude/tooling.md](.claude/tooling.md) — Minimum tool versions (runtime, build, test, release, deps)

---

## Local setup

`.env` is a symlink to `~/.ssh/.env.wimwian-org` (GitHub token for the wimwian-org). On a new checkout, recreate it:

```bash
ln -sf ~/.ssh/.env.wimwian-org .env
```

The file is gitignored. Never commit credentials.

---

## Commands

```bash
uv sync                                          # install runtime + dev deps
uv run pytest                                    # full test suite
uv run pytest tests/test_color.py               # single test file
uv run pytest tests/test_color.py::TestParse    # single test class
uv run pytest --cov=t2t --cov-report=term-missing  # with coverage
uv run pdoc t2t -o docs                         # regenerate HTML docs
uv run t2t -i sample.toml -d                    # dry-run against sample config
```

---

## Architecture

t2t is a single-package CLI (`t2t/`) that reads a `.toml` design token file and emits four Tailwind v4–compatible CSS files.

### Data flow

```
TOML file
  └─ tomllib.load()
       ├─ palette.build_palette_map()     → palette_map  (name → base oklch)
       ├─ tokens.build_token_maps()       → light_map, dark_map  (CSS var → oklch)
       │     ├─ dsl.resolve_color()       resolves ramp() DSL strings
       │     └─ gamut.check_gamut()       hard-exits if >20% outside sRGB
       ├─ contrast.validate_contrast()    hard-exits if any pair fails WCAG AA
       └─ render.*()                      → CSS strings
            └─ main.convert_split()      bundles into {theme, typography, utilities, wimwian}
```

`main.py` orchestrates everything. `convert()` (single-file output) and `convert_split()` (four-file output) are the two entry points; the CLI uses `convert_split`.

### Module responsibilities

| Module | Role |
|--------|------|
| `color.py` | Parse/format oklch strings; `color_ramp(base, step)` — the ramp from step 0 (black) through step 500 (base) to step 1000 (white) |
| `gamut.py` | oklch → oklab → linear sRGB; `check_gamut()` validates every resolved color |
| `dsl.py` | Resolves `ramp(palette, step[, alpha])` DSL strings at conversion time |
| `palette.py` | Builds `palette_map` (name → base oklch) from `[[palette]]` entries |
| `tokens.py` | Resolves `[[token]]` entries into `light_map` / `dark_map`; auto-derives dark as `1000 - light` for integer steps |
| `contrast.py` | WCAG contrast ratio; validates `[[contrast]]` pairs in both themes |
| `typography.py` | Derives `line-height` and `letter-spacing` from font-size when not explicitly provided |
| `render.py` | One function per CSS output section; returns `""` when section is empty |
| `output.py` | Builds the stderr token/contrast summary table and the `report.md` file |

### Dark mode implementation

t2t uses the CSS space-toggle trick — no JavaScript, no media queries, no duplicated property values:

```css
:root             { --L: initial; --D: ; }
[data-theme=dark] { --L: ; --D: initial; }

--color-surface: var(--L, oklch(91% 0.04 260)) var(--D, oklch(11% 0.04 260));
```

The `[data-theme='dark']` block only flips `--L`/`--D`; individual token values are **not** repeated there. `render_dark()` emits only the toggle flip; all token values are in `:root`.

### Token resolution rules

- Integer `light` value → requires `palette` field → calls `color_ramp(palette_base, step)`
- `ramp(name, step[, alpha])` string → resolved via `dsl.resolve_ramp_dsl()`
- Raw `oklch(...)` string → passed through unchanged
- `var(--...)` string → pass-through pointer token; no dark variant generated
- `dark` omitted → auto-derived as `1000 - light` for int steps, `ramp(pal, 1000-N)` for DSL; raw oklch/CSS vars get no auto-dark

### Output files (from `convert_split`)

| File | Contents |
|------|----------|
| `wimwian.css` | `@import "tailwindcss"` + imports for the three below |
| `theme.css` | `@font-face` blocks, `:root` custom properties, dark-mode flip |
| `typography.css` | `@utility` blocks from `[text]` categories |
| `utilities.css` | `@utility tint-*`, `@utility font-*`, `[utilities]`, `[components]` |

After writing, the CLI runs `npx --yes prettier` on all four files (skipped with a warning if `npx` is absent).

### sRGB gamut tolerance

Colors within sRGB are silently accepted. Colors 0–20% outside sRGB (P3 range) return `True` from `check_gamut()` — browsers clamp them cleanly. Colors more than 20% outside sRGB cause a hard `sys.exit(1)`.
