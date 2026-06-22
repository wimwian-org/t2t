"""Tests for color.py — parse_oklch, fmt_oklch, is_oklch, color_ramp."""

import pytest
from t2t.color import parse_oklch, fmt_oklch, is_oklch, color_ramp


class TestParseOklch:
    def test_basic(self):
        L, C, H, A = parse_oklch("oklch(55% 0.20 260)")
        assert L == 55.0
        assert C == 0.20
        assert H == 260.0
        assert A == 1.0

    def test_alpha_fraction(self):
        _, _, _, A = parse_oklch("oklch(55% 0.20 260 / 0.5)")
        assert A == 0.5

    def test_alpha_percent(self):
        _, _, _, A = parse_oklch("oklch(55% 0.20 260 / 50%)")
        assert A == pytest.approx(0.5)

    def test_alpha_zero(self):
        _, _, _, A = parse_oklch("oklch(55% 0.20 260 / 0)")
        assert A == 0.0

    def test_alpha_one_fraction(self):
        _, _, _, A = parse_oklch("oklch(55% 0.20 260 / 1.0)")
        assert A == 1.0

    def test_black(self):
        L, C, H, A = parse_oklch("oklch(0% 0 0)")
        assert L == 0.0 and C == 0.0 and H == 0.0 and A == 1.0

    def test_white(self):
        L, C, H, _ = parse_oklch("oklch(100% 0 0)")
        assert L == 100.0

    def test_case_insensitive(self):
        L, C, H, _ = parse_oklch("OKLCH(55% 0.20 260)")
        assert L == 55.0

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Cannot parse oklch color"):
            parse_oklch("red")

    def test_hex_raises(self):
        with pytest.raises(ValueError):
            parse_oklch("#ff0000")


class TestFmtOklch:
    def test_opaque_omits_alpha(self):
        assert fmt_oklch(55, 0.2, 260) == "oklch(55% 0.2 260)"

    def test_alpha_included(self):
        assert fmt_oklch(55, 0.2, 260, 0.5) == "oklch(55% 0.2 260 / 0.5)"

    def test_zero_chroma(self):
        assert fmt_oklch(0, 0, 0) == "oklch(0% 0 0)"

    def test_4g_precision(self):
        # :.4g should not produce unnecessary trailing zeros
        result = fmt_oklch(5.5, 0.02, 260)
        assert result == "oklch(5.5% 0.02 260)"


class TestIsOklch:
    def test_oklch_string(self):
        assert is_oklch("oklch(55% 0.20 260)") is True

    def test_uppercase(self):
        assert is_oklch("OKLCH(55% 0.20 260)") is True

    def test_non_oklch(self):
        assert is_oklch("red") is False
        assert is_oklch("var(--color-x)") is False
        assert is_oklch("#ff0000") is False
        assert is_oklch("ramp(primary, 400)") is False


class TestColorRamp:
    BASE = "oklch(55% 0.20 260)"

    def test_step_zero_is_black(self):
        result = color_ramp(self.BASE, 0)
        L, C, H, _ = parse_oklch(result)
        assert L == 0.0 and C == 0.0

    def test_step_negative_clamps_to_black(self):
        assert color_ramp(self.BASE, -10) == color_ramp(self.BASE, 0)

    def test_step_500_returns_base(self):
        result = color_ramp(self.BASE, 500)
        assert result == "oklch(55% 0.2 260)"

    def test_step_1000_is_white(self):
        result = color_ramp(self.BASE, 1000)
        L, C, _, _ = parse_oklch(result)
        assert L == 100.0 and C == 0.0

    def test_step_over_1000_clamps_to_white(self):
        assert color_ramp(self.BASE, 1500) == color_ramp(self.BASE, 1000)

    def test_step_below_500_darkens(self):
        result = color_ramp(self.BASE, 250)
        L, C, _, _ = parse_oklch(result)
        assert L == pytest.approx(27.5)
        assert C == pytest.approx(0.10)

    def test_step_above_500_lightens(self):
        result = color_ramp(self.BASE, 750)
        L, C, _, _ = parse_oklch(result)
        assert L == pytest.approx(77.5)
        assert C == pytest.approx(0.10)

    def test_hue_preserved(self):
        for step in (0, 250, 500, 750, 1000):
            _, _, H, _ = parse_oklch(color_ramp(self.BASE, step))
            assert H == 260.0

    def test_alpha_parameter_used(self):
        result = color_ramp(self.BASE, 500, 0.5)
        assert result == "oklch(55% 0.2 260 / 0.5)"

    def test_base_alpha_ignored(self):
        with_alpha    = color_ramp("oklch(55% 0.20 260 / 0.3)", 500)
        without_alpha = color_ramp("oklch(55% 0.20 260)", 500)
        assert with_alpha == without_alpha

    def test_base_alpha_ignored_alpha_param_wins(self):
        result = color_ramp("oklch(55% 0.20 260 / 0.3)", 500, 0.5)
        assert "/ 0.5" in result
        assert "0.3" not in result

    def test_alpha_one_omitted(self):
        result = color_ramp(self.BASE, 500, 1.0)
        assert "/" not in result

    # Spec examples
    def test_spec_step_50(self):
        result = color_ramp(self.BASE, 50)
        L, C, _, _ = parse_oklch(result)
        assert L == pytest.approx(5.5)
        assert C == pytest.approx(0.02)

    def test_spec_step_950(self):
        result = color_ramp(self.BASE, 950)
        L, C, _, _ = parse_oklch(result)
        assert L == pytest.approx(95.5)
        assert C == pytest.approx(0.02)
