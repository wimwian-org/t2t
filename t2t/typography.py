# Copyright (c) 2026 @wimwian
# SPDX-License-Identifier: MIT
# https://github.com/wimwian-org/t2t
"""
Typography derivation helpers.

Computes line-height and letter-spacing automatically from a font-size string,
so TOML authors do not need to specify these values manually.

Unit conversion (for threshold lookup only — the original size string is emitted
unchanged in CSS output):

```
rem → identity
em  → 1:1 (root-level equivalent)
px  → ÷ 16
pt  → × 1.3333 ÷ 16
```

Line-height thresholds (unitless multiplier):

```
<= 1.0 rem → 1.5
<= 1.5 rem → 1.4
<= 2.0 rem → 1.3
<= 2.5 rem → 1.2
 > 2.5 rem → 1.1
```

Letter-spacing thresholds (em offset — negative = tighter optical tracking):

```
<= 1.5 rem → 0        (omitted from CSS output)
<= 2.5 rem → -0.025em
 > 2.5 rem → -0.05em
```
"""

import re

_SIZE_RE = re.compile(r'^([\d.]+)(rem|em|px|pt)$')

_PX_PER_REM = 16.0
_PT_TO_PX   = 1.3333


def _to_rem(size: str) -> float | None:
    """
    Convert a CSS size string to a rem equivalent for threshold lookup.

    Returns None if the unit is unrecognized or the string cannot be parsed.
    The original `size` string should always be emitted unchanged in CSS output.
    """
    m = _SIZE_RE.match(size.strip())
    if not m:
        return None
    v, unit = float(m.group(1)), m.group(2)
    return {
        "rem": v,
        "em":  v,
        "px":  v / _PX_PER_REM,
        "pt":  v * _PT_TO_PX / _PX_PER_REM,
    }[unit]


def derive_leading(size: str) -> float:
    """
    Derive a unitless line-height multiplier from a CSS font-size string.

    The rem-equivalent of `size` is compared against the thresholds defined
    in this module's docstring.

    Raises:
        ValueError: If the unit cannot be converted to rem
                    (caller should provide 'leading' explicitly in that case).
    """
    rem = _to_rem(size)
    if rem is None:
        raise ValueError(
            f"Cannot derive line-height for size {size!r} — provide 'leading' explicitly"
        )
    if rem <= 1.0: return 1.5
    if rem <= 1.5: return 1.4
    if rem <= 2.0: return 1.3
    if rem <= 2.5: return 1.2
    return 1.1


def derive_tracking(size: str) -> float | None:
    """
    Derive a letter-spacing value (in em) from a CSS font-size string.

    Returns None when the computed tracking is 0 — callers should omit
    `letter-spacing` from the CSS output in that case (browser default).

    The returned value is the em offset (e.g. -0.025), not the multiplier.
    """
    rem = _to_rem(size)
    if rem is None:
        return None
    if rem <= 1.5: return None
    if rem <= 2.5: return -0.025
    return -0.05
