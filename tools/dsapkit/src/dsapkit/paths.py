"""Every input and output location, defined once."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import BuildError


@dataclass(frozen=True)
class Paths:
    root: Path

    @classmethod
    def discover(cls, start: Path | None = None) -> Paths:
        """The repository root is the nearest folder above `start` that holds CLAUDE.md."""
        here = (start or Path(__file__)).resolve()
        for folder in (here, *here.parents):
            if (folder / "CLAUDE.md").is_file() and (folder / "packages").is_dir():
                return cls(folder)
        raise BuildError(f"could not find the repository root above {here}")

    # packages/tokens
    @property
    def tokens(self) -> Path:
        return self.root / "packages" / "tokens"

    @property
    def tokens_json(self) -> Path:
        return self.tokens / "tokens.json"

    @property
    def contrast_json(self) -> Path:
        return self.tokens / "contrast.json"

    @property
    def fonts_config(self) -> Path:
        return self.tokens / "fonts.config.json"

    @property
    def fonts_lock(self) -> Path:
        return self.tokens / "fonts.lock.json"

    @property
    def fonts_metrics(self) -> Path:
        return self.tokens / "fonts.metrics.json"

    @property
    def fonts_dir(self) -> Path:
        return self.tokens / "fonts"

    @property
    def render_fonts(self) -> Path:
        return self.tokens / ".cache" / "render-fonts"

    @property
    def tokens_dist(self) -> Path:
        return self.tokens / "dist"

    @property
    def tokens_resolved(self) -> Path:
        return self.tokens_dist / "tokens.resolved.json"

    # packages/icons
    @property
    def icons(self) -> Path:
        return self.root / "packages" / "icons"

    @property
    def icons_dist(self) -> Path:
        return self.icons / "dist"

    # packages/brand
    @property
    def brand(self) -> Path:
        return self.root / "packages" / "brand"

    @property
    def brand_dist(self) -> Path:
        return self.brand / "dist"

    @property
    def identity_json(self) -> Path:
        return self.brand / "identity.json"

    @property
    def logo_json(self) -> Path:
        return self.brand / "logo.json"

    @property
    def favicons_json(self) -> Path:
        return self.brand / "favicons.json"

    @property
    def og_layout(self) -> Path:
        return self.brand / "og" / "layout.json"

    @property
    def og_copy(self) -> Path:
        return self.brand / "og" / "copy.json"

    @property
    def voice_json(self) -> Path:
        return self.brand / "voice.json"

    # packages/media
    @property
    def media(self) -> Path:
        return self.root / "packages" / "media"

    @property
    def media_manifest(self) -> Path:
        return self.media / "manifest.json"

    @property
    def media_encode(self) -> Path:
        return self.media / "encode.json"

    @property
    def media_assets(self) -> Path:
        return (self.media / "assets").resolve()

    @property
    def media_lock(self) -> Path:
        return self.media / "media.lock.json"

    # packages/site
    @property
    def site(self) -> Path:
        return self.root / "packages" / "site"

    @property
    def site_dist(self) -> Path:
        return self.site / "dist"

    @property
    def map(self) -> Path:
        return self.root / "packages" / "map"

    @property
    def map_config(self) -> Path:
        return self.map / "map.json"

    @property
    def map_source(self) -> Path:
        return self.map / "source"

    @property
    def map_lock(self) -> Path:
        return self.map / "map.lock.json"

    @property
    def map_dist(self) -> Path:
        return self.map / "dist"

    @property
    def content(self) -> Path:
        return self.root / "packages" / "content"

    @property
    def content_templates(self) -> Path:
        return self.content / "templates.json"

    @property
    def content_syllabus(self) -> Path:
        return self.content / "syllabus.json"

    @property
    def content_widgets(self) -> Path:
        return self.content / "widgets"

    @property
    def web(self) -> Path:
        return self.root / "apps" / "web"

    @property
    def web_src(self) -> Path:
        return self.web / "src"

    @property
    def web_site_config(self) -> Path:
        """Site settings that are not copy or data (indexing before launch)."""
        return self.web_src / "config" / "site.json"

    @property
    def web_generated(self) -> Path:
        """Everything make web-data writes for the site (docs/adr/0007-web-app.md)."""
        return self.web_src / "generated"

    # docs
    @property
    def content_docs(self) -> Path:
        return self.root / "docs" / "content"

    @property
    def guide(self) -> Path:
        return self.root / "docs" / "brand" / "guide"

    @property
    def seo_docs(self) -> Path:
        return self.root / "docs" / "seo"
