# Copyright (c) 2026 @wimwian
# SPDX-License-Identifier: MIT
# https://github.com/wimwian-org/t2t
"""Tests for render.py — render_text_utilities, render_tint_utilities, helpers."""

from t2t.render import (
    _resolve_weight,
    _is_utility_ref,
    render_text_utilities,
    render_tint_utilities,
)


class TestResolveWeight:
    def test_weight_key(self):
        assert _resolve_weight({"weight": 700}, 500) == 700

    def test_font_weight_key(self):
        assert _resolve_weight({"font-weight": "600"}, 500) == 600

    def test_fallback_when_absent(self):
        assert _resolve_weight({}, 500) == 500

    def test_string_value_converted(self):
        assert _resolve_weight({"weight": "400"}, 500) == 400


class TestIsUtilityRef:
    def test_bare_name_is_ref(self):
        assert _is_utility_ref("font-sans") is True

    def test_with_space_is_not_ref(self):
        assert _is_utility_ref("Inter, sans-serif") is False

    def test_with_double_quote_is_not_ref(self):
        assert _is_utility_ref('"Inter"') is False

    def test_with_single_quote_is_not_ref(self):
        assert _is_utility_ref("'Inter'") is False


class TestRenderTextUtilities:
    def test_empty_returns_empty_string(self):
        assert render_text_utilities({}) == ""

    def test_basic_category_emits_utility(self):
        text = {"body": {"md": {"size": "1rem"}}}
        result = render_text_utilities(text)
        assert "@utility body-md" in result

    def test_size_in_apply(self):
        text = {"body": {"md": {"size": "1rem"}}}
        result = render_text_utilities(text)
        assert "text-[1rem]" in result

    def test_comment_emitted_before_rules(self):
        text = {"body": {"comment": "Body text", "md": {"size": "1rem"}}}
        result = render_text_utilities(text)
        assert "/* Body text */" in result
        assert result.index("/* Body text */") < result.index("@utility body-md")

    def test_category_line_height_used_as_fallback(self):
        text = {"body": {"line-height": "1.6", "md": {"size": "1rem"}}}
        result = render_text_utilities(text)
        assert "leading-[1.6]" in result

    def test_size_entry_line_height_overrides_category(self):
        text = {"body": {"line-height": "1.6", "md": {"size": "1rem", "line-height": "1.8"}}}
        result = render_text_utilities(text)
        assert "leading-[1.8]" in result

    def test_capitalize_added_to_apply(self):
        text = {"label": {"capitalize": True, "md": {"size": "0.875rem"}}}
        result = render_text_utilities(text)
        assert "capitalize" in result

    def test_small_caps_emits_css_property(self):
        text = {"label": {"small-caps": True, "md": {"size": "0.875rem"}}}
        result = render_text_utilities(text)
        assert "font-variant-caps: small-caps" in result

    def test_utility_ref_family_in_apply(self):
        text = {
            "font-family": "font-sans",
            "body": {"md": {"size": "1rem"}},
        }
        result = render_text_utilities(text)
        assert "font-sans" in result
        assert "font-family:" not in result

    def test_raw_stack_family_emits_css_property(self):
        text = {
            "body": {
                "font-family": "Inter, sans-serif",
                "md": {"size": "1rem"},
            }
        }
        result = render_text_utilities(text)
        assert "font-family: Inter, sans-serif" in result

    def test_weight_class_in_apply(self):
        text = {"body": {"weight": 700, "md": {"size": "1rem"}}}
        result = render_text_utilities(text)
        assert "font-bold" in result

    def test_unknown_weight_not_in_apply(self):
        text = {"body": {"weight": 350, "md": {"size": "1rem"}}}
        result = render_text_utilities(text)
        assert "font-" not in result.split("@apply")[1].split(";")[0]

    def test_non_dict_top_level_key_ignored(self):
        text = {"weight": 500, "font-family": "font-sans", "body": {"md": {"size": "1rem"}}}
        result = render_text_utilities(text)
        assert "@utility body-md" in result

    def test_multiple_categories_separated(self):
        text = {
            "body":    {"md": {"size": "1rem"}},
            "display": {"lg": {"size": "3rem"}},
        }
        result = render_text_utilities(text)
        assert "@utility body-md" in result
        assert "@utility display-lg" in result


class TestRenderTintUtilities:
    _TOKENS = [
        {"name": "--surface-primary-bg", "palette": "primary", "light": 750},
        {"name": "--surface-bg",         "value": "var(--surface-primary-bg)"},
    ]

    def test_emits_utility_per_palette(self):
        result = render_tint_utilities(["primary", "mono"], self._TOKENS)
        assert "@utility tint-primary" in result
        assert "@utility tint-mono" in result

    def test_remaps_surface_vars(self):
        result = render_tint_utilities(["primary"], self._TOKENS)
        assert "--surface-bg: var(--surface-primary-bg)" in result

    def test_empty_when_no_palettes(self):
        assert render_tint_utilities([], self._TOKENS) == ""

    def test_empty_when_no_surface_tokens(self):
        tokens = [{"name": "--color-bg", "palette": "primary", "light": 900}]
        assert render_tint_utilities(["primary"], tokens) == ""
