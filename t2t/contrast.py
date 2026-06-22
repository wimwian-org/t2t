# Copyright (c) 2026 @wimwian
# SPDX-License-Identifier: MIT
# https://github.com/wimwian-org/t2t
"""
WCAG contrast ratio computation and [[contrast]] pair validation.

Contrast ratio is computed from relative luminance per WCAG 2.1:
    https://www.w3.org/TR/WCAG21/#contrast-minimum

The oklch → linear sRGB conversion is reused from gamut.py, since linear sRGB
channels are exactly the input required by the WCAG luminance formula.

Thresholds:
    Normal text  — AA: 4.5:1,  AAA: 7.0:1
    Large text   — AA: 3.0:1,  AAA: 4.5:1

Large text (WCAG 2.1 definition):
    >= 18pt (24px) at normal weight, or >= 14pt (18.67px) at bold weight.
    Set large = true in [[contrast]] for these pairs.
"""

import sys

from .color import parse_oklch
from .dsl import resolve_color
from .gamut import oklch_to_linear_srgb

# (AA, AAA) keyed by large=False/True
_THRESHOLDS: dict[bool, tuple[float, float]] = {
    False: (4.5, 7.0),
    True:  (3.0, 4.5),
}


def _relative_luminance(L_pct: float, C: float, H: float) -> float:
    """
    Compute WCAG relative luminance from an oklch color.

    Converts oklch → linear sRGB, then applies the WCAG luminance formula:
        Y = 0.2126·R + 0.7152·G + 0.0722·B
    """
    R, G, B = oklch_to_linear_srgb(L_pct, C, H)
    return 0.2126 * R + 0.7152 * G + 0.0722 * B


def contrast_ratio(c1: str, c2: str) -> float:
    """
    Compute the WCAG contrast ratio between two oklch color strings.

    The ratio is always >= 1.0 (lighter / darker + 0.05 offsets).
    Black vs white returns 21.0.

    Args:
        c1: First oklch color string.
        c2: Second oklch color string.
    """
    L1, C1, H1, _ = parse_oklch(c1)
    L2, C2, H2, _ = parse_oklch(c2)
    Y1 = _relative_luminance(L1, C1, H1)
    Y2 = _relative_luminance(L2, C2, H2)
    hi, lo = (Y1, Y2) if Y1 >= Y2 else (Y2, Y1)
    return (hi + 0.05) / (lo + 0.05)


def resolve_contrast_color(val: str, light_map: dict[str, str], dark_map: dict[str, str],
                            palette_map: dict[str, str], theme: str) -> str:
    """
    Resolve a [[contrast]] bg/fg value to an oklch string.

    Accepts three forms:
        "--color-*"          token reference (looked up in light_map / dark_map)
        "ramp(...)"          ramp() DSL expression
        "oklch(...)"         raw oklch string (passed through)

    Args:
        val:         The raw TOML value string.
        light_map:   Resolved light-theme token values.
        dark_map:    Resolved dark-theme token values.
        palette_map: Palette name → base color mapping for DSL resolution.
        theme:       "light" or "dark" — selects which token map to use.

    Raises:
        ValueError: If val starts with "--" but is not found in the token map.
    """
    if val.startswith("--"):
        color = (light_map if theme == "light" else dark_map).get(val)
        if color is None:
            raise ValueError(f"Contrast references unknown token {val!r}")
        return color
    return resolve_color(val, palette_map)


def validate_contrast(pairs: list[dict], palette_map: dict[str, str],
                      light_map: dict[str, str], dark_map: dict[str, str]) -> list[str]:
    """
    Validate WCAG contrast ratios for all [[contrast]] pairs.

    Both the light and dark resolved values are checked independently per pair.

    Behaviour:
        ratio >= AAA  — silent pass
        AA <= ratio < AAA  — warning collected and returned
        ratio < AA    — hard error, t2t exits non-zero immediately

    Args:
        pairs:       List of [[contrast]] dicts from TOML.
        palette_map: Palette name → base color.
        light_map:   Resolved light-theme token values.
        dark_map:    Resolved dark-theme token values.

    Returns:
        List of warning strings (AA-passing but not AAA) for display in the summary.
    """
    warnings: list[str] = []
    for pair in pairs:
        label = pair["label"]
        large = pair.get("large", False)
        aa, aaa = _THRESHOLDS[large]
        for theme in ("light", "dark"):
            bg    = resolve_contrast_color(pair["bg"], light_map, dark_map, palette_map, theme)
            fg    = resolve_contrast_color(pair["fg"], light_map, dark_map, palette_map, theme)
            ratio = contrast_ratio(bg, fg)
            if ratio < aa:
                print(
                    f"t2t: error:   [{theme}] {label!r}  "
                    f"contrast {ratio:.1f}:1 — fails AA minimum ({aa}:1)",
                    file=sys.stderr,
                )
                sys.exit(1)
            elif ratio < aaa:
                warnings.append(
                    f"[{theme}] {label!r}  "
                    f"contrast {ratio:.1f}:1 — passes AA ({aa}:1) but not AAA ({aaa}:1)"
                )
    return warnings
