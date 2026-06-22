"""Tests for tokens.py — resolve_token_color, build_token_maps."""

import pytest
from t2t.tokens import resolve_token_color, build_token_maps

BASE    = "oklch(55% 0.20 260)"
PAL_MAP = {"primary": BASE, "mono": "oklch(50% 0 0)"}


class TestResolveTokenColor:
    def test_integer_with_palette(self):
        result = resolve_token_color(500, BASE, PAL_MAP)
        assert result == "oklch(55% 0.2 260)"

    def test_integer_zero(self):
        result = resolve_token_color(0, BASE, PAL_MAP)
        assert result.startswith("oklch(0%")

    def test_integer_1000(self):
        result = resolve_token_color(1000, BASE, PAL_MAP)
        assert result.startswith("oklch(100%")

    def test_integer_without_palette_raises(self):
        with pytest.raises(ValueError, match="palette"):
            resolve_token_color(500, None, PAL_MAP)

    def test_ramp_dsl_string(self):
        result = resolve_token_color("ramp(primary, 500)", None, PAL_MAP)
        assert result == "oklch(55% 0.2 260)"

    def test_raw_oklch_string(self):
        result = resolve_token_color("oklch(55% 0.20 260)", None, PAL_MAP)
        assert result == "oklch(55% 0.20 260)"

    def test_arbitrary_string_passthrough(self):
        result = resolve_token_color("var(--color-brand)", None, PAL_MAP)
        assert result == "var(--color-brand)"


class TestBuildTokenMaps:
    def test_empty(self):
        light, dark = build_token_maps([], PAL_MAP)
        assert light == {} and dark == {}

    def test_integer_light_with_palette(self):
        tokens = [{"name": "--color-accent", "palette": "primary", "light": 200}]
        light, dark = build_token_maps(tokens, PAL_MAP)
        assert "--color-accent" in light
        # dark defaults to 1000 - 200 = 800
        assert "--color-accent" in dark
        dark_L, _, _, _  = _parse(dark["--color-accent"])
        light_L, _, _, _ = _parse(light["--color-accent"])
        assert dark_L > light_L

    def test_integer_dark_default_is_1000_minus_light(self):
        tokens = [{"name": "--color-x", "palette": "primary", "light": 200}]
        light, dark = build_token_maps(tokens, PAL_MAP)
        from t2t.color import color_ramp
        assert dark["--color-x"] == color_ramp(BASE, 800)

    def test_explicit_dark_overrides_default(self):
        tokens = [{"name": "--color-x", "palette": "primary", "light": 200, "dark": 900}]
        light, dark = build_token_maps(tokens, PAL_MAP)
        from t2t.color import color_ramp
        assert dark["--color-x"] == color_ramp(BASE, 900)

    def test_ramp_dsl_light_auto_dark_complement(self):
        tokens = [{"name": "--color-x", "light": "ramp(primary, 750)"}]
        light, dark = build_token_maps(tokens, PAL_MAP)
        from t2t.color import color_ramp
        assert dark["--color-x"] == color_ramp(BASE, 250)

    def test_ramp_dsl_light_auto_dark_ignored_when_explicit(self):
        tokens = [{"name": "--color-x", "light": "ramp(primary, 750)", "dark": "ramp(primary, 900)"}]
        light, dark = build_token_maps(tokens, PAL_MAP)
        from t2t.color import color_ramp
        assert dark["--color-x"] == color_ramp(BASE, 900)

    def test_string_light_no_dark_omitted_from_dark(self):
        tokens = [{"name": "--color-x", "light": "oklch(55% 0.10 260)"}]
        light, dark = build_token_maps(tokens, PAL_MAP)
        assert "--color-x" in light
        assert "--color-x" not in dark

    def test_string_light_with_explicit_dark(self):
        tokens = [{
            "name":  "--color-x",
            "light": "oklch(90% 0.02 260)",
            "dark":  "oklch(20% 0.02 260)",
        }]
        light, dark = build_token_maps(tokens, PAL_MAP)
        assert light["--color-x"] == "oklch(90% 0.02 260)"
        assert dark["--color-x"]  == "oklch(20% 0.02 260)"

    def test_ramp_dsl_as_string_value(self):
        tokens = [{
            "name":  "--color-accent",
            "light": "ramp(primary, 200)",
            "dark":  "ramp(primary, 800)",
        }]
        light, dark = build_token_maps(tokens, PAL_MAP)
        from t2t.color import color_ramp
        assert light["--color-accent"] == color_ramp(BASE, 200)
        assert dark["--color-accent"]  == color_ramp(BASE, 800)

    def test_muted_generates_light_variant(self):
        tokens = [{"name": "--color-x", "light": "oklch(55% 0.10 260)", "muted": 0.5}]
        light, dark = build_token_maps(tokens, PAL_MAP)
        assert "--color-x-muted" in light
        assert "/ 0.5" in light["--color-x-muted"]

    def test_disabled_generates_light_variant(self):
        tokens = [{"name": "--color-x", "light": "oklch(55% 0.10 260)", "disabled": 0.3}]
        light, dark = build_token_maps(tokens, PAL_MAP)
        assert "--color-x-disabled" in light
        assert "/ 0.3" in light["--color-x-disabled"]

    def test_muted_and_disabled_both_light_and_dark(self):
        tokens = [{
            "name":     "--color-x",
            "light":    "oklch(90% 0.05 260)",
            "dark":     "oklch(20% 0.05 260)",
            "muted":    0.6,
            "disabled": 0.3,
        }]
        light, dark = build_token_maps(tokens, PAL_MAP)
        assert "--color-x-muted"    in light and "--color-x-muted"    in dark
        assert "--color-x-disabled" in light and "--color-x-disabled" in dark

    def test_muted_string_alpha_accepted(self):
        tokens = [{"name": "--color-x", "light": "oklch(55% 0.10 260)", "muted": "0.75"}]
        light, _ = build_token_maps(tokens, PAL_MAP)
        assert "--color-x-muted" in light
        assert "/ 0.75" in light["--color-x-muted"]

    def test_muted_without_dark_no_dark_variant(self):
        tokens = [{"name": "--color-x", "light": "oklch(55% 0.10 260)", "muted": 0.5}]
        light, dark = build_token_maps(tokens, PAL_MAP)
        assert "--color-x-muted" in light
        assert "--color-x-muted" not in dark

    def test_alpha_variants_preserve_hue(self):
        tokens = [{"name": "--color-x", "light": "oklch(55% 0.10 260)", "muted": 0.5}]
        light, _ = build_token_maps(tokens, PAL_MAP)
        from t2t.color import parse_oklch
        L, C, H, A = parse_oklch(light["--color-x-muted"])
        assert H == 260
        assert A == 0.5

    def test_multiple_tokens(self):
        tokens = [
            {"name": "--color-surface", "palette": "mono", "light": 950, "dark": 50},
            {"name": "--color-text",    "palette": "mono", "light": 100, "dark": 900},
        ]
        light, dark = build_token_maps(tokens, PAL_MAP)
        assert "--color-surface" in light
        assert "--color-text" in light

    def test_out_of_gamut_exits(self):
        tokens = [{"name": "--bad", "light": "oklch(55% 0.40 260)"}]
        with pytest.raises(SystemExit):
            build_token_maps(tokens, PAL_MAP)


class TestPointerToken:
    def test_value_passthrough(self):
        tokens = [{"name": "--surface-bg", "value": "var(--surface-mono-bg)"}]
        light, dark = build_token_maps(tokens, PAL_MAP)
        assert light["--surface-bg"] == "var(--surface-mono-bg)"
        assert "--surface-bg" not in dark


def _parse(color: str):
    from t2t.color import parse_oklch
    return parse_oklch(color)
