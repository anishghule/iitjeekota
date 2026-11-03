"""Render fonts: plain TTF instances of every role and weight, for rasterising and measuring text.

HarfBuzz (inside librsvg) cannot read woff2, so PNG rendering uses static TTFs
cached in packages/tokens/.cache/render-fonts (never shipped). Which instances
exist follows the tokens: every role at every weight in font.weight, at the
role's width from font.stretch.

Rendering always goes through an isolated fontconfig that sees only these files.
Each file is given the family "dsap-{role}" at scan time, so an SVG asks for a
role and a weight and gets exactly the brand font, on any machine.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from xml.sax.saxutils import escape

from ..errors import BuildError
from ..jsonio import read_json, write_bytes, write_json
from ..paths import Paths
from ..tokens import TokenSet
from .config import FontsConfig, role_stretch
from .google import GoogleFonts
from .sfnt import Face

FAMILY_PREFIX = "dsap-"
INDEX_SCHEMA = 1  # bump when RenderFace changes; older caches are then rebuilt


@dataclass(frozen=True)
class RenderFace:
    role: str
    weight: int
    stretch: float
    file: str
    sha256: str

    @property
    def key(self) -> tuple[str, int, float]:
        return self.role, self.weight, self.stretch


class RenderFonts:
    def __init__(self, paths: Paths, cfg: FontsConfig, tokens: TokenSet, client: GoogleFonts) -> None:
        self._dir = paths.render_fonts
        self._index = self._dir / "index.json"
        self._cfg = cfg
        self._tokens = tokens
        self._client = client

    @staticmethod
    def family(role: str) -> str:
        return FAMILY_PREFIX + role

    def required(self) -> list[tuple[str, int, float]]:
        weights = sorted({int(w) for w in self._tokens.tree["font"]["weight"].values()})
        return [(fam.role, w, role_stretch(self._tokens, fam.role)) for fam in self._cfg.families for w in weights]

    def _cached(self) -> dict[tuple[str, int, float], RenderFace]:
        """Faces already on disk whose hash still matches. An index from another schema counts as empty."""
        if not self._index.exists():
            return {}
        index = read_json(self._index)
        if not isinstance(index, dict) or index.get("schema") != INDEX_SCHEMA:
            return {}
        faces = [RenderFace(**entry) for entry in index["faces"]]
        valid = {}
        for face in faces:
            path = self._dir / face.file
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == face.sha256:
                valid[face.key] = face
        return valid

    def ensure(self) -> list[RenderFace]:
        """Download whatever the tokens need and the cache lacks; return the full set."""
        cached = self._cached()
        faces = []
        for role, weight, stretch in self.required():
            face = cached.get((role, weight, stretch))
            if face is None:
                data = self._client.instance(self._cfg.family(role).family, weight, stretch)
                name = f"{role}-{weight}-{stretch:g}.ttf"
                write_bytes(self._dir / name, data)
                face = RenderFace(role, weight, stretch, name, hashlib.sha256(data).hexdigest())
            faces.append(face)
        write_json(self._index, {"schema": INDEX_SCHEMA, "faces": [face.__dict__ for face in faces]})
        return faces

    @cached_property
    def faces(self) -> dict[tuple[str, int], Face]:
        """Every render face, loaded once, keyed by (role, weight)."""
        return {(f.role, f.weight): Face.from_path(self._dir / f.file) for f in self._entries}

    def face(self, role: str, weight: int) -> Face:
        try:
            return self.faces[(role, weight)]
        except KeyError:
            raise BuildError(f"no render font for role {role!r} at weight {weight}; weights come from font.weight") from None

    def measure(self, text: str, role: str, weight: int, size: float, tracking_em: float = 0.0) -> float:
        """Width in px of `text` set at `size` px (an upper bound: no kerning or ligatures)."""
        face = self.face(role, weight)
        return face.advance(text) / face.units_per_em * size + tracking_em * size * max(len(text) - 1, 0)

    @cached_property
    def _entries(self) -> list[RenderFace]:
        return self.ensure()

    def fontconfig(self, folder: Path) -> Path:
        """Write an isolated fontconfig file into `folder` and return its path."""
        rules = "".join(
            f'<match target="scan"><test name="file"><string>{escape(str(self._dir / f.file))}</string></test>'
            f'<edit name="family" mode="assign" binding="same"><string>{escape(self.family(f.role))}</string></edit></match>'
            for f in self._entries)
        conf = folder / "fonts.conf"
        conf.write_text(
            '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
            f"<fontconfig><dir>{escape(str(self._dir))}</dir><cachedir>{escape(str(folder / 'cache'))}</cachedir>"
            f"{rules}</fontconfig>\n", encoding="utf-8")
        return conf

    @staticmethod
    def empty_fontconfig(folder: Path) -> Path:
        """A fontconfig with no fonts: shapes-only renders, where any stray text shows up as missing glyphs."""
        conf = folder / "fonts.conf"
        conf.write_text(
            '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
            f"<fontconfig><cachedir>{escape(str(folder / 'cache'))}</cachedir></fontconfig>\n", encoding="utf-8")
        return conf
