"""Tests for contrast.py — contrast_ratio, resolve_contrast_color, validate_contrast."""

import pytest
from t2t.contrast import contrast_ratio, resolve_contrast_color, validate_contrast

BLACK = "oklch(0% 0 0)"
WHITE = "oklch(100% 0 0)"
# Mid-grey — contrast vs white ≈ 5.2:1 (AA pass, not AAA)
MID   = "oklch(50% 0 0)"
# Near-black — contrast vs white ≈ 17:1 (AAA pass)
DARK  = "oklch(20% 0 0)"


class TestContrastRatio:
    def test_black_vs_white(self):
        ratio = contrast_ratio(BLACK, WHITE)
        assert ratio == pytest.approx(21.0, rel=0.01)

    def test_white_vs_black_same(self):
        assert contrast_ratio(WHITE, BLACK) == pytest.approx(contrast_ratio(BLACK, WHITE))

    def test_same_color_is_one(self):
        assert contrast_ratio(BLACK, BLACK) == pytest.approx(1.0)
        assert contrast_ratio(WHITE, WHITE) == pytest.approx(1.0)

    def test_ratio_always_gte_one(self):
        for c1, c2 in [(BLACK, MID), (WHITE, MID), (MID, DARK)]:
            assert contrast_ratio(c1, c2) >= 1.0

    def test_mid_grey_vs_white_passes_aa(self):
        ratio = contrast_ratio(MID, WHITE)
        assert ratio >= 4.5

    def test_mid_grey_vs_white_fails_aaa(self):
        ratio = contrast_ratio(MID, WHITE)
        assert ratio < 7.0

    def test_alpha_ignored(self):
        # Alpha should not affect luminance computation
        opaque      = contrast_ratio("oklch(55% 0.10 260)", "oklch(95% 0 0)")
        transparent = contrast_ratio("oklch(55% 0.10 260 / 0.5)", "oklch(95% 0 0)")
        assert opaque == pytest.approx(transparent, rel=0.01)


class TestResolveContrastColor:
    LIGHT = {"--color-bg": "oklch(95% 0 0)", "--color-fg": "oklch(10% 0 0)"}
    DARK  = {"--color-bg": "oklch(10% 0 0)", "--color-fg": "oklch(90% 0 0)"}
    PAL   = {"primary": "oklch(55% 0.20 260)"}

    def test_token_ref_light(self):
        result = resolve_contrast_color("--color-bg", self.LIGHT, self.DARK, self.PAL, "light")
        assert result == "oklch(95% 0 0)"

    def test_token_ref_dark(self):
        result = resolve_contrast_color("--color-bg", self.LIGHT, self.DARK, self.PAL, "dark")
        assert result == "oklch(10% 0 0)"

    def test_ramp_dsl(self):
        result = resolve_contrast_color("ramp(primary, 500)", self.LIGHT, self.DARK, self.PAL, "light")
        assert result == "oklch(55% 0.2 260)"

    def test_raw_oklch_passthrough(self):
        result = resolve_contrast_color(WHITE, self.LIGHT, self.DARK, self.PAL, "light")
        assert result == WHITE

    def test_unknown_token_raises(self):
        with pytest.raises(ValueError, match="unknown token"):
            resolve_contrast_color("--color-missing", self.LIGHT, self.DARK, self.PAL, "light")


class TestValidateContrast:
    PAL   = {}
    LIGHT = {"--bg": WHITE, "--fg": DARK}
    DARK  = {"--bg": BLACK, "--fg": WHITE}

    def _pair(self, bg, fg, large=False):
        return [{"label": "test", "bg": bg, "fg": fg, "large": large}]

    def test_aaa_pass_no_warnings(self):
        warnings = validate_contrast(self._pair(BLACK, WHITE), self.PAL, {}, {})
        assert warnings == []

    def test_aa_not_aaa_warns(self):
        # MID vs WHITE: ~5.2:1 — passes AA (4.5), fails AAA (7.0)
        warnings = validate_contrast(self._pair(MID, WHITE), self.PAL, {}, {})
        assert len(warnings) >= 1
        assert "AA" in warnings[0]

    def test_below_aa_exits(self):
        # Two similar mid-greys → ratio ≈ 1–2:1 → fails AA
        low_contrast = "oklch(48% 0 0)"
        with pytest.raises(SystemExit) as exc:
            validate_contrast(self._pair(MID, low_contrast), self.PAL, {}, {})
        assert exc.value.code == 1

    def test_large_text_lower_threshold(self):
        # oklch(45% 0 0) vs oklch(75% 0 0): ratio ≈ 3.35:1
        # passes large AA (3.0) but fails large AAA (4.5) → warning, not exit
        bg = "oklch(45% 0 0)"
        fg = "oklch(75% 0 0)"
        warnings = validate_contrast(self._pair(bg, fg, large=True), self.PAL, {}, {})
        assert isinstance(warnings, list)
        assert len(warnings) >= 1  # at least one "passes AA not AAA" warning

    def test_token_reference_resolved(self):
        pairs = [{"label": "t", "bg": "--bg", "fg": "--fg"}]
        warnings = validate_contrast(pairs, self.PAL, self.LIGHT, self.DARK)
        # Both light (white/near-black) and dark (black/white) should be AAA
        assert warnings == []

    def test_both_themes_checked(self):
        # Light pair is high contrast; dark pair is low contrast
        light = {"--bg": WHITE, "--fg": WHITE}   # contrast 1:1 → exits
        dark  = {"--bg": BLACK, "--fg": WHITE}
        pairs = [{"label": "t", "bg": "--bg", "fg": "--fg"}]
        with pytest.raises(SystemExit):
            validate_contrast(pairs, self.PAL, light, dark)
