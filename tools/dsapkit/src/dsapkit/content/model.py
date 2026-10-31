"""Templates, pages and shared blocks from packages/content (docs/adr/0005-content-format.md)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import BuildError
from ..jsonio import read_json
from ..media.library import load_library
from ..paths import Paths
from .syllabus import Syllabus, load_syllabus

KINDS = {"prose", "faq", "list"}
STATUSES = {"draft", "ready"}


@dataclass(frozen=True)
class Paragraph:
    text: str
    requires: tuple[str, ...] = ()


@dataclass(frozen=True)
class Question:
    question: str
    answer: Paragraph


@dataclass(frozen=True)
class SectionSpec:
    id: str
    kind: str
    paragraphs: tuple[int, int] = (0, 0)
    items: tuple[int, int] = (0, 0)
    gates: tuple[str, ...] = ()
    component: str | None = None
    shared: bool = False
    optional: bool = False
    widget: str | None = None  # data for the section's interactive part, in widgets/{locale}/{name}.json


@dataclass(frozen=True)
class Layout:
    intro: tuple[int, int] = (1, 2)
    sections: tuple[SectionSpec, ...] = ()
    free: dict[str, Any] | None = None  # {"min", "max", "kinds"}: page-specific sections before the fixed ones
    waits_for: str | None = None        # not written in this phase, and why
    markdown: dict[str, int] | None = None  # a Markdown post: {"minWords", "introMaxWords"}


@dataclass(frozen=True)
class Section:
    id: str
    kind: str | None              # given on free sections; fixed sections take the layout's kind
    heading: str | None
    paragraphs: tuple[Paragraph, ...]
    points: tuple[Paragraph, ...]
    questions: tuple[Question, ...]
    block: str | None = None
    action: dict[str, Any] | None = None


@dataclass(frozen=True)
class Page:
    route: str
    locale: str
    status: str
    title: str
    description: str
    h1: str
    intro: tuple[Paragraph, ...]
    sections: tuple[Section, ...]
    file: Path


@dataclass(frozen=True)
class Post:
    """A guide: JSON front matter, then Markdown. Its H1 is the title in blog.json."""
    route: str
    locale: str
    status: str
    title: str          # the meta title; the H1 is the route name
    description: str
    author: str         # a fact id naming the author
    requires: tuple[str, ...]
    body: str
    file: Path

    @property
    def blocks(self) -> list[str]:
        """Paragraphs, headings and list items, as written, in order."""
        return [b.strip() for b in self.body.split("\n\n") if b.strip()]


@dataclass
class Content:
    meta: dict[str, int]
    similarity: dict[str, Any]
    actions: frozenset[str]
    layouts: dict[str, Layout]             # by template
    route_layouts: dict[str, Layout]       # by route id, where a page differs from its template
    pages: dict[tuple[str, str], Page]     # (route id, locale) -> page
    syllabus: Syllabus
    blocks: dict[tuple[str, str], Section] = field(default_factory=dict)  # (block id, locale) -> block
    posts: dict[tuple[str, str], Post] = field(default_factory=dict)      # (route id, locale) -> post
    widgets: dict[tuple[str, str], Any] = field(default_factory=dict)     # (widget name, locale) -> raw data
    media: dict[str, str] = field(default_factory=dict)                   # media slot id -> origin, for media gates

    def layout(self, route_id: str, template: str) -> Layout | None:
        return self.route_layouts.get(route_id) or self.layouts.get(template)

    def copy(self, route_id: str, locale: str) -> Page | Post | None:
        """The page or post written for a route in one language, if any."""
        return self.pages.get((route_id, locale)) or self.posts.get((route_id, locale))


def _span(raw: Any, name: str, where: str) -> tuple[int, int]:
    if raw is None:
        return (0, 0)
    if not (isinstance(raw, list) and len(raw) == 2 and 0 <= raw[0] <= raw[1]):
        raise BuildError(f"{where}: {name} must be [min, max]")
    return raw[0], raw[1]


def _layout(raw: dict[str, Any], where: str) -> Layout:
    if "waitsFor" in raw:
        return Layout(waits_for=raw["waitsFor"])
    if "markdown" in raw:
        return Layout(markdown=raw["markdown"])
    specs = []
    for s in raw.get("sections", []):
        if s.get("kind") not in KINDS:
            raise BuildError(f"{where}: section {s.get('id')} kind must be one of {sorted(KINDS)}")
        specs.append(SectionSpec(s["id"], s["kind"], _span(s.get("paragraphs"), "paragraphs", where),
                                 _span(s.get("items"), "items", where), tuple(s.get("gates", [])),
                                 s.get("component"), bool(s.get("shared")), bool(s.get("optional")), s.get("widget")))
    return Layout(_span(raw["intro"], "intro", where), tuple(specs), raw.get("free"))


def _paragraph(raw: Any, where: str) -> Paragraph:
    if isinstance(raw, str):
        return Paragraph(raw)
    if isinstance(raw, dict) and isinstance(raw.get("text"), str):
        return Paragraph(raw["text"], tuple(raw.get("requires", [])))
    raise BuildError(f"{where}: a paragraph is a string or {{\"text\", \"requires\"}}")


def _section(raw: dict[str, Any], where: str) -> Section:
    sid = raw.get("id", "")
    here = f"{where} section {sid or '?'}"
    questions = tuple(Question(q["q"], _paragraph(q["a"], here)) for q in raw.get("questions", []))
    return Section(sid, raw.get("kind"), raw.get("heading"),
                   tuple(_paragraph(p, here) for p in raw.get("body", [])),
                   tuple(_paragraph(p, here) for p in raw.get("points", [])),
                   questions, raw.get("block"), raw.get("action"))


def _locale_files(root: Path, locales: list[str], pattern: str = "*.json") -> list[tuple[str, Path]]:
    if not root.exists():
        return []
    unknown = sorted(d.name for d in root.iterdir() if d.is_dir() and d.name not in locales)
    if unknown:
        raise BuildError(f"{root}: folders {unknown} are not site locales {locales}")
    return [(loc, f) for loc in locales if (root / loc).exists() for f in sorted((root / loc).glob(pattern))]


FRONT_MATTER = "---\n"


def _post(file: Path, locale: str, where: str) -> Post:
    """JSON between two --- lines, then Markdown. JSON is valid YAML, so Astro reads the same front matter."""
    text = file.read_text(encoding="utf-8")
    end = text.find("\n" + FRONT_MATTER, len(FRONT_MATTER))
    if not text.startswith(FRONT_MATTER) or end < 0:
        raise BuildError(f"{where}: a post starts with JSON front matter between two --- lines")
    try:
        meta = json.loads(text[len(FRONT_MATTER):end])
    except json.JSONDecodeError as err:
        raise BuildError(f"{where}: front matter is not valid JSON: {err.msg}") from err
    if meta.get("status") not in STATUSES:
        raise BuildError(f"{where}: status must be one of {sorted(STATUSES)}")
    return Post(f"post-{file.stem}", locale, meta["status"], meta.get("title", ""), meta.get("description", ""),
                meta.get("author", ""), tuple(meta.get("requires", [])), text[end + 1 + len(FRONT_MATTER):], file)


def load_content(paths: Paths, locales: list[str]) -> Content:
    raw = read_json(paths.content_templates)
    layouts = {name: _layout(t, f"templates.json {name}") for name, t in raw["templates"].items()}
    route_layouts = {rid: _layout(t, f"templates.json routes.{rid}") for rid, t in raw.get("routes", {}).items()}
    pages = {}
    for loc, file in _locale_files(paths.content / "pages", locales):
        data = read_json(file)
        where = str(file.relative_to(paths.root))
        if data.get("route") != file.stem:
            raise BuildError(f"{where}: route {data.get('route')!r} must match the file name")
        if data.get("status") not in STATUSES:
            raise BuildError(f"{where}: status must be one of {sorted(STATUSES)}")
        meta = data.get("meta", {})
        pages[(file.stem, loc)] = Page(file.stem, loc, data["status"], meta.get("title", ""), meta.get("description", ""),
                                       data.get("h1", ""), tuple(_paragraph(p, where) for p in data.get("intro", [])),
                                       tuple(_section(s, where) for s in data.get("sections", [])), file)
    blocks = {}
    for loc, file in _locale_files(paths.content / "blocks", locales):
        blocks[(file.stem, loc)] = _section({**read_json(file), "id": file.stem}, str(file.relative_to(paths.root)))
    posts = {}
    for loc, file in _locale_files(paths.content / "posts", locales, "*.md"):
        post = _post(file, loc, str(file.relative_to(paths.root)))
        posts[(post.route, loc)] = post
    widgets = {(file.stem, loc): read_json(file) for loc, file in _locale_files(paths.content / "widgets", locales)}
    media = {slot.id: slot.origin for slot in load_library(paths).slots}
    return Content(raw["meta"], raw["similarity"], frozenset(raw["actions"]), layouts, route_layouts, pages,
                   load_syllabus(paths), blocks, posts, widgets, media)
