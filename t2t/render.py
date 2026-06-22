# Copyright (c) 2026 @wimwian
# SPDX-License-Identifier: MIT
# https://github.com/wimwian-org/t2t
"""
CSS section renderers.

Each public function takes resolved data and returns a CSS string for one
output section. Functions return an empty string when there is nothing to emit
so the caller can filter with a simple truthiness check.

Output order (enforced by `convert()` in main.py):

```
1. @layer base          — @font-face blocks
2. @theme               — --color-* custom properties
3. @layer utilities     — .font-*, .text-* utility classes + [utilities]
4. @layer components    — component rules
5. :root {}             — --L/--D toggles + [root] vars + [[token]] light/dark values
6. [data-theme='dark']  — --L/--D flip (no individual token vars)
7. static               — unlayered rules
```
"""

from .dsl import resolve_color
from .typography import derive_leading, derive_tracking


# ── Internal helpers ──────────────────────────────────────────────────────────

def _split_decls(raw: str) -> list[str]:
    """Split a raw semicolon-delimited declaration string into individual declarations."""
    return [d.strip().rstrip(";") for d in raw.split(";") if d.strip()]


def _rule(selector: str, props: list[str], indent: str = "  ") -> str:
    """Render a CSS rule block with consistent indentation."""
    i2   = indent + "  "
    body = f"\n{i2}".join(f"{p};" for p in props)
    return f"{indent}{selector} {{\n{i2}{body}\n{indent}}}"


# ── Section renderers ─────────────────────────────────────────────────────────

def render_base(fonts: list[dict]) -> str:
    """
    Render @layer base containing @font-face declarations.

    Each [[font]] entry may have one or more [[font.face]] sub-entries.
    Required face fields: family, url. Optional: weight, style, display.
    """
    blocks = []
    for font in fonts:
        for face in font.get("face", []):
            props = [
                f'font-family: "{face["family"]}"',
                f'src: url("{face["url"]}") format("woff2")',
            ]
            if w := face.get("weight"):  props.append(f"font-weight: {w}")
            if s := face.get("style"):   props.append(f"font-style: {s}")
            if d := face.get("display"): props.append(f"font-display: {d}")
            blocks.append(_rule("@font-face", props))
    return ("@layer base {\n" + "\n\n".join(blocks) + "\n}") if blocks else ""


def render_theme(_palettes: list[dict]) -> str:
    """Palette step vars are no longer emitted; raw color tokens are removed."""
    return ""


def render_utilities(fonts: list[dict], typography: dict, utilities: dict) -> str:
    """
    Render font and other utility classes.

    Generates, in order:

    ```
    @utility font-<name> — font-family stack (one per [[font]]), usable with @apply
    @layer utilities     — .text-<key>, .font-<weight>, and [utilities] rules
    ```

    Typography derivation (when not explicitly provided in TOML):

    ```
    line-height:    derived from size via derive_leading()
    font-weight:    defaults to 500
    letter-spacing: derived from size via derive_tracking(), omitted when 0
    ```
    """
    parts = []

    for font in fonts:
        stack = ", ".join(f'"{f}"' if " " in f else f for f in font.get("stack", []))
        parts.append(f"@utility font-{font['name']} {{\n  font-family: {stack};\n}}")

    layer_rules = []

    for key, val in typography.get("sizes", {}).items():
        size     = val["size"]
        leading  = val.get("leading",  derive_leading(size))
        weight   = val.get("weight",   500)
        tracking = derive_tracking(size)
        props    = [f"font-size: {size}", f"line-height: {leading:g}", f"font-weight: {weight}"]
        if tracking is not None:  # pragma: no cover
            props.append(f"letter-spacing: {tracking:g}em")
        layer_rules.append(_rule(f".text-{key}", props))

    for key, val in typography.get("weights", {}).items():  # pragma: no cover
        layer_rules.append(_rule(f".font-{key}", [f"font-weight: {val}"]))

    for selector, decls in utilities.items():  # pragma: no cover
        layer_rules.append(_rule(selector, _split_decls(decls)))

    if layer_rules:
        parts.append("@layer utilities {\n" + "\n\n".join(layer_rules) + "\n}")

    return "\n\n".join(parts) if parts else ""


def render_components(components: dict) -> str:
    """
    Render @layer components from [components].

    Keys are CSS selectors; values are raw semicolon-delimited declaration strings.
    """
    if not components:
        return ""
    rules = [_rule(sel, _split_decls(decls)) for sel, decls in components.items()]
    return "@layer components {\n" + "\n\n".join(rules) + "\n}"


def _var_group(name: str) -> str:
    """Return the first dash-segment of a CSS custom property name as a group key."""
    return name.lstrip("-").split("-")[0]


def _gap(lines: list[str]) -> None:
    """Append a blank line separator only when lines is non-empty."""
    if lines:
        lines.append("")


def render_root(root: dict, palette_map: dict[str, str],
                light_map: dict[str, str], dark_map: dict[str, str],
                comments_map: dict[str, str]) -> str:
    """
    Render the :root {} block.

    Structure:

    ```
    --L / --D   space-toggle (when any dark value exists)
    [root]      raw vars, auto-grouped by first var-name segment with /* comment */
    [[token]]   var(--L, light) var(--D, dark) when dark exists, plain value otherwise;
                /* comment */ inserted before any token in comments_map
    ```
    """
    lines: list[str] = []

    if dark_map:
        lines.append("  --L: initial;")
        lines.append("  --D: ;")

    prev_group: str | None = None
    for key, val in root.items():
        group = _var_group(key)
        if group != prev_group:
            _gap(lines)
            lines.append(f"  /* {group} */")
            prev_group = group
        lines.append(f"  {key}: {resolve_color(str(val), palette_map)};")

    for name, light_val in light_map.items():
        comment = comments_map.get(name)
        if comment:
            _gap(lines)
            lines.append(f"  /* {comment} */")
        if name in dark_map:
            lines.append(f"  {name}: var(--L, {light_val}) var(--D, {dark_map[name]});")
        else:
            lines.append(f"  {name}: {light_val};")

    return (":root {\n" + "\n".join(lines) + "\n}") if lines else ""


def render_dark(dark_map: dict[str, str]) -> str:
    """
    Render the [data-theme='dark'] flip block.

    Flips --L and --D so all var(--L, light) var(--D, dark) token declarations
    resolve to their dark values. Individual token values are not repeated.
    """
    if not dark_map:
        return ""
    return "[data-theme='dark'] {\n  --L: ;\n  --D: initial;\n}"


_WEIGHT_CLASSES: dict[int, str] = {
    100: "font-thin",
    200: "font-extralight",
    300: "font-light",
    400: "font-normal",
    500: "font-medium",
    600: "font-semibold",
    700: "font-bold",
    800: "font-extrabold",
    900: "font-black",
}


def _resolve_weight(d: dict, fallback: int) -> int:
    """Return font-weight as int, checking both 'weight' and 'font-weight' keys."""
    raw = d.get("weight") or d.get("font-weight")
    return int(str(raw)) if raw else fallback


def _is_utility_ref(value: str) -> bool:
    """Return True if value is a bare utility name (no spaces or quotes) rather than a raw CSS stack."""
    return " " not in value and '"' not in value and "'" not in value


def render_text_utilities(text: dict) -> str:
    """
    Render [text] into @utility blocks for typography.css.

    Each category (display, title, heading, body, label, code) emits one
    @utility per size variant. Properties resolved via inheritance:
        font-size    — from size entry (required)
        line-height  — size entry → category default → derive_leading(size)
        font-weight  — size entry → category default → global default (500)
        font-family  — category → global [text] default; utility refs (e.g.
                       font-sans) are folded into @apply; raw stacks use font-family:
        capitalize   — category flag → @apply capitalize
        small-caps   — category flag → font-variant-caps: small-caps (raw CSS)

    Tailwind-compatible properties go in @apply; everything else is raw CSS.
    """
    if not text:
        return ""

    global_weight = _resolve_weight(text, 500)
    global_family = text.get("font-family")
    groups: list[str] = []

    for category, cat_data in text.items():
        if not isinstance(cat_data, dict):
            continue

        comment        = cat_data.get("comment")
        cat_weight     = _resolve_weight(cat_data, global_weight)
        cat_lh         = cat_data.get("line-height")
        cat_family     = cat_data.get("font-family") or global_family
        cat_capitalize = cat_data.get("capitalize", False)
        cat_smallcaps  = cat_data.get("small-caps", False)

        rules: list[str] = []
        for size_key, size_data in cat_data.items():
            if not isinstance(size_data, dict) or "size" not in size_data:
                continue

            size   = size_data["size"]
            lh     = size_data.get("line-height") or cat_lh or derive_leading(size)
            weight = _resolve_weight(size_data, cat_weight)

            apply_parts = [f"text-[{size}]", f"leading-[{lh}]"]
            wc = _WEIGHT_CLASSES.get(weight)
            if wc:
                apply_parts.append(wc)
            if cat_capitalize:
                apply_parts.append("capitalize")
            if cat_family and _is_utility_ref(cat_family):
                apply_parts.append(cat_family)

            inner = [f"  @apply {' '.join(apply_parts)};"]
            if cat_family and not _is_utility_ref(cat_family):
                inner.append(f"  font-family: {cat_family};")
            if cat_smallcaps:
                inner.append("  font-variant-caps: small-caps;")

            rules.append(f"@utility {category}-{size_key} {{\n" + "\n".join(inner) + "\n}")

        if rules:
            prefix = f"/* {comment} */\n" if comment else ""
            groups.append(prefix + "\n".join(rules))

    return "\n\n".join(groups) if groups else ""


def render_tint_utilities(palette_names: list[str], tokens: list[dict]) -> str:
    """
    Render @utility tint-<palette> blocks for utilities.css.

    For each palette, emits a utility that redirects all generic --surface-*
    pointer vars to their --surface-<palette>-* counterparts. This lets any
    element pick up a colour family by applying a single tint-* utility class.
    """
    surface_vars = [
        t["name"] for t in tokens
        if "value" in t and t["name"].startswith("--surface-")
    ]
    if not palette_names or not surface_vars:
        return ""

    rules: list[str] = []
    for palette in palette_names:
        slot_lines = [
            f"  {var}: var(--surface-{palette}-{var[len('--surface-'):]});"
            for var in surface_vars
        ]
        rules.append(f"@utility tint-{palette} {{\n" + "\n".join(slot_lines) + "\n}")

    return "\n\n".join(rules)


def render_static(static: dict) -> str:
    """
    Render unlayered CSS rules from [static].

    Emitted last in the file so they beat all @layer declarations.
    Keys are CSS selectors; values are raw declaration strings.
    """
    if not static:
        return ""
    return "\n\n".join(_rule(sel, _split_decls(decls), indent="") for sel, decls in static.items())
