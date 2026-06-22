"""
Token resolution: build light and dark color maps from [[token]] entries.

Each [[token]] entry defines a named CSS custom property with a light-theme
color and optional dark, muted, and disabled values.

```
light    required  int (palette step) or string (ramp DSL / raw oklch)
dark     optional  same forms as light; when omitted, auto-derived as
                   1000−step for int light or ramp(pal, 1000−step) for
                   ramp() DSL light; raw oklch / CSS var → no auto-dark
muted    optional  float alpha (0–1); generates <name>-muted in both maps
disabled optional  float alpha (0–1); generates <name>-disabled in both maps
```

muted and disabled are alpha variants of the resolved light/dark color, valid
for both modes. Each [[token]] therefore expands to up to 6 CSS custom
properties: name, name-muted, name-disabled × {light, dark}.

Resolved values are oklch strings and are validated against the sRGB gamut
immediately after resolution.
"""

import re

from .color import apply_alpha, color_ramp, is_oklch
from .dsl import resolve_color
from .gamut import check_gamut

_RAMP_STEP_RE = re.compile(r'^ramp\(([^,]+),\s*(\d+)(?:,\s*[\d.]+)?\s*\)$', re.DOTALL)


def _default_dark(light: int | str) -> int | str | None:
    """
    Derive the default dark value from a light specification.

    ```
    int step      → 1000 - step        (same palette, complementary shade)
    ramp(pal, N)  → ramp(pal, 1000-N)  (same palette + alpha if present)
    anything else → None               (no auto-dark)
    ```
    """
    if isinstance(light, int):
        return 1000 - light
    m = _RAMP_STEP_RE.match(str(light).strip())
    if m:
        palette_ref, step = m.group(1).strip(), int(m.group(2))
        return f"ramp({palette_ref}, {1000 - step})"
    return None


def resolve_token_color(val: int | str, palette_base: str | None,
                         palette_map: dict[str, str]) -> str:
    """
    Resolve a single token light/dark value to an oklch string.

    Args:
        val:          Integer step (requires palette_base) or string color value.
        palette_base: Base oklch string for the token's named palette, or None.
        palette_map:  Full palette name → base color mapping for DSL resolution.

    Returns:
        An oklch color string.

    Raises:
        ValueError: If val is an integer but no palette_base is provided.
    """
    if isinstance(val, int):
        if not palette_base:
            raise ValueError("Integer token value requires a 'palette' field")
        return color_ramp(palette_base, val)
    return resolve_color(str(val), palette_map)


def build_token_maps(tokens: list[dict],
                     palette_map: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """
    Resolve all [[token]] entries into light and dark color maps.

    Runs sRGB gamut validation on every resolved oklch value.
    Tokens without a dark value are absent from dark_map — render_dark skips them.
    muted and disabled alpha variants are added as <name>-muted / <name>-disabled
    keys in both light_map and dark_map (only when the resolved color is oklch).

    Args:
        tokens:      List of [[token]] dicts from TOML.
        palette_map: Palette name → base color mapping.

    Returns:
        (light_map, dark_map): dicts mapping CSS custom property name → oklch string.
    """
    light_map: dict[str, str] = {}
    dark_map:  dict[str, str] = {}

    for token in tokens:
        name = token["name"]

        # Pass-through pointer: value = "var(--...)" — emit as-is, no dark/alpha variants
        if "value" in token:
            light_map[name] = token["value"]
            continue

        palette_base = palette_map.get(token.get("palette", ""))

        light_val = resolve_token_color(token["light"], palette_base, palette_map)
        if is_oklch(light_val):
            check_gamut(light_val, f"{name} (light)")
        light_map[name] = light_val

        light    = token["light"]
        dark_raw = token.get("dark", _default_dark(light))
        dark_val = None
        if dark_raw is not None:
            dark_val = resolve_token_color(dark_raw, palette_base, palette_map)
            if is_oklch(dark_val):
                check_gamut(dark_val, f"{name} (dark)")
            dark_map[name] = dark_val

        for variant in ("muted", "disabled"):
            raw_alpha = token.get(variant)
            if raw_alpha is None:
                continue
            alpha = float(raw_alpha)
            key   = f"{name}-{variant}"
            if is_oklch(light_val):
                light_map[key] = apply_alpha(light_val, alpha)
            if dark_val is not None and is_oklch(dark_val):
                dark_map[key] = apply_alpha(dark_val, alpha)

    return light_map, dark_map


def build_comments_map(tokens: list[dict]) -> dict[str, str]:
    """Return a mapping of token name → section comment for tokens that carry a 'comment' field."""
    return {t["name"]: t["comment"] for t in tokens if "comment" in t}
