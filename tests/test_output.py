# Copyright (c) 2026 @wimwian
# SPDX-License-Identifier: MIT
# https://github.com/wimwian-org/t2t
"""Tests for output.py — build_report."""

from t2t.output import build_report

_PALETTE_MAP = {"primary": "oklch(55% 0.10 260)"}
_LIGHT = {"--color-bg": "oklch(90% 0.02 260)", "--color-fg": "oklch(10% 0.02 260)"}
_DARK  = {"--color-bg": "oklch(10% 0.02 260)", "--color-fg": "oklch(90% 0.02 260)"}


class TestBuildReport:
    def test_returns_string(self):
        assert isinstance(build_report({}, _PALETTE_MAP, {}, {}), str)

    def test_ends_with_newline(self):
        result = build_report({}, _PALETTE_MAP, {}, {})
        assert result.endswith("\n")

    def test_title_uses_meta_name(self):
        data = {"meta": {"name": "my-theme"}}
        result = build_report(data, _PALETTE_MAP, {}, {})
        assert "my-theme" in result

    def test_title_includes_version(self):
        data = {"meta": {"name": "t", "version": "2.0.0"}}
        result = build_report(data, _PALETTE_MAP, {}, {})
        assert "v2.0.0" in result

    def test_default_title_when_no_meta(self):
        result = build_report({}, _PALETTE_MAP, {}, {})
        assert "theme" in result

    def test_token_names_in_table(self):
        result = build_report({}, _PALETTE_MAP, _LIGHT, _DARK)
        assert "--color-bg" in result
        assert "--color-fg" in result

    def test_root_vars_listed(self):
        data = {"root": {"--radius-card": "0.75rem"}}
        result = build_report(data, _PALETTE_MAP, {}, {})
        assert "--radius-card" in result

    def test_no_contrast_section_when_no_pairs(self):
        result = build_report({}, _PALETTE_MAP, _LIGHT, _DARK)
        assert "## Contrast" not in result

    def test_contrast_section_present_when_pairs_exist(self):
        data = {"contrast": [{"label": "bg/fg", "bg": "--color-bg", "fg": "--color-fg"}]}
        result = build_report(data, _PALETTE_MAP, _LIGHT, _DARK)
        assert "## Contrast" in result
        assert "bg/fg" in result

    def test_aaa_pass_symbol(self):
        data = {"contrast": [{"label": "bg/fg", "bg": "--color-bg", "fg": "--color-fg"}]}
        result = build_report(data, _PALETTE_MAP, _LIGHT, _DARK)
        assert "✓ AAA" in result

    def test_aa_only_symbol(self):
        # large=True → AA 3:1, AAA 4.5:1; white vs oklch(65%) ≈ 3.2:1 → AA only
        light = {"--lo": "oklch(100% 0 0)", "--hi": "oklch(65% 0 0)"}
        data = {"contrast": [{"label": "t", "bg": "--lo", "fg": "--hi", "large": True}]}
        result = build_report(data, {}, light, light)
        assert "⚠! AA" in result

    def test_fail_symbol(self):
        # Very similar lightness: contrast < 3:1, fails even large-text AA
        light = {"--lo": "oklch(80% 0 0)", "--hi": "oklch(70% 0 0)"}
        data = {"contrast": [{"label": "t", "bg": "--lo", "fg": "--hi", "large": True}]}
        result = build_report(data, {}, light, light)
        assert "✗ FAIL" in result
