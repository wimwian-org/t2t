# Copyright (c) 2026 @wimwian
# SPDX-License-Identifier: MIT
# https://github.com/wimwian-org/t2t
"""Tests for convert_split and _build_minified in t2t.main."""

import tomllib
import pytest
from t2t.main import _build_minified, convert_split


_MINIMAL = tomllib.loads("""
[[palette]]
name = "primary"
base = "oklch(55% 0.10 260)"

[[token]]
name = "--color-bg"
palette = "primary"
light = 900
dark = 100
""")

_WITH_TEXT = tomllib.loads("""
[[palette]]
name = "mono"
base = "oklch(50% 0 0)"

[[token]]
name = "--color-bg"
light = "oklch(90% 0 0)"

[text]
weight = 500
font-family = "font-sans"

[text.body]
[text.body.md]
size = "1rem"
""")

_WITH_TINTS = tomllib.loads("""
[[palette]]
name = "primary"
base = "oklch(55% 0.10 260)"

[[token]]
name = "--surface-primary-bg"
palette = "primary"
light = 750

[[token]]
name = "--surface-bg"
value = "var(--surface-primary-bg)"
""")


class TestConvertSplit:
    def test_returns_four_keys(self):
        result = convert_split(_MINIMAL)
        assert set(result) == {"theme", "typography", "utilities", "wimwian"}

    def test_wimwian_imports_tailwindcss(self):
        result = convert_split(_MINIMAL)
        assert '@import "tailwindcss";' in result["wimwian"]

    def test_wimwian_always_imports_theme(self):
        result = convert_split(_MINIMAL)
        assert '@import "./theme.css";' in result["wimwian"]

    def test_wimwian_header_uses_meta_name(self):
        data = tomllib.loads('[meta]\nname = "my-theme"\n' + """
[[palette]]
name = "mono"
base = "oklch(50% 0 0)"
""")
        result = convert_split(data)
        assert "my-theme" in result["wimwian"]

    def test_wimwian_header_includes_version(self):
        data = tomllib.loads('[meta]\nname = "t"\nversion = "1.2.3"\n' + """
[[palette]]
name = "mono"
base = "oklch(50% 0 0)"
""")
        result = convert_split(data)
        assert "v1.2.3" in result["wimwian"]

    def test_wimwian_omits_version_when_absent(self):
        result = convert_split(_MINIMAL)
        assert " v" not in result["wimwian"]

    def test_theme_contains_root(self):
        result = convert_split(_MINIMAL)
        assert ":root" in result["theme"]

    def test_theme_contains_dark_toggle(self):
        result = convert_split(_MINIMAL)
        assert "[data-theme='dark']" in result["theme"]

    def test_typography_has_utility_when_text_present(self):
        result = convert_split(_WITH_TEXT)
        assert "@utility body-md" in result["typography"]

    def test_wimwian_imports_typography_when_present(self):
        result = convert_split(_WITH_TEXT)
        assert '@import "./typography.css";' in result["wimwian"]

    def test_wimwian_omits_typography_import_when_empty(self):
        result = convert_split(_MINIMAL)
        assert "./typography.css" not in result["wimwian"]

    def test_wimwian_omits_utilities_import_when_empty(self):
        result = convert_split(_MINIMAL)
        assert "./utilities.css" not in result["wimwian"]

    def test_utilities_contains_tint_when_surface_tokens_present(self):
        result = convert_split(_WITH_TINTS)
        assert "@utility tint-primary" in result["utilities"]

    def test_wimwian_imports_utilities_when_present(self):
        result = convert_split(_WITH_TINTS)
        assert '@import "./utilities.css";' in result["wimwian"]


def _files(theme="", typography="", utilities="", wimwian="") -> dict[str, str]:
    return {"theme": theme, "typography": typography, "utilities": utilities, "wimwian": wimwian}


class TestBuildMinified:
    def test_starts_with_tailwindcss_import(self):
        result = _build_minified(_files(theme=":root { --x: 1; }"))
        assert result.startswith('@import "tailwindcss";')

    def test_no_other_import_statements(self):
        result = _build_minified(_files(
            theme=":root { --x: 1; }",
            utilities="@layer utilities { .foo { color: red; } }",
        ))
        # only the leading tailwindcss import; no ./theme.css, ./typography.css etc.
        assert result.count("@import") == 1

    def test_theme_content_included(self):
        result = _build_minified(_files(theme=":root { --color-bg: oklch(100% 0 0); }"))
        assert "--color-bg" in result

    def test_typography_content_included(self):
        result = _build_minified(_files(typography="@layer utilities { .text-sm { font-size: .875rem; } }"))
        assert ".text-sm" in result

    def test_utilities_content_included(self):
        result = _build_minified(_files(utilities="@layer utilities { .font-sans { font-family: sans-serif; } }"))
        assert ".font-sans" in result

    def test_wimwian_manifest_excluded(self):
        result = _build_minified(_files(
            theme=":root { --x: 1; }",
            wimwian='@import "tailwindcss";\n@import "./theme.css";',
        ))
        assert "./theme.css" not in result

    def test_empty_sections_omitted(self):
        result = _build_minified(_files(theme=":root { --x: 1; }", typography="   ", utilities=""))
        assert result == '@import "tailwindcss";' + ":root{--x:1}"

    def test_all_sections_empty(self):
        result = _build_minified(_files())
        assert result == '@import "tailwindcss";'

    def test_output_is_minified(self):
        theme = ":root {\n  --color-bg: oklch(100% 0 0);\n  --color-fg: oklch(0% 0 0);\n}"
        result = _build_minified(_files(theme=theme))
        assert "\n" not in result
        assert "  " not in result

    def test_comments_stripped(self):
        result = _build_minified(_files(theme="/* generated */ :root { --x: 1; }"))
        assert "generated" not in result

    def test_all_three_sections_consolidated(self):
        result = _build_minified(_files(
            theme=":root { --color-bg: oklch(100% 0 0); }",
            typography="@layer utilities { .text-lg { font-size: 1.5rem; } }",
            utilities="@layer utilities { .font-sans { font-family: sans-serif; } }",
        ))
        assert "--color-bg" in result
        assert ".text-lg" in result
        assert ".font-sans" in result
