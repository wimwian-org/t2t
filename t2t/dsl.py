# Copyright (c) 2026 @wimwian
# SPDX-License-Identifier: MIT
# https://github.com/wimwian-org/t2t
"""
ramp() DSL resolver.

Because TOML values are literals, color_ramp() cannot be called directly in
a TOML file. Any string value matching the pattern ramp(...) is recognised by
t2t and evaluated as a color_ramp call at conversion time.

Syntax:

```
"ramp(<color-ref>, <step>)"
"ramp(<color-ref>, <step>, <alpha>)"
```

where `<color-ref>` is either a palette name (looked up via palette_map) or an
inline `oklch(...)` string. All other string values are passed through unchanged.

Examples:

```
ramp(primary, 400)                        palette reference
ramp(primary, 400, 0.5)                   palette reference with alpha
ramp(oklch(55% 0.20 260), 400)            inline oklch
ramp(oklch(55% 0.20 260), 400, 0.5)       inline oklch with alpha
```
"""

import re

from .color import color_ramp

_RAMP_RE = re.compile(r'^ramp\((.+),\s*(\d+)(?:,\s*([\d.]+))?\s*\)$', re.DOTALL)


def resolve_ramp_dsl(s: str, palette_map: dict[str, str]) -> str | None:
    """
    Parse and evaluate a ramp() DSL expression.

    Args:
        s:           The string to test and evaluate.
        palette_map: Mapping of palette name → base oklch string.

    Returns:
        A resolved oklch string if `s` is a valid ramp() expression,
        or None if `s` does not match the pattern.

    Raises:
        ValueError: If the color reference is not a known palette name and
                    cannot be parsed as an oklch string by color_ramp.
    """
    m = _RAMP_RE.match(s.strip())
    if not m:
        return None
    color_ref = m.group(1).strip()
    step      = int(m.group(2))
    alpha     = float(m.group(3)) if m.group(3) else 1.0
    base = palette_map.get(color_ref, color_ref)  # palette name or inline oklch
    return color_ramp(base, step, alpha)


def resolve_color(s: str, palette_map: dict[str, str]) -> str:
    """
    Resolve a color value string.

    If `s` is a ramp() DSL expression, evaluate it and return the resulting
    oklch string. Otherwise return `s` unchanged (raw oklch, CSS var, etc.).

    Args:
        s:           Color value string from TOML.
        palette_map: Mapping of palette name → base oklch string.
    """
    result = resolve_ramp_dsl(s, palette_map)
    return result if result is not None else s
