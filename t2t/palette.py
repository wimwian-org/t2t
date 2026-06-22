# Copyright (c) 2026 @wimwian
# SPDX-License-Identifier: MIT
# https://github.com/wimwian-org/t2t
"""
Palette name → base-color mapping.

A [[palette]] entry in TOML names a palette and anchors it at a base oklch
color (step 500 on the ramp). The `steps` field is no longer supported — palettes
are used only as named references for the ramp() DSL and token resolution;
no raw --color-<name>-<step> properties are emitted.
"""


def build_palette_map(palettes: list[dict]) -> dict[str, str]:
    """
    Build a mapping of palette name → base oklch string from a list of
    [[palette]] dicts.

    Used by the DSL resolver and token map builder to look up base colors
    by palette name.
    """
    return {p["name"]: p["base"] for p in palettes}
