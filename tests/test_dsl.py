"""Tests for dsl.py — resolve_ramp_dsl, resolve_color."""

import pytest
from t2t.dsl import resolve_ramp_dsl, resolve_color

BASE     = "oklch(55% 0.20 260)"
PALETTES = {"primary": BASE, "mono": "oklch(50% 0 0)"}


class TestResolveRampDsl:
    def test_palette_name_reference(self):
        result = resolve_ramp_dsl("ramp(primary, 500)", PALETTES)
        assert result == "oklch(55% 0.2 260)"

    def test_inline_oklch(self):
        result = resolve_ramp_dsl(f"ramp({BASE}, 500)", PALETTES)
        assert result == "oklch(55% 0.2 260)"

    def test_with_alpha(self):
        result = resolve_ramp_dsl("ramp(primary, 500, 0.5)", PALETTES)
        assert result is not None
        assert "/ 0.5" in result

    def test_inline_oklch_with_alpha(self):
        result = resolve_ramp_dsl(f"ramp({BASE}, 500, 0.5)", PALETTES)
        assert result is not None
        assert "/ 0.5" in result

    def test_step_zero(self):
        result = resolve_ramp_dsl("ramp(primary, 0)", PALETTES)
        assert result is not None
        assert result.startswith("oklch(0%")

    def test_step_1000(self):
        result = resolve_ramp_dsl("ramp(primary, 1000)", PALETTES)
        assert result is not None
        assert result.startswith("oklch(100%")

    def test_non_ramp_returns_none(self):
        assert resolve_ramp_dsl("oklch(55% 0.20 260)", PALETTES) is None
        assert resolve_ramp_dsl("var(--color-x)", PALETTES) is None
        assert resolve_ramp_dsl("red", PALETTES) is None
        assert resolve_ramp_dsl("", PALETTES) is None

    def test_unknown_palette_falls_back_to_inline(self):
        # Unknown palette name → treated as an oklch string → ValueError from parse_oklch
        with pytest.raises(ValueError):
            resolve_ramp_dsl("ramp(unknown-palette, 500)", PALETTES)

    def test_whitespace_tolerant(self):
        result = resolve_ramp_dsl("ramp( primary , 500 )", PALETTES)
        assert result is not None


class TestResolveColor:
    def test_ramp_dsl_resolved(self):
        result = resolve_color("ramp(primary, 500)", PALETTES)
        assert result == "oklch(55% 0.2 260)"

    def test_raw_oklch_passthrough(self):
        raw = "oklch(55% 0.20 260)"
        assert resolve_color(raw, PALETTES) == raw

    def test_css_var_passthrough(self):
        var = "var(--color-brand)"
        assert resolve_color(var, PALETTES) == var

    def test_arbitrary_string_passthrough(self):
        s = "1.5rem"
        assert resolve_color(s, PALETTES) == s
