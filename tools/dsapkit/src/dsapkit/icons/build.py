"""Validate packages/icons/svg against icons.json and build the sprite, CSS, TypeScript and standalone SVGs."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from ..errors import BuildError
from ..jsonio import GENERATED, read_json, reset_dir, write_text
from ..paths import Paths
from ..tokens import load_tokens
from .geometry import element_points

SVG_NS = "http://www.w3.org/2000/svg"
ACCENT, SOLID = "ac", "fl"


@dataclass(frozen=True)
class Icon:
    name: str
    meaning: str
    elements: tuple[ET.Element, ...]


def _validate(name: str, root: ET.Element, cfg: dict) -> tuple[ET.Element, ...]:
    rules = cfg["rules"]
    if root.tag != f"{{{SVG_NS}}}svg":
        raise BuildError(f"{name}: root must be <svg> in the SVG namespace")
    if root.get("viewBox") != rules["viewBox"]:
        raise BuildError(f"{name}: viewBox must be {rules['viewBox']}")
    if set(root.attrib) - {"viewBox"}:
        raise BuildError(f"{name}: the root may only carry viewBox; stroke and colour come from tokens")
    elements = tuple(root)
    if not elements:
        raise BuildError(f"{name}: empty icon")
    low, high = rules["bounds"]
    accents = 0
    for el in elements:
        tag = el.tag.split("}")[-1]
        if tag not in rules["elements"]:
            raise BuildError(f"{name}: <{tag}> is not allowed")
        extra = set(el.attrib) - set(rules["attributes"])
        if extra:
            raise BuildError(f"{name}: attributes {sorted(extra)} are not allowed on <{tag}>")
        cls = el.get("class", "")
        if cls and cls not in rules["classes"]:
            raise BuildError(f"{name}: class {cls!r} is not allowed")
        accents += cls == ACCENT
        if el.get("transform", "rotate(").split("(")[0] != "rotate":
            raise BuildError(f"{name}: only rotate() transforms are allowed")
        for px, py in element_points(el):
            if not (low - 0.5 <= px <= high + 0.5 and low - 0.5 <= py <= high + 0.5):
                raise BuildError(f"{name}: point ({px:g}, {py:g}) is outside the {low} to {high} grid")
    needs_accent = name not in cfg["noAccent"]
    if needs_accent and not accents:
        raise BuildError(f'{name}: needs one accent stroke (class="{ACCENT}")')
    if not needs_accent and accents:
        raise BuildError(f"{name}: listed in noAccent but has an accent")
    return elements


def load_icons(paths: Paths) -> list[Icon]:
    cfg = read_json(paths.icons / "icons.json")
    files = {f.stem: f for f in sorted((paths.icons / "svg").glob("*.svg"))}
    described = set(cfg["icons"])
    problems = []
    if set(files) - described:
        problems.append(f"not described in icons.json: {sorted(set(files) - described)}")
    if described - set(files):
        problems.append(f"described in icons.json but no svg file: {sorted(described - set(files))}")
    icons = []
    for name, meaning in cfg["icons"].items():
        if name not in files:
            continue
        try:
            icons.append(Icon(name, meaning, _validate(name, ET.parse(files[name]).getroot(), cfg)))
        except (BuildError, ET.ParseError) as err:
            problems.append(str(err))
    if problems:
        raise BuildError("icon check failed:\n  " + "\n  ".join(problems))
    return icons


def _element(el: ET.Element, colours: dict[str, str] | None = None) -> str:
    attrs = dict(el.attrib)
    cls = attrs.get("class", "")
    if cls == SOLID:
        attrs["fill"] = colours["main"] if colours else "currentColor"
    if colours and cls == ACCENT:
        attrs["stroke"] = colours["accent"]
    return f"<{el.tag.split('}')[-1]} " + " ".join(f'{k}="{v}"' for k, v in attrs.items()) + "/>"


def symbol_attributes(stroke_width: float, stroke: str = "currentColor") -> str:
    return (f'viewBox="0 0 24 24" fill="none" stroke="{stroke}" stroke-width="{stroke_width:g}" '
            'stroke-linecap="round" stroke-linejoin="round"')


def build_icons(paths: Paths) -> list[Icon]:
    tokens = load_tokens(paths.tokens_json)
    stroke = tokens.tree["icon"]["stroke"]
    icons = load_icons(paths)
    out = reset_dir(paths.icons_dist)
    header = GENERATED.format(source="packages/icons")

    symbols = "".join(f'<symbol id="i-{i.name}" {symbol_attributes(stroke)}>' + "".join(_element(e) for e in i.elements)
                      + "</symbol>" for i in icons)
    # The sprite is embedded in each page. It is hidden by a class in icons.css, not a style attribute,
    # so pages can run under a Content Security Policy that blocks inline styles (docs/adr/0007-web-app.md).
    write_text(out / "sprite.svg", f"<!-- {header} -->\n"
               f'<svg xmlns="{SVG_NS}" class="icon-sprite" aria-hidden="true" focusable="false">'
               f"<defs>{symbols}</defs></svg>\n")

    sizes = "".join(f".icon--{name} {{ width: var(--icon-{name}); height: var(--icon-{name}); }}\n"
                    for name in tokens.tree["icon"]["size"])
    write_text(out / "icons.css", f"/* {header} */\n"
               "/* Icons take the text colour; the accent stroke takes --icon-accent from the surface. */\n"
               ".icon-sprite { position: absolute; width: 0; height: 0; overflow: hidden; }\n"
               ".icon { width: var(--icon-lg); height: var(--icon-lg); flex: none; stroke-width: var(--icon-stroke); vertical-align: middle; }\n"
               + sizes + f"symbol .{ACCENT} {{ stroke: var(--icon-accent, currentColor); }}\n"
               f"symbol .{SOLID} {{ fill: currentColor; }}\n")

    meanings = json.dumps({i.name: i.meaning for i in icons}, indent=2, ensure_ascii=False)
    write_text(out / "icons.ts", f"// {header}\n\n"
               f"export const iconNames = {json.dumps([i.name for i in icons], indent=2)} as const;\n\n"
               "export type IconName = (typeof iconNames)[number];\n\n"
               f"export const iconMeanings: Record<IconName, string> = {meanings};\n")

    for surface, folder in (("chalk", "svg"), ("ink", "svg-ink")):
        roles = tokens.tree["surface"][surface]
        colours = {"main": roles["text"], "accent": roles["icon-accent"]}
        for icon in icons:
            body = "".join(_element(e, colours) for e in icon.elements)
            write_text(out / folder / f"{icon.name}.svg",
                       f'<svg xmlns="{SVG_NS}" width="24" height="24" {symbol_attributes(stroke, colours["main"])}>{body}</svg>\n')
    return icons
