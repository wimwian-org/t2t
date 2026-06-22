# Changelog

<!-- towncrier release notes start -->

## 0.2.0 (2026-06-22)

### Features

- Initial release of t2t — TOML to Tailwind v4 CSS converter.

  Converts a `.toml` design token file into four Tailwind v4-compatible CSS files
  (`theme.css`, `typography.css`, `utilities.css`, `wimwian.css`) using the CSS
  space-toggle dark mode trick. Supports oklch color ramps, WCAG AA contrast
  validation, sRGB gamut checking, and `ramp()` DSL shorthand. (#1)
