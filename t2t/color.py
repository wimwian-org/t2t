"""
oklch color parsing, formatting, and the core color_ramp function.

All color values in this project are oklch strings of the form:

```
oklch(L% C H)
oklch(L% C H / A)
```

where L is lightness 0–100, C is chroma >= 0, H is hue 0–360, and A is
alpha 0.0–1.0 (fraction or percentage).
"""

import re

_OKLCH_RE = re.compile(
    r'oklch\(\s*([\d.]+)%?\s+([\d.]+)\s+([\d.]+)'
    r'(?:\s*/\s*([\d.]+%?))?\s*\)',
    re.IGNORECASE,
)


def parse_oklch(s: str) -> tuple[float, float, float, float]:
    """
    Parse an oklch color string into (L_pct, C, H, A).

    L_pct is lightness as a percentage (0–100).
    A defaults to 1.0 (opaque) when absent from the string.
    Alpha may be written as a fraction (0.5) or percentage (50%).

    Raises ValueError for unrecognised formats.
    """
    m = _OKLCH_RE.match(s.strip())
    if not m:
        raise ValueError(f"Cannot parse oklch color: {s!r}")
    L, C, H = float(m.group(1)), float(m.group(2)), float(m.group(3))
    raw_a = m.group(4)
    if raw_a is None:
        A = 1.0
    elif raw_a.endswith("%"):
        A = float(raw_a[:-1]) / 100
    else:
        A = float(raw_a)
    return L, C, H, A


def fmt_oklch(L: float, C: float, H: float, A: float = 1.0) -> str:
    """
    Format (L_pct, C, H, A) as an oklch string.

    Alpha is omitted when A == 1.0 (fully opaque).
    Uses :.4g precision for L and C to avoid trailing zeros.
    """
    alpha = f" / {A:g}" if A < 1.0 else ""
    return f"oklch({L:.4g}% {C:.4g} {H:g}{alpha})"


def is_oklch(s: str) -> bool:
    """Return True if s looks like an oklch(...) color string."""
    return s.strip().lower().startswith("oklch(")


def apply_alpha(color: str, alpha: float) -> str:
    """Return the same oklch color with the given alpha value substituted."""
    L, C, H, _ = parse_oklch(color)
    return fmt_oklch(L, C, H, alpha)


def color_ramp(base: str, step: int, alpha: float = 1.0) -> str:
    """
    Compute the oklch color at position `step` (0–1000) on a perceptual ramp
    anchored at step 500 == base color.

    Steps below 500 interpolate linearly toward black (L=0, C=0).
    Steps above 500 interpolate linearly toward white (L=100, C=0).
    Hue (H) is always carried through unchanged from base.

    The alpha channel embedded in the base string is intentionally ignored;
    use the `alpha` parameter to control output transparency (default: 1.0 opaque).

    Args:
        base:  oklch color string anchoring the ramp at step 500.
        step:  integer 0–1000 selecting the output shade.
        alpha: output alpha, 0.0–1.0. Omitted from the returned string when 1.0.

    Returns:
        An oklch color string.

    Examples:
        ```python
        >>> color_ramp("oklch(55% 0.20 260)", 0)
        'oklch(0% 0 260)'
        >>> color_ramp("oklch(55% 0.20 260)", 500)
        'oklch(55% 0.2 260)'
        >>> color_ramp("oklch(55% 0.20 260)", 1000)
        'oklch(100% 0 260)'
        >>> color_ramp("oklch(55% 0.20 260)", 500, 0.5)
        'oklch(55% 0.2 260 / 0.5)'
        >>> color_ramp("oklch(55% 0.20 260 / 0.3)", 500)  # base alpha ignored
        'oklch(55% 0.2 260)'
        ```
    """
    L, C, H, _ = parse_oklch(base)

    if step <= 0:
        return fmt_oklch(0.0, 0.0, H, alpha)
    if step >= 1000:
        return fmt_oklch(100.0, 0.0, H, alpha)
    if step == 500:
        return fmt_oklch(L, C, H, alpha)
    if step < 500:
        t = step / 500          # 0.0 at black, 1.0 at base
        return fmt_oklch(L * t, C * t, H, alpha)
    t = (step - 500) / 500      # 0.0 at base, 1.0 at white
    return fmt_oklch(L + (100 - L) * t, C * (1 - t), H, alpha)
