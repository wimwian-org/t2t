"""Tests for gamut.py — oklch_to_linear_srgb, check_gamut."""

import pytest
from t2t.gamut import oklch_to_linear_srgb, check_gamut


class TestOklchToLinearSrgb:
    def test_black(self):
        R, G, B = oklch_to_linear_srgb(0, 0, 0)
        assert R == pytest.approx(0.0, abs=1e-6)
        assert G == pytest.approx(0.0, abs=1e-6)
        assert B == pytest.approx(0.0, abs=1e-6)

    def test_white(self):
        R, G, B = oklch_to_linear_srgb(100, 0, 0)
        assert R == pytest.approx(1.0, abs=1e-4)
        assert G == pytest.approx(1.0, abs=1e-4)
        assert B == pytest.approx(1.0, abs=1e-4)

    def test_mid_grey_in_gamut(self):
        R, G, B = oklch_to_linear_srgb(50, 0, 0)
        assert 0.0 <= R <= 1.0
        assert 0.0 <= G <= 1.0
        assert 0.0 <= B <= 1.0
        # achromatic: all channels equal
        assert R == pytest.approx(G, abs=1e-6)
        assert G == pytest.approx(B, abs=1e-6)

    def test_high_chroma_may_be_out_of_gamut(self):
        # Very saturated color — at least one channel outside [0,1]
        R, G, B = oklch_to_linear_srgb(55, 0.40, 260)
        assert any(v < -1e-4 or v > 1 + 1e-4 for v in (R, G, B))


class TestCheckGamut:
    def test_in_gamut_passes(self):
        # Should not raise or exit
        check_gamut("oklch(55% 0.10 260)", "test")

    def test_black_passes(self):
        check_gamut("oklch(0% 0 0)", "black")

    def test_white_passes(self):
        check_gamut("oklch(100% 0 0)", "white")

    def test_out_of_gamut_exits(self):
        with pytest.raises(SystemExit) as exc:
            check_gamut("oklch(55% 0.40 260)", "high-chroma")
        assert exc.value.code == 1

    def test_error_message_contains_label(self, capsys):
        with pytest.raises(SystemExit):
            check_gamut("oklch(55% 0.40 260)", "--color-bad")
        captured = capsys.readouterr()
        assert "--color-bad" in captured.err
