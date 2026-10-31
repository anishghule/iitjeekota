"""CSS emitters: tokens.css, typography.css and fonts.css.

Naming: palette primitives are `--color-{family}-{step}`; surface roles are bare
(`--text`, `--accent`) and are set per `[data-surface]`; type variants are
`--type-{variant}-{size|lh|tracking|weight|stretch}` and only typography.css
turns them into rules.
"""

from __future__ import annotations

from typing import Any

from .colour import css_rgb

GENERIC_FAMILIES = {"serif", "sans-serif", "monospace", "system-ui", "cursive", "fantasy", "ui-sans-serif", "ui-serif"}
ROOT_REM = 16


def num(value: float, places: int = 4) -> str:
    text = f"{value:.{places}f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def rem(px: float) -> str:
    return f"{num(px / ROOT_REM)}rem" if px else "0"


def fluid(min_px: float, max_px: float, vmin: float, vmax: float) -> str:
    """clamp() that grows linearly from min_px at vmin to max_px at vmax (rem based, so it respects user font size)."""
    if min_px == max_px:
        return rem(min_px)
    slope = (max_px - min_px) / (vmax - vmin)
    return f"clamp({rem(min_px)}, {rem(min_px - slope * vmin)} + {num(slope * 100)}vw, {rem(max_px)})"


def font_stack(families: list[str]) -> str:
    return ", ".join(f if f in GENERIC_FAMILIES else f'"{f}"' for f in families)


def shadow(layers: list[dict[str, Any]]) -> str:
    parts = []
    for layer in layers:
        dims = " ".join(f"{num(layer[k])}px" if layer[k] else "0" for k in ("offsetX", "offsetY", "blur", "spread"))
        parts.append(("inset " if layer.get("inset") else "") + f"{dims} {css_rgb(layer['color'], layer.get('alpha', 1))}")
    return ", ".join(parts)


def cubic_bezier(points: list[float]) -> str:
    return f"cubic-bezier({', '.join(num(p, 3) for p in points)})"


def rule(selector: str, declarations: list[str], indent: str = "") -> str:
    body = "".join(f"{indent}  {d}\n" for d in declarations)
    return f"{indent}{selector} {{\n{body}{indent}}}\n"


def _type_declarations(tree: dict[str, Any], script: str) -> list[str]:
    """Line height, tracking and weight per variant for one script ('latin' or 'devanagari')."""
    out = []
    deva = tree["type"]["devanagari"]
    for variant, spec in tree["type"]["scale"].items():
        if script == "devanagari":
            out += [f"--type-{variant}-lh: {num(deva['lineHeight'][variant])};",
                    f"--type-{variant}-tracking: 0em;",
                    f"--type-{variant}-weight: {deva['weight'][variant]};"]
        else:
            out += [f"--type-{variant}-lh: {num(spec['lineHeight'])};",
                    f"--type-{variant}-tracking: {num(spec['tracking'])}em;",
                    f"--type-{variant}-weight: {spec['weight']};"]
    return out


def tokens_css(tree: dict[str, Any]) -> str:
    vmin, vmax = tree["type"]["viewport"]["min"], tree["type"]["viewport"]["max"]
    families = tree["font"]["family"]
    root = ["/* Palette: primitives only. Components use the surface roles below. */"]
    for family, steps in tree["color"].items():
        root += [f"--color-{family}-{step}: {value};" for step, value in steps.items()]

    root.append("/* Type */")
    root += [f"--font-{role}: {font_stack(stack)};" for role, stack in families.items()]
    root += [f"--weight-{name}: {value};" for name, value in tree["font"]["weight"].items()]
    root += [f"--stretch-{name}: {num(value)}%;" for name, value in tree["font"]["stretch"].items()]
    for variant, spec in tree["type"]["scale"].items():
        root += [f"--type-{variant}-size: {fluid(spec['min'], spec['max'], vmin, vmax)};",
                 f"--type-{variant}-stretch: {num(spec['stretch'])}%;"]
    root += _type_declarations(tree, "latin")

    root.append("/* Space, radius, layout, layers */")
    for name, value in tree["space"].items():
        if name == "fluid":
            root += [f"--space-{k}: {fluid(v['min'], v['max'], vmin, vmax)};" for k, v in value.items()]
        else:
            root.append(f"--space-{name}: {rem(value)};")
    root += [f"--radius-{name}: {'9999px' if value >= 9999 else rem(value)};" for name, value in tree["radius"].items()]
    root += [f"--{name}: {value if isinstance(value, str) else rem(value)};" for name, value in tree["layout"].items()]
    root += [f"--nav-{name}: {value if isinstance(value, str) else rem(value)};"
             for name, value in tree["nav"].items() if name != "menu-from"]
    root += [f"--z-{name}: {value};" for name, value in tree["z"].items()]

    root.append("/* Motion */")
    root += [f"--ease-{name}: {cubic_bezier(value)};" for name, value in tree["motion"]["ease"].items()]
    root += [f"--dur-{name}: {num(value)}ms;" for name, value in tree["motion"]["duration"].items()]

    root.append("/* Icons */")
    root += [f"--icon-{name}: {rem(value)};" for name, value in tree["icon"]["size"].items()]
    root.append(f"--icon-stroke: {num(tree['icon']['stroke'])};")

    out = [rule(":root", root)]
    default_surface = next(iter(tree["surface"]))
    for surface, roles in tree["surface"].items():
        scheme = "dark" if surface == default_surface else "light"
        decls = [f"color-scheme: {scheme};"] + [f"--{role}: {value};" for role, value in roles.items()]
        decls += [f"--shadow-{level}: {shadow(layers)};" for level, layers in tree["shadow"][surface].items()]
        selector = f'[data-surface="{surface}"]'
        out.append(rule(f":root, {selector}" if surface == default_surface else selector, decls))

    deva_locales = tree["type"]["devanagari"]["locales"]
    latin_locales = tree["type"]["latin"]["locales"]
    out.append("/* Devanagari locales: Devanagari fonts, taller lines, no letter-spacing (keeps the shirorekha joined). */\n")
    out.append(rule(", ".join(f":lang({loc})" for loc in deva_locales),
                    ["--font-display: var(--font-devanagari);", "--font-body: var(--font-devanagari);",
                     "--measure: var(--measure-devanagari);"] + _type_declarations(tree, "devanagari")))
    out.append("/* Latin locales: restores Latin type inside a Devanagari page (an English quote, a name). */\n")
    out.append(rule(", ".join(f":lang({loc})" for loc in latin_locales),
                    [f"--font-display: {font_stack(families['display'])};", f"--font-body: {font_stack(families['body'])};",
                     f"--measure: {tree['layout']['measure']};"] + _type_declarations(tree, "latin")))
    still = [f"--dur-{name}: 0ms;" for name in tree["motion"]["duration"]]
    out.append("@media (prefers-reduced-motion: reduce) {\n" + rule(":root", still, "  ") + "}\n")
    return "\n".join(out)


def breakpoints_css(tree: dict[str, Any]) -> str:
    """Visibility classes from the breakpoint tokens, since media queries cannot read custom properties.
    .from-{bp} shows only from that width up, .below-{bp} only below it; .nav-wide and .nav-narrow
    follow nav.menu-from. Hidden elements keep their own display when shown."""
    hide = ["display: none !important;"]
    out = []
    breakpoints = dict(tree["breakpoint"])
    pairs = [(f".from-{name}", f".below-{name}", px) for name, px in breakpoints.items()]
    pairs.append((".nav-wide", ".nav-narrow", breakpoints[tree["nav"]["menu-from"]]))
    for wide, narrow, px in pairs:
        out.append(f"@media (width < {rem(px)}) {{\n" + rule(wide, hide, "  ") + "}\n")
        out.append(f"@media (width >= {rem(px)}) {{\n" + rule(narrow, hide, "  ") + "}\n")
    return "\n".join(out)


def typography_css(tree: dict[str, Any]) -> str:
    out = []
    for variant, spec in tree["type"]["scale"].items():
        out.append(rule(f".t-{variant}", [
            f"font-family: var(--font-{spec['family']});",
            f"font-size: var(--type-{variant}-size);",
            f"line-height: var(--type-{variant}-lh);",
            f"letter-spacing: var(--type-{variant}-tracking);",
            f"font-weight: var(--type-{variant}-weight);",
            f"font-stretch: var(--type-{variant}-stretch);",
            f"text-wrap: {'balance' if spec['family'] == 'display' else 'pretty'};",
        ]))
    out.append(rule(".tnum", ["font-variant-numeric: tabular-nums;"]))
    return "\n".join(out)


def fonts_css(lock: dict[str, Any], metrics: dict[str, Any], base_url: str) -> str:
    base = base_url.rstrip("/")
    size_adjust = {role: entry["value"] for role, entry in metrics["sizeAdjust"].items()}
    out = []
    for face in lock["files"]:
        decls = [f'font-family: "{face["family"]}";', f"font-style: {face['style']};", f"font-weight: {face['weight']};"]
        if face["stretch"] != "normal":
            decls.append(f"font-stretch: {face['stretch']};")
        decls += ["font-display: swap;", f'src: url("{base}/{face["file"]}") format("woff2");',
                  f"unicode-range: {face['unicodeRange']};"]
        if face["role"] in size_adjust:
            decls.append(f"size-adjust: {num(size_adjust[face['role']], 2)}%;")
        out.append(rule("@font-face", decls))
    for fallback in metrics["fallbacks"].values():
        out.append(rule("@font-face", [
            f'font-family: "{fallback["family"]}";',
            "src: " + ", ".join(f'local("{name}")' for name in fallback["local"]) + ";",
            f"size-adjust: {num(fallback['sizeAdjust'], 2)}%;",
            f"ascent-override: {num(fallback['ascentOverride'], 2)}%;",
            f"descent-override: {num(fallback['descentOverride'], 2)}%;",
            f"line-gap-override: {num(fallback['lineGapOverride'], 2)}%;",
        ]))
    return "\n".join(out)
