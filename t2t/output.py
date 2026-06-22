"""
Console summary table printed to stderr on successful conversion.

Printed to stderr so that stdout (which may be piped to a file) carries only
the CSS output. ANSI colour is used when stderr is a TTY; plain text otherwise.

Layout:
    Tokens section   — one row per palette step, [[token]], and [root] entry
    Contrast section — markdown table, one row per [[contrast]] pair

Contrast row symbols:
    ✓  (green)  — passes AAA threshold
    ⚠! (yellow) — passes AA but not AAA
    ✗  (red)    — fails AA minimum
"""

import sys

from .contrast import contrast_ratio, resolve_contrast_color, _THRESHOLDS


# ── ANSI ──────────────────────────────────────────────────────────────────────

def _ansi(code: str, text: str) -> str:  # pragma: no cover
    return f"\033[{code}m{text}\033[0m" if sys.stderr.isatty() else text

def green(t: str)  -> str: return _ansi("32", t)   # pragma: no cover
def yellow(t: str) -> str: return _ansi("33", t)   # pragma: no cover
def red(t: str)    -> str: return _ansi("31", t)    # pragma: no cover
def bold(t: str)   -> str: return _ansi("1",  t)    # pragma: no cover


# ── Tokens table (plain aligned columns) ─────────────────────────────────────

_TOKEN_WIDTHS = (32, 28, 28)
_TOKEN_HR     = "─" * (sum(_TOKEN_WIDTHS) + 2 * (len(_TOKEN_WIDTHS) - 1))


def _token_row(*cells: str) -> str:  # pragma: no cover
    return "  ".join(f"{c:<{w}}" for c, w in zip(cells, _TOKEN_WIDTHS))


# ── Contrast table (markdown with fixed column widths) ────────────────────────

_LABEL_W = 32   # visible width of the label column
_GRADE_W = 14   # visible width of each grade cell  ("21.0:1 ⚠! AA " = 13 chars)

_MD_SEP = (
    f"|{'-' * (_LABEL_W + 2)}"
    f"|{'-' * (_GRADE_W + 2)}"
    f"|{'-' * (_GRADE_W + 2)}|"
)


def _grade_cell(ratio: float, aa: float, aaa: float) -> str:  # pragma: no cover
    """
    Return a _GRADE_W-wide grade cell for the contrast markdown table.

    The symbol is ANSI-coloured when stderr is a TTY. Padding is computed from
    the plain (no-ANSI) string so column widths stay consistent.
    """
    prefix = f"{ratio:.1f}:1"
    if ratio >= aaa:
        sym_plain, sym_colored, grade = "✓",  green("✓"),   "AAA"
    elif ratio >= aa:
        sym_plain, sym_colored, grade = "⚠!", yellow("⚠!"), "AA "
    else:
        sym_plain, sym_colored, grade = "✗",  red("✗"),     "FAIL"

    plain   = f"{prefix} {sym_plain} {grade}"
    colored = f"{prefix} {sym_colored} {grade}"
    pad     = " " * max(0, _GRADE_W - len(plain))
    return colored + pad


def _md_row(label: str, light: str, dark: str) -> str:  # pragma: no cover
    """Render one markdown table row. label is padded; light/dark arrive pre-padded."""
    return f"| {label:<{_LABEL_W}} | {light} | {dark} |"


# ── Public API ────────────────────────────────────────────────────────────────

def build_report(data: dict, palette_map: dict[str, str],
                 light_map: dict[str, str], dark_map: dict[str, str]) -> str:
    """
    Build a markdown report string suitable for writing to report.md.

    No ANSI codes — symbols are plain unicode so the file renders correctly
    in any markdown viewer.
    """
    meta    = data.get("meta", {})
    name    = meta.get("name", "theme")
    version = meta.get("version", "")
    title   = f"{name} v{version}" if version else name

    lines: list[str] = [f"# {title}\n", "## Tokens\n",
                         "| Name | Light | Dark |",
                         "|------|-------|------|"]

    for tok_name, light_val in light_map.items():
        dark_val = dark_map.get(tok_name, "—")
        lines.append(f"| `{tok_name}` | `{light_val}` | `{dark_val}` |")
    for key in data.get("root", {}):
        lines.append(f"| `{key}` | — | — |")

    pairs = data.get("contrast", [])
    if pairs:
        lines += ["", "## Contrast\n",
                  "| Label | Light | Dark |",
                  "|-------|-------|------|"]
        for pair in pairs:
            label = pair["label"]
            large = pair.get("large", False)
            aa, aaa = _THRESHOLDS[large]
            cells: list[str] = [label]
            for theme in ("light", "dark"):
                bg    = resolve_contrast_color(pair["bg"], light_map, dark_map, palette_map, theme)
                fg    = resolve_contrast_color(pair["fg"], light_map, dark_map, palette_map, theme)
                ratio = contrast_ratio(bg, fg)
                if ratio >= aaa:
                    badge = f"{ratio:.1f}:1 ✓ AAA"
                elif ratio >= aa:
                    badge = f"{ratio:.1f}:1 ⚠! AA"
                else:
                    badge = f"{ratio:.1f}:1 ✗ FAIL"
                cells.append(badge)
            lines.append(f"| {cells[0]} | {cells[1]} | {cells[2]} |")

    return "\n".join(lines) + "\n"


def print_summary(data: dict, palette_map: dict[str, str],  # pragma: no cover
                  light_map: dict[str, str], dark_map: dict[str, str],
                  contrast_warnings: list[str]) -> None:
    """
    Print the tokens and contrast summary tables to stderr.

    Args:
        data:              Parsed TOML dict.
        palette_map:       Palette name → base color.
        light_map:         Resolved [[token]] light values.
        dark_map:          Resolved [[token]] dark values.
        contrast_warnings: Warning strings from validate_contrast().
    """
    e = sys.stderr

    # ── Tokens ────────────────────────────────────────────────────────────────
    print(bold("Tokens"), file=e)
    print(_TOKEN_HR, file=e)
    print(_token_row("Name", "Light", "Dark"), file=e)
    print(_TOKEN_HR, file=e)

    for name, light_val in light_map.items():
        print(_token_row(name, light_val, dark_map.get(name, "—")), file=e)

    for key in data.get("root", {}):
        print(_token_row(key, "—", "—"), file=e)

    print(_TOKEN_HR, file=e)
    print(file=e)

    # ── Contrast ──────────────────────────────────────────────────────────────
    pairs = data.get("contrast", [])
    if not pairs:
        return

    print(bold("Contrast"), file=e)
    print(_md_row("Label", f"{'Light':<{_GRADE_W}}", f"{'Dark':<{_GRADE_W}}"), file=e)
    print(_MD_SEP, file=e)

    for pair in pairs:
        label = pair["label"]
        large = pair.get("large", False)
        aa, aaa = _THRESHOLDS[large]
        cells: list[str] = [label]
        for theme in ("light", "dark"):
            bg    = resolve_contrast_color(pair["bg"], light_map, dark_map, palette_map, theme)
            fg    = resolve_contrast_color(pair["fg"], light_map, dark_map, palette_map, theme)
            ratio = contrast_ratio(bg, fg)
            cells.append(_grade_cell(ratio, aa, aaa))
        print(_md_row(*cells), file=e)

    print(_MD_SEP, file=e)
    if contrast_warnings:
        print(yellow(f"⚠  {len(contrast_warnings)} warning(s) — passes AA but not AAA"), file=e)
    print(file=e)
