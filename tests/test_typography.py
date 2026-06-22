"""Tests for typography.py — _to_rem, derive_leading, derive_tracking."""

import pytest
from t2t.typography import _to_rem, derive_leading, derive_tracking


class TestToRem:
    def test_rem_identity(self):
        assert _to_rem("1rem") == pytest.approx(1.0)
        assert _to_rem("1.5rem") == pytest.approx(1.5)

    def test_em_identity(self):
        assert _to_rem("1em") == pytest.approx(1.0)
        assert _to_rem("2em") == pytest.approx(2.0)

    def test_px_divides_by_16(self):
        assert _to_rem("16px") == pytest.approx(1.0)
        assert _to_rem("24px") == pytest.approx(1.5)
        assert _to_rem("32px") == pytest.approx(2.0)

    def test_pt_conversion(self):
        # 12pt × 1.3333 / 16 ≈ 1.0
        assert _to_rem("12pt") == pytest.approx(1.0, rel=0.01)

    def test_unrecognised_unit_returns_none(self):
        assert _to_rem("1vw") is None
        assert _to_rem("1ch") is None

    def test_unparseable_returns_none(self):
        assert _to_rem("auto") is None
        assert _to_rem("") is None


class TestDeriveLeading:
    def test_threshold_1rem(self):
        assert derive_leading("1rem") == 1.5

    def test_threshold_below_1rem(self):
        assert derive_leading("0.875rem") == 1.5

    def test_threshold_1_5rem(self):
        assert derive_leading("1.5rem") == 1.4

    def test_threshold_between_1_and_1_5(self):
        assert derive_leading("1.125rem") == 1.4

    def test_threshold_2rem(self):
        assert derive_leading("2rem") == 1.3

    def test_threshold_2_5rem(self):
        assert derive_leading("2.5rem") == 1.2

    def test_threshold_above_2_5rem(self):
        assert derive_leading("3rem") == 1.1
        assert derive_leading("4rem") == 1.1

    def test_px_unit_converted(self):
        # 16px == 1rem → 1.5
        assert derive_leading("16px") == 1.5
        # 24px == 1.5rem → 1.4
        assert derive_leading("24px") == 1.4

    def test_unknown_unit_raises(self):
        with pytest.raises(ValueError, match="Cannot derive line-height"):
            derive_leading("1vw")


class TestDeriveTracking:
    def test_at_or_below_1_5rem_returns_none(self):
        assert derive_tracking("1rem") is None
        assert derive_tracking("1.5rem") is None
        assert derive_tracking("0.75rem") is None

    def test_between_1_5_and_2_5rem(self):
        assert derive_tracking("2rem") == pytest.approx(-0.025)

    def test_at_2_5rem(self):
        assert derive_tracking("2.5rem") == pytest.approx(-0.025)

    def test_above_2_5rem(self):
        assert derive_tracking("3rem") == pytest.approx(-0.05)

    def test_px_unit_converted(self):
        # 32px = 2rem → -0.025
        assert derive_tracking("32px") == pytest.approx(-0.025)
        # 48px = 3rem → -0.05
        assert derive_tracking("48px") == pytest.approx(-0.05)

    def test_unknown_unit_returns_none(self):
        assert derive_tracking("2vw") is None
