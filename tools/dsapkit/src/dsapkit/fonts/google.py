"""Google Fonts client: woff2 files for the site, static TTF instances for measuring and rendering."""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

from ..errors import BuildError
from ..net import https_get
from .sfnt import is_sfnt

ALLOWED_HOSTS = frozenset({"fonts.googleapis.com", "fonts.gstatic.com", "raw.githubusercontent.com"})
# Google Fonts chooses the file format from the user agent.
WOFF2_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
TTF_AGENT = "dsapkit/0.1 (static font instances)"
# CSS font-stretch keywords and their percentages.
STRETCH_KEYWORDS = {50.0: "ultra-condensed", 62.5: "extra-condensed", 75.0: "condensed", 87.5: "semi-condensed",
                    100.0: "normal", 112.5: "semi-expanded", 125.0: "expanded", 150.0: "extra-expanded",
                    200.0: "ultra-expanded"}

_FACE_RE = re.compile(r"(?:/\*\s*([\w-]+)\s*\*/\s*)?@font-face\s*\{([^}]*)\}", re.S)
_DESC_RE = re.compile(r"([\w-]+)\s*:\s*([^;]+);")
_URL_RE = re.compile(r"url\((https://[^)]+)\)")


@dataclass(frozen=True)
class FaceDeclaration:
    subset: str
    url: str
    style: str
    weight: str
    stretch: str
    unicode_range: str


def parse_css(css: str) -> list[FaceDeclaration]:
    faces = []
    for subset, body in _FACE_RE.findall(css):
        desc = {k.strip(): v.strip() for k, v in _DESC_RE.findall(body)}
        match = _URL_RE.search(desc.get("src", ""))
        if match:
            faces.append(FaceDeclaration(subset or "", match.group(1), desc.get("font-style", "normal"),
                                         desc.get("font-weight", "400"), desc.get("font-stretch", "normal"),
                                         desc.get("unicode-range", "")))
    return faces


def stretch_matches(declared: str, stretch: float) -> bool:
    keyword = STRETCH_KEYWORDS.get(stretch)
    return declared == keyword or declared == f"{stretch:g}%"


class GoogleFonts:
    def __init__(self, css_api: str) -> None:
        self.css_api = css_api

    def _css(self, query: str, agent: str) -> str:
        url = f"{self.css_api}?family={urllib.parse.quote(query, safe=':,@;.')}&display=swap"
        return https_get(url, allow=ALLOWED_HOSTS, user_agent=agent).decode("utf-8")

    def web_faces(self, query: str) -> list[FaceDeclaration]:
        return parse_css(self._css(query, WOFF2_AGENT))

    def woff2(self, url: str) -> bytes:
        data = https_get(url, allow=ALLOWED_HOSTS, user_agent=WOFF2_AGENT)
        if data[:4] != b"wOF2":
            raise BuildError(f"{url} is not a woff2 file")
        return data

    def instance(self, family: str, weight: int, stretch: float = 100.0) -> bytes:
        """A static TTF of one weight and width."""
        query = f"{family}:wght@{weight}" if stretch == 100 else f"{family}:wdth,wght@{stretch:g},{weight}"
        faces = [f for f in parse_css(self._css(query, TTF_AGENT)) if stretch_matches(f.stretch, stretch)]
        if not faces:
            raise BuildError(f"Google Fonts has no {family} at weight {weight}, width {stretch:g}%")
        data = https_get(faces[0].url, allow=ALLOWED_HOSTS, user_agent=TTF_AGENT)
        if not is_sfnt(data):
            raise BuildError(f"{faces[0].url} is not a TrueType/OpenType file")
        return data

    def text(self, url: str) -> bytes:
        return https_get(url, allow=ALLOWED_HOSTS, user_agent=TTF_AGENT)
