"""Tests for palette.py — build_palette_map."""

from t2t.palette import build_palette_map


class TestBuildPaletteMap:
    def test_empty(self):
        assert build_palette_map([]) == {}

    def test_single_palette(self):
        palettes = [{"name": "primary", "base": "oklch(55% 0.20 260)"}]
        result = build_palette_map(palettes)
        assert result == {"primary": "oklch(55% 0.20 260)"}

    def test_multiple_palettes(self):
        palettes = [
            {"name": "primary", "base": "oklch(55% 0.20 260)"},
            {"name": "mono",    "base": "oklch(50% 0 0)"},
        ]
        result = build_palette_map(palettes)
        assert len(result) == 2
        assert result["mono"] == "oklch(50% 0 0)"
