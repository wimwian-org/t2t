# Copyright (c) 2026 @wimwian
# SPDX-License-Identifier: MIT
# https://github.com/wimwian-org/t2t
"""
sRGB gamut validation for oklch colors.

Not all oklch colors can be represented in sRGB. This module converts oklch
to linear sRGB via the oklab intermediate space and checks that all channels
fall within [0, 1]. Out-of-gamut colors are a hard error.

Conversion pipeline:

```
oklch → oklab → linear sRGB
```

The oklab → linear sRGB matrix comes from the Oklab specification
(https://bottosson.github.io/posts/oklab/).
"""

import math
import sys

from .color import parse_oklch


def oklch_to_linear_srgb(L_pct: float, C: float, H_deg: float) -> tuple[float, float, float]:
    """
    Convert an oklch color to linear sRGB via the oklab intermediate space.

    Args:
        L_pct: Lightness as a percentage (0–100).
        C:     Chroma (>= 0).
        H_deg: Hue in degrees (0–360).

    Returns:
        (R, G, B) in linear sRGB. Values outside [0, 1] indicate out-of-gamut.
    """
    L = L_pct / 100
    H = math.radians(H_deg)
    a = C * math.cos(H)
    b = C * math.sin(H)

    # oklab → LMS (cube roots)
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3

    # LMS → linear sRGB
    R =  4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    G = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    B = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    return R, G, B


def check_gamut(oklch_str: str, label: str) -> bool:
    """
    Validate that an oklch color is within (or near) the sRGB gamut.

    Returns True if the color is P3-range (0–20% outside sRGB): browsers
    silently clamp such values to the gamut boundary, so the CSS remains valid
    and the caller can choose to surface it as a design note.

    Colors more than 20% outside sRGB indicate a likely input error and cause
    a hard exit.

    Alpha is not involved in gamut checking.

    Args:
        oklch_str: oklch color string to validate.
        label:     Human-readable name used in the error message.

    Returns:
        True if the color is P3-range (slightly outside sRGB), False otherwise.
    """
    L, C, H, _ = parse_oklch(oklch_str)
    R, G, B = oklch_to_linear_srgb(L, C, H)
    tol = 1e-4
    bad = [(ch, v) for ch, v in (("R", R), ("G", G), ("B", B)) if v < -tol or v > 1 + tol]
    if not bad:
        return False
    channels = "  ".join(f"{ch}={v:.4f}" for ch, v in bad)
    severity = max(abs(v - (0 if v < 0 else 1)) for _, v in bad)
    if severity > 0.20:
        print(f"t2t: error: {label} {oklch_str} is out of sRGB gamut", file=sys.stderr)
        print(f"  {channels}", file=sys.stderr)
        sys.exit(1)
    return True
