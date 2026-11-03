"""Shared, lazily built objects for one dsapkit run."""

from __future__ import annotations

from functools import cached_property

from .brand.logo import OfficialLogo
from .brand.raster import Rasteriser
from .fonts.config import FontsConfig, load_fonts_config
from .fonts.google import GoogleFonts
from .fonts.render import RenderFonts
from .paths import Paths
from .tokens import TokenSet, load_tokens


class Context:
    def __init__(self, paths: Paths) -> None:
        self.paths = paths

    @cached_property
    def tokens(self) -> TokenSet:
        return load_tokens(self.paths.tokens_json)

    @cached_property
    def fonts_config(self) -> FontsConfig:
        return load_fonts_config(self.paths.fonts_config, self.tokens)

    @cached_property
    def google_fonts(self) -> GoogleFonts:
        return GoogleFonts(self.fonts_config.css_api)

    @cached_property
    def render_fonts(self) -> RenderFonts:
        return RenderFonts(self.paths, self.fonts_config, self.tokens, self.google_fonts)

    @cached_property
    def logo(self) -> OfficialLogo:
        """The official medal, decoded and located once per run."""
        return OfficialLogo.load(self.paths)

    @cached_property
    def text_raster(self) -> Rasteriser:
        """For images with text, rendered in the brand fonts."""
        return Rasteriser(self.render_fonts)
