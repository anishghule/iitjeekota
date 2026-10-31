"""Open Graph images laid out from og/layout.json.

Text follows the same rules as the site CSS: a block names a type variant; Latin
locales use that variant's family, line height, tracking and weight; Devanagari
locales use the Devanagari role with its size-adjust, line heights and weights
from tokens.json. Lines are measured with the render fonts and placed in CSS
line boxes (half-leading above and below the font's ascent and descent).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import BuildError
from ..fonts.config import DEVANAGARI_ROLE
from ..fonts.render import RenderFonts
from ..jsonio import read_json, reset_dir
from ..paths import Paths
from ..tokens import TokenSet
from .logo import OfficialLogo
from .raster import Rasteriser
from .svg import SVG_NS, escape, num


@dataclass(frozen=True)
class TextStyle:
    role: str
    weight: int
    size: float          # nominal size; line boxes are measured from this
    glyph_size: float    # size the glyphs are drawn at (nominal x size-adjust)
    line_height: float
    tracking_em: float
    colour: str


def _greedy(words: list[str], measure: Callable[[str], float], width: float) -> list[str]:
    lines: list[str] = []
    for word in words:
        candidate = f"{lines[-1]} {word}" if lines else word
        if lines and measure(candidate) <= width:
            lines[-1] = candidate
        else:
            lines.append(word)
    return lines


def wrap_text(text: str, measure: Callable[[str], float], width: float, balance: bool) -> list[str]:
    """Greedy word wrap. With `balance`, the narrowest width that keeps the same number of lines (CSS text-wrap: balance)."""
    words = text.split()
    lines = _greedy(words, measure, width)
    if not balance or len(lines) < 2:
        return lines
    low, high = 0.0, width
    while high - low > 1:
        mid = (low + high) / 2
        if len(_greedy(words, measure, mid)) <= len(lines):
            high = mid
        else:
            low = mid
    return _greedy(words, measure, high)


@dataclass(frozen=True)
class SetBlock:
    style: TextStyle
    lines: list[str]

    @property
    def height(self) -> float:
        return len(self.lines) * self.style.size * self.style.line_height


class OgRenderer:
    def __init__(self, paths: Paths, tokens: TokenSet, fonts: RenderFonts, logo: OfficialLogo, raster: Rasteriser) -> None:
        self._tokens = tokens
        self._fonts = fonts
        self._logo = logo
        self._raster = raster
        self._layout = read_json(paths.og_layout)
        self._identity = read_json(paths.identity_json)
        self._metrics = read_json(paths.fonts_metrics, "run make metrics")
        self._out = paths.brand_dist / "og"

    # ------------------------------------------------------------ type

    def _style(self, block: dict[str, Any], locale: str) -> TextStyle:
        tree = self._tokens.tree
        variant = tree["type"]["scale"].get(block["variant"])
        if variant is None:
            raise BuildError(f"og/layout.json: unknown type variant {block['variant']!r}")
        devanagari = locale in tree["type"]["devanagari"]["locales"]
        role = DEVANAGARI_ROLE if devanagari else variant["family"]
        if devanagari:
            line_height = tree["type"]["devanagari"]["lineHeight"][block["variant"]]
            weight, tracking = tree["type"]["devanagari"]["weight"][block["variant"]], 0.0
        else:
            line_height, weight, tracking = variant["lineHeight"], variant["weight"], variant["tracking"]
        if "weight" in block:
            weight = tree["font"]["weight"][block["weight"]]
        adjust = self._metrics["sizeAdjust"].get(role, {}).get("value", 100) / 100
        surface = tree["surface"][self._layout["surface"]]
        return TextStyle(role, int(weight), block["size"], block["size"] * adjust, line_height, tracking,
                         surface[block["colour"]])

    def _wrap(self, text: str, style: TextStyle, width: float, max_lines: int, balance: bool, name: str) -> list[str]:
        def measure(line: str) -> float:
            return self._fonts.measure(line, style.role, style.weight, style.glyph_size, style.tracking_em)

        lines = wrap_text(text, measure, width, balance)
        if len(lines) > max_lines:
            raise BuildError(f"OG {name} needs {len(lines)} lines, layout allows {max_lines}: {text!r}")
        return lines

    def _baseline_offset(self, style: TextStyle) -> float:
        """Distance from the top of a line box to the baseline, as in CSS."""
        face = self._fonts.face(style.role, style.weight)
        ascent = face.ascender / face.units_per_em * style.glyph_size
        descent = abs(face.descender) / face.units_per_em * style.glyph_size
        return (style.size * style.line_height - (ascent + descent)) / 2 + ascent

    def _text(self, block: SetBlock, x: float, top: float, locale: str) -> str:
        s = block.style
        step = s.size * s.line_height
        first = top + self._baseline_offset(s)
        spans = "".join(f'<tspan x="{num(x)}" y="{num(first + i * step)}">{escape(line)}</tspan>'
                        for i, line in enumerate(block.lines))
        spacing = f' letter-spacing="{num(s.tracking_em * s.glyph_size)}"' if s.tracking_em else ""
        return (f'<text lang="{locale}" font-family="{RenderFonts.family(s.role)}" font-weight="{s.weight}" '
                f'font-size="{num(s.glyph_size)}" fill="{s.colour}"{spacing}>{spans}</text>')

    # ------------------------------------------------------------ layout

    def svg(self, locale: str, values: dict[str, str]) -> str:
        layout, tree = self._layout, self._tokens.tree
        surface = tree["surface"][layout["surface"]]
        column = layout["column"]
        blocks: dict[str, SetBlock] = {}
        for name, cfg in layout["blocks"].items():
            text = values.get(cfg["source"], "")
            if not text:
                continue
            style = self._style(cfg, locale)
            balance = tree["type"]["scale"][cfg["variant"]]["family"] == "display"  # mirrors typography.css
            blocks[name] = SetBlock(style, self._wrap(text, style, column["width"], cfg["maxLines"], balance, name))

        def stack(names: list[str]) -> list[SetBlock]:
            return [blocks[n] for n in names if n in blocks]

        regions = layout["regions"]
        parts: list[str] = []
        y = regions["top"]["y"]
        for block in stack(regions["top"]["blocks"]):
            parts.append(self._text(block, column["x"], y, locale))
            y += block.height
        top_end = y
        bottom = stack(regions["bottom"]["blocks"])
        bottom_start = regions["bottom"]["y"] - sum(b.height for b in bottom)
        y = bottom_start
        for block in bottom:
            parts.append(self._text(block, column["x"], y, locale))
            y += block.height
        middle = stack(regions["middle"]["blocks"])
        gap = regions["middle"]["gap"]
        total = sum(b.height for b in middle) + gap * max(len(middle) - 1, 0)
        if total > bottom_start - top_end:
            raise BuildError(f"OG text for {locale} does not fit between the top and bottom regions")
        y = top_end + (bottom_start - top_end - total) / 2
        for block in middle:
            parts.append(self._text(block, column["x"], y, locale))
            y += block.height + gap

        canvas, texture, glow, logo = layout["canvas"], layout["texture"], layout["glow"], layout["logo"]
        w, h = canvas["width"], canvas["height"]
        return (
            f'<svg xmlns="{SVG_NS}" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<defs><radialGradient id="og-glow" cx="{glow["x"]}" cy="{glow["y"]}" r="{glow["radius"]}" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{surface[glow["colour"]]}" stop-opacity="{glow["opacity"]}"/>'
            f'<stop offset="1" stop-color="{surface[glow["colour"]]}" stop-opacity="0"/></radialGradient>'
            f'<filter id="og-texture" x="0" y="0" width="100%" height="100%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="{texture["frequency"]}" numOctaves="{texture["octaves"]}" seed="{texture["seed"]}"/>'
            f'<feColorMatrix type="saturate" values="0"/>'
            f'<feComponentTransfer><feFuncA type="table" tableValues="0 {texture["opacity"]}"/></feComponentTransfer>'
            f'<feComposite in2="SourceGraphic" operator="in"/></filter></defs>'
            f'<rect width="{w}" height="{h}" fill="{surface["bg"]}"/>'
            f'<rect width="{w}" height="{h}" fill="{surface[texture["colour"]]}" filter="url(#og-texture)"/>'
            f'<rect width="{w}" height="{h}" fill="url(#og-glow)"/>'
            + self._logo.element(logo["x"], logo["y"], logo["size"])
            + "".join(parts) + "</svg>"
        )

    def render(self, locale: str, title: str, subtitle: str, out: Path) -> None:
        values = {"brand": self._identity["localNames"][locale], "domain": self._identity["domain"],
                  "title": title, "subtitle": subtitle}
        canvas = self._layout["canvas"]
        self._raster.png(self.svg(locale, values), out, canvas["width"], canvas["height"])

    def render_defaults(self, copy_path: Path) -> list[Path]:
        reset_dir(self._out)
        written = []
        for locale, copy in read_json(copy_path)["locales"].items():
            out = self._out / f"og-default-{locale}.png"
            self.render(locale, copy["title"], copy.get("subtitle", ""), out)
            written.append(out)
        return written
