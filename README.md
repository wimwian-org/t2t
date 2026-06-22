<!-- Copyright (c) 2026 @wimwian -->
<!-- SPDX-License-Identifier: MIT -->
<!-- https://github.com/wimwian-org/t2t -->
# t2t — TOML to Tailwind

Convert a TOML theme configuration into a set of Tailwind-compatible CSS files.

t2t takes a single `.toml` file that describes your design tokens — palettes,
typography, dark-mode pairs, contrast requirements — and emits four CSS files
ready to drop into a Tailwind v4 project.

## Output files

| File | Contents |
|------|----------|
| `wimwian.css` | Entry point: `@import "tailwindcss"` + the three files below |
| `theme.css` | `@font-face` blocks, `:root` custom properties, dark-mode flip |
| `typography.css` | `@utility` blocks for text scale categories |
| `utilities.css` | `@utility font-*`, `@utility tint-*`, custom utility rules |

A `report.md` with a token/contrast summary is written alongside the CSS.

## Installation

Requires Python ≥ 3.15 and [uv](https://docs.astral.sh/uv/).

```
git clone <repo>
cd t2t
uv sync
```

Run without installing:

```
uv run t2t -i theme.toml -o dist/wimwian.css
```

Or install the entry point into the venv:

```
uv pip install -e .
t2t -i theme.toml -o dist/wimwian.css
```

## CLI

```
t2t -i <input.toml> [-o <output.css>] [-d] [-m]

  -i, --input      TOML theme file (required)
  -o, --output     Output CSS path; omit to print to stdout
  -d, --dryrun     Print CSS to stdout without writing any files
  -m, --add-minified  Write a minified copy next to the output (wimwian-min.css)
```

When `-o` is given, t2t writes four files into the same directory as `output`:
`wimwian.css`, `theme.css`, `typography.css`, `utilities.css`, and `report.md`.
Each is then formatted with [prettier](https://prettier.io/) via `npx --yes prettier`
(if Node/npx is available; skipped with a warning otherwise).

A summary table is printed to `stderr` on every run:

```
Tokens
──────────────────────────────────────────────────────────────────────────────────────
Name                              Light                        Dark
──────────────────────────────────────────────────────────────────────────────────────
--color-surface                   oklch(91% 0.04 260)          oklch(11% 0.04 260)
...

Contrast
| Label            | Light          | Dark           |
|------------------|----------------|----------------|
| surface / accent | 12.3:1 ✓ AAA   | 11.8:1 ✓ AAA   |
```

## TOML configuration reference

### `[meta]`

Optional. Sets the package name and version used in the `wimwian.css` header
comment.

```toml
[meta]
name    = "my-theme"
version = "1.0.0"
```

---

### `[[palette]]`

Named color families. Each palette anchors a hue at step 500; t2t derives
the full ramp using oklch lightness interpolation. Palettes are referenced by
name in token definitions and the `ramp()` DSL.

```toml
[[palette]]
name = "primary"
base = "oklch(55% 0.20 260)"   # step 500 anchor

[[palette]]
name = "mono"
base = "oklch(50% 0.00 0)"
```

No CSS custom properties are emitted for palettes themselves — they exist
only as references for token resolution.

---

### `[[font]]`

Font families and optional `@font-face` declarations.

```toml
[[font]]
name  = "sans"
stack = ["Inter", "ui-sans-serif", "system-ui"]

  [[font.face]]
  family  = "Inter"
  url     = "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS.woff2"
  weight  = "100 900"    # optional
  style   = "normal"     # optional
  display = "swap"       # optional
```

Each `[[font]]` emits an `@utility font-<name>` block. Each `[[font.face]]`
emits an `@font-face` rule inside `@layer base`.

---

### `[typography]`

Free-form text size and weight utility classes for `utilities.css`.

```toml
[typography.sizes]
sm      = { size = "0.875rem" }
base    = { size = "1rem" }
lg      = { size = "1.5rem" }
display = { size = "3rem", leading = 1.0, weight = 700 }

[typography.weights]
normal   = 400
medium   = 500
semibold = 600
bold     = 700
```

`leading` and `weight` are optional — t2t derives them from `size` when omitted
(see [Automatic derivation](#automatic-derivation)).

---

### `[text]`

Semantic typography categories for `typography.css`. Each category produces
one `@utility <category>-<size>` block per size variant. These differ from
`[typography]` in that they use Tailwind's `@apply` mechanism and support
font-family and small-caps options.

```toml
[text]
font-family = "font-sans"  # global default for all categories
weight      = 400

[text.body]
comment     = "Body text"
font-family = "font-sans"
weight      = 400

  [text.body.base]
  size = "1rem"

  [text.body.sm]
  size   = "0.875rem"
  weight = 300

[text.display]
weight    = 700
capitalize = false
small-caps = false

  [text.display.xl]
  size        = "3rem"
  line-height = 1.05
```

Inheritance chain for each property:
`size entry` → `category default` → `[text]` global → built-in default

---

### `[[token]]`

Design tokens: CSS custom properties with light and dark resolved values.
Each token expands to up to six properties:
`name`, `name-muted`, `name-disabled` × {light, dark}.

```toml
[[token]]
name     = "--color-surface"
palette  = "primary"     # palette to use for integer step resolution
light    = 900           # step on the ramp (0–1000)
dark     = 100           # omit for auto-derived (1000 - light)
muted    = 0.6           # alpha variant
disabled = 0.35          # alpha variant
comment  = "Surfaces"    # printed as /* comment */ in :root
```

**Light / dark value forms:**

| Form | Example | Notes |
|------|---------|-------|
| Integer step | `900` | Requires `palette` field |
| `ramp()` DSL | `"ramp(primary, 400)"` | See below |
| Raw oklch | `"oklch(80% 0.10 120)"` | Passed through directly |
| CSS var | `"var(--some-var)"` | Passed through; no auto-dark |

**Pass-through pointer tokens** (no light/dark — just a static value):

```toml
[[token]]
name  = "--surface-primary-bg"
value = "var(--color-surface)"
```

**Auto-dark derivation:** when `dark` is omitted, t2t computes it as
`1000 - light` for integer steps, or `ramp(palette, 1000 - N)` for
`ramp()` DSL values. Raw oklch and CSS vars get no auto-dark.

---

### `ramp()` DSL

`ramp()` expressions can appear anywhere a color value is accepted. They
invoke the same lightness ramp as integer token steps but accept an explicit
palette reference or an inline oklch string.

```
ramp(primary, 400)                    palette reference, step 400
ramp(primary, 400, 0.5)               with alpha 0.5
ramp(oklch(55% 0.20 260), 400)        inline base color
ramp(oklch(55% 0.20 260), 400, 0.5)   inline + alpha
```

Step 0 → `oklch(0% 0 H)` (black), step 500 → base color, step 1000 → `oklch(100% 0 H)` (white).

---

### `[root]`

Raw CSS custom properties emitted directly into `:root {}`. Values may use
`ramp()` DSL or raw CSS.

```toml
[root]
"--radius-card"    = "0.75rem"
"--radius-button"  = "0.5rem"
"--spacing-layout" = "ramp(primary, 200)"
```

Variables are grouped by their first dash-segment with a `/* group */` comment.

---

### `[[contrast]]`

WCAG contrast validation pairs. t2t exits non-zero if any pair fails AA.
AAA misses produce a warning in the summary table.

```toml
[[contrast]]
label = "surface / accent"
bg    = "--color-surface"    # token name, ramp(), or oklch()
fg    = "--color-accent"
large = false                # true → large-text thresholds (AA 3:1, AAA 4.5:1)
```

Both light and dark resolved values are validated independently.

---

### `[utilities]`

Free-form utility classes appended to the `@layer utilities` block.

```toml
[utilities]
".card"    = "padding: 1rem; border-radius: var(--radius-card);"
".surface" = "background-color: var(--color-surface);"
```

---

### `[components]`

Free-form component rules in `@layer components`.

```toml
[components]
".btn-primary" = "background: var(--color-accent); color: var(--color-surface); padding: 0.5rem 1rem;"
```

---

### `[static]`

Unlayered CSS rules emitted at the end of `theme.css`, after all `@layer`
declarations. Use for resets or global rules that must beat `@layer` specificity.

```toml
[static]
"*, *::before, *::after" = "box-sizing: border-box;"
"html"                   = "font-synthesis: none;"
```

---

## Color system

All colors are `oklch(L% C H)` or `oklch(L% C H / A)`.

- **L** — lightness, 0–100 (percent)
- **C** — chroma ≥ 0
- **H** — hue 0–360 (degrees)
- **A** — alpha 0.0–1.0

oklch provides perceptually uniform lightness, so the ramp from step 0 to 1000
looks linear to the eye regardless of hue.

### sRGB gamut validation

Every resolved oklch color is validated against the sRGB gamut at conversion
time. Colors up to 20% outside sRGB are accepted (browsers clamp P3-range
values cleanly). Colors more than 20% outside sRGB cause a hard error.

### Automatic derivation

When `leading` (line-height) is not provided for a size:

| Size (rem equivalent) | line-height |
|----------------------|-------------|
| ≤ 1.0 rem | 1.5 |
| ≤ 1.5 rem | 1.4 |
| ≤ 2.0 rem | 1.3 |
| ≤ 2.5 rem | 1.2 |
| > 2.5 rem | 1.1 |

Letter-spacing is omitted (browser default) for sizes ≤ 1.5 rem,
`-0.025em` for ≤ 2.5 rem, and `-0.05em` above.

---

## Dark mode

t2t uses the CSS space-toggle trick to avoid duplicating token values:

```css
:root          { --L: initial; --D: ; }
[data-theme='dark'] { --L: ; --D: initial; }

--color-surface: var(--L, oklch(91% 0.04 260)) var(--D, oklch(11% 0.04 260));
```

Add `data-theme="dark"` to any ancestor element to activate dark mode for
that subtree. No JavaScript is needed; no media query is required.

---

## Development

```
uv sync           # install runtime + dev dependencies
uv run pytest     # run the test suite (153 tests)
uv run pytest --cov=t2t --cov-report=term-missing
uv run pdoc t2t -o docs   # regenerate HTML docs
```
