# Copyright (c) 2026 @wimwian
# SPDX-License-Identifier: MIT
# https://github.com/wimwian-org/t2t
"""Integration tests for the full t2t pipeline via main.convert()."""

import tomllib
import pytest
from t2t.main import convert


MINIMAL_TOML = b"""
[[palette]]
name = "primary"
base = "oklch(55% 0.10 260)"

[[token]]
name = "--color-bg"
palette = "primary"
light = 1000
dark = 0

[[token]]
name = "--color-fg"
palette = "primary"
light = 0
dark = 1000
"""


def _load(raw: bytes) -> dict:
    return tomllib.loads(raw.decode())


class TestConvertReturns:
    def test_returns_tuple(self):
        css, light, dark = convert(_load(MINIMAL_TOML))
        assert isinstance(css, str)
        assert isinstance(light, dict)
        assert isinstance(dark, dict)

    def test_css_ends_with_newline(self):
        css, _, _ = convert(_load(MINIMAL_TOML))
        assert css.endswith("\n")

    def test_light_and_dark_maps_populated(self):
        _, light, dark = convert(_load(MINIMAL_TOML))
        assert "--color-bg" in light
        assert "--color-fg" in light
        assert "--color-bg" in dark
        assert "--color-fg" in dark

    def test_light_dark_colors_are_mirrored(self):
        _, light, dark = convert(_load(MINIMAL_TOML))
        from t2t.color import parse_oklch
        light_L, _, _, _ = parse_oklch(light["--color-bg"])
        dark_L,  _, _, _ = parse_oklch(dark["--color-bg"])
        assert light_L > dark_L


class TestCssSections:
    def test_root_section_present_when_tokens(self):
        css, _, _ = convert(_load(MINIMAL_TOML))
        assert ":root" in css

    def test_dark_toggle_section_present(self):
        css, _, _ = convert(_load(MINIMAL_TOML))
        assert "[data-theme='dark']" in css
        assert "--L: ;" in css
        assert "--D: initial;" in css

    def test_base_layer_present_with_font(self):
        data = _load(MINIMAL_TOML + b"""
[[font]]
name  = "sans"
stack = ["Inter", "ui-sans-serif"]

  [[font.face]]
  family  = "Inter"
  url     = "https://example.com/inter.woff2"
  weight  = "100 900"
  display = "swap"
""")
        css, _, _ = convert(data)
        assert "@layer base" in css
        assert "@font-face" in css
        assert "Inter" in css

    def test_utilities_layer_with_typography(self):
        data = _load(MINIMAL_TOML + b"""
[[font]]
name  = "sans"
stack = ["Inter", "ui-sans-serif"]

[typography.sizes]
base = { size = "1rem" }
""")
        css, _, _ = convert(data)
        assert "@layer utilities" in css
        assert "font-size: 1rem" in css

    def test_components_section(self):
        data = _load(MINIMAL_TOML + b"""
[components]
".btn" = "display: inline-flex"
""")
        css, _, _ = convert(data)
        assert "@layer components" in css

    def test_static_section(self):
        data = _load(MINIMAL_TOML + b"""
[static]
"*, *::before, *::after" = "box-sizing: border-box"
""")
        css, _, _ = convert(data)
        assert "box-sizing: border-box" in css
        static_idx  = css.index("box-sizing")
        layer_after = css.rfind("@layer", 0, static_idx)
        brace_after = css.rfind("}", 0, static_idx)
        assert brace_after > layer_after

    def test_no_palette_step_vars_emitted(self):
        css, _, _ = convert(_load(MINIMAL_TOML))
        assert "--color-primary-" not in css


class TestMutedDisabled:
    def test_muted_in_root(self):
        data = _load(MINIMAL_TOML + b"""
[[token]]
name = "--color-x"
light = "oklch(55% 0.10 260)"
dark  = "oklch(30% 0.10 260)"
muted = 0.6
""")
        css, _, _ = convert(data)
        assert "--color-x-muted" in css

    def test_disabled_combined_in_root(self):
        data = _load(MINIMAL_TOML + b"""
[[token]]
name = "--color-x"
light = "oklch(55% 0.10 260)"
dark  = "oklch(30% 0.10 260)"
disabled = 0.3
""")
        css, _, _ = convert(data)
        root_block = css[:css.index("[data-theme='dark']")]
        assert "--color-x-disabled" in root_block
        assert "var(--L," in root_block


class TestSpaceToggle:
    def test_toggle_vars_in_root(self):
        css, _, _ = convert(_load(MINIMAL_TOML))
        root = css[:css.index("[data-theme='dark']")]
        assert "--L: initial;" in root
        assert "--D: ;" in root

    def test_dark_token_uses_var_L_D_format(self):
        css, _, _ = convert(_load(MINIMAL_TOML))
        assert "var(--L," in css
        assert "var(--D," in css

    def test_dark_block_only_has_toggle_flip(self):
        css, _, _ = convert(_load(MINIMAL_TOML))
        dark_block = css[css.index("[data-theme='dark']"):]
        assert "--color-bg" not in dark_block
        assert "--L: ;" in dark_block
        assert "--D: initial;" in dark_block

    def test_token_without_dark_emitted_plain(self):
        data = _load(MINIMAL_TOML + b"""
[[token]]
name = "--color-plain"
light = "oklch(55% 0.10 260)"
""")
        css, _, _ = convert(data)
        assert "--color-plain: oklch(55% 0.10 260);" in css

    def test_sections_separated_by_double_blank_line(self):
        data = _load(MINIMAL_TOML + b"""
[static]
"*" = "box-sizing: border-box"
""")
        css, _, _ = convert(data)
        assert "\n\n\n" in css

    def test_token_comment_emitted_as_css_comment(self):
        data = _load(MINIMAL_TOML + b"""
[[token]]
name = "--color-x"
comment = "brand colours"
light = "oklch(55% 0.10 260)"
dark  = "oklch(30% 0.10 260)"
""")
        css, _, _ = convert(data)
        assert "/* brand colours */" in css

    def test_root_vars_auto_grouped_with_comment(self):
        data = _load(MINIMAL_TOML + b"""
[root]
"--elevation-sm" = "7.78"
"--font-sans" = "sans-serif"
""")
        css, _, _ = convert(data)
        assert "/* elevation */" in css
        assert "/* font */" in css


class TestRootToken:
    def test_root_section_with_root_mapping(self):
        data = _load(MINIMAL_TOML + b"""
[root]
"--radius-card" = "0.75rem"
""")
        css, _, _ = convert(data)
        assert "--radius-card: 0.75rem" in css

    def test_token_in_root(self):
        _, light, _ = convert(_load(MINIMAL_TOML))
        assert light["--color-bg"].startswith("oklch(")


class TestEmptyInput:
    def test_empty_toml_produces_newline(self):
        css, light, dark = convert({})
        assert css.strip() == "" or css == "\n"
        assert light == {}
        assert dark == {}
