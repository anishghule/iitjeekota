"""The official D-SAP medal, located inside its image and rendered at any size.

The medal comes from the media slot named in packages/brand/logo.json. Its
visible area is found from the alpha channel, so a re-exported or re-padded
logo needs no new numbers. Raster renditions (logo sizes, favicons, app icons)
go through the linear-light pipeline in images.raster, with the sharpening rules
from logo.json; OG images place the medal as an SVG element instead.
"""

from __future__ import annotations

import base64
from functools import cached_property
from pathlib import Path

from ..images.info import image_type
from ..images.png import Pixels, decode_png, encode_png
from ..images.raster import Image
from ..jsonio import read_json, reset_dir, write_bytes
from ..media.library import load_slots, slot_path
from ..paths import Paths
from .svg import SVG_NS, escape, num


class OfficialLogo:
    def __init__(self, data: bytes, cfg: dict, alt: str) -> None:
        self._data = data
        self._cfg = cfg
        self.alt = alt
        self.pixels: Pixels = decode_png(data)
        x, y, side = self.pixels.alpha_box(cfg["alphaThreshold"]).square()
        self.crop = (round(x), round(y), round(side))  # square around the medal, in image pixels

    @classmethod
    def load(cls, paths: Paths) -> OfficialLogo:
        cfg = read_json(paths.logo_json)
        slot = next(s for s in load_slots(paths)[0] if s.id == cfg["slot"])
        return cls(slot_path(paths, cfg["slot"]).read_bytes(), cfg, slot.alt.get("en", ""))

    @cached_property
    def image(self) -> Image:
        """The medal square in linear light, the source of every raster rendition."""
        x, y, side = self.crop
        return Image.from_pixels(self.pixels, x, y, side, side)

    def rendition(self, size: int) -> Image:
        image = self.image.resize(size)
        rule = next((r for r in self._cfg["sharpen"] if size <= r["maxSize"]), None)
        return image.sharpen(rule["radius"], rule["amount"]) if rule else image

    def png(self, size: int) -> bytes:
        return encode_png(self.rendition(size).to_pixels())

    def plate(self, size: int, background: str, scale: float) -> bytes:
        """The medal centred on an opaque square, at `scale` of its side (touch and maskable icons)."""
        return encode_png(self.image.on_background(background, size, scale).to_pixels())

    @cached_property
    def data_uri(self) -> str:
        return f"data:{image_type(self._data)};base64,{base64.b64encode(self._data).decode('ascii')}"

    def element(self, x: float, y: float, size: float) -> str:
        """The medal as an SVG element filling a `size` square at (x, y), for layouts rendered as SVG."""
        cx, cy, side = self.crop
        return (f'<svg x="{num(x)}" y="{num(y)}" width="{num(size)}" height="{num(size)}" '
                f'viewBox="{num(cx)} {num(cy)} {num(side)} {num(side)}">'
                f'<image width="{self.pixels.width}" height="{self.pixels.height}" href="{self.data_uri}"/></svg>')

    def document(self, size: int) -> str:
        return (f'<svg xmlns="{SVG_NS}" width="{size}" height="{size}" viewBox="0 0 {size} {size}" role="img">'
                f"<title>{escape(self.alt)}</title>{self.element(0, 0, size)}</svg>")


def build_logo(paths: Paths, logo: OfficialLogo) -> list[Path]:
    cfg = read_json(paths.logo_json)
    folder = reset_dir(paths.brand_dist / "logo")
    written = []
    for size in cfg["sizes"]:
        out = folder / cfg["fileName"].format(size=size)
        write_bytes(out, logo.png(size))
        written.append(out)
    return written
