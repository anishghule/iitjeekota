"""Pull the human-readable text out of each kind of file, keeping line numbers and locale.

Directives (in any comment style, or as plain text):
  copy-lint-disable / copy-lint-enable    skip the lines between them
  copy-lint-allow: best, guarantee        allow these terms on this line and the next
  copy-lint-allow-file: best              allow these terms in the whole file
  "$copyLintAllow": ["best"]              in JSON: allow these terms in that object's strings
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from ..errors import BuildError

TEXT_SUFFIXES = {".md", ".mdx", ".txt", ".html", ".json", ".yaml", ".yml"}
_ALLOW_RE = re.compile(r"copy-lint-allow:\s*([^\n>*-][^\n>]*?)\s*(?:-->|\*/|$)")
_ALLOW_FILE_RE = re.compile(r"copy-lint-allow-file:\s*([^\n>]*?)\s*(?:-->|\*/|$)")
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_URL_RE = re.compile(r"https?://\S+")
_COMMENT_RE = re.compile(r"<!--.*?-->")  # comments carry directives, never copy


@dataclass(frozen=True)
class TextLine:
    """One unit of copy: a Markdown line, an HTML block element or a JSON string."""

    path: Path
    line: int
    text: str
    locale: str
    allowed: frozenset[str]
    prose: bool = False  # running text, counted for readability


def _terms(text: str) -> set[str]:
    return {t.strip().lower() for t in text.split(",") if t.strip()}


def locale_from_path(path: Path, locales: set[str], default: str) -> str:
    for part in reversed(path.parts):
        stem_parts = part.split(".")
        for candidate in (part, *stem_parts):
            if candidate in locales:
                return candidate
    return default


@dataclass
class _Block:
    tag: str
    line: int
    lang: str
    parts: list[str]


class _HtmlText(HTMLParser):
    """Visible text of an HTML file, one entry per block element, in document order.

    Entries are (line, text, lang, prose); directive comments appear as entries with lang "directive".
    """

    SKIP = {"script", "style", "svg", "code", "pre", "template"}
    BLOCKS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "figcaption", "caption", "summary",
              "dt", "dd", "blockquote", "label", "button", "title"}
    PROSE = {"p", "li", "dd", "blockquote"}
    VOID = {"br", "img", "meta", "link", "input", "hr", "source", "wbr", "area", "col", "embed", "track"}

    def __init__(self, default_locale: str) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[tuple[int, str, str, bool]] = []
        self._skip = 0
        self._langs = [default_locale]
        self._open: list[str] = []
        self._blocks: list[_Block] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.VOID:
            return
        lang = (dict(attrs).get("lang") or self._langs[-1]).split("-")[0]
        self._open.append(tag)
        self._langs.append(lang)
        if tag in self.SKIP:
            self._skip += 1
        if tag in self.BLOCKS:
            self._blocks.append(_Block(tag, self.getpos()[0], lang, []))

    def handle_endtag(self, tag: str) -> None:
        while self._open:
            closed = self._open.pop()
            self._langs.pop()
            if closed in self.SKIP:
                self._skip -= 1
            if closed in self.BLOCKS and self._blocks:
                self._emit(self._blocks.pop())
            if closed == tag:
                break

    def _emit(self, block: _Block) -> None:
        text = " ".join(" ".join(block.parts).split())
        if text:
            self.entries.append((block.line, text, block.lang, block.tag in self.PROSE))

    def handle_data(self, data: str) -> None:
        if self._skip or not data.strip():
            return
        if self._blocks:
            self._blocks[-1].parts.append(data)
        else:  # text outside any block element stands alone
            self._emit(_Block("", self.getpos()[0], self._langs[-1], [data]))

    def handle_comment(self, data: str) -> None:
        self.entries.append((self.getpos()[0], f"<!--{data}-->", "directive", False))


def _json_strings(value: object, locale: str, locales: set[str], path: str = "",
                  allowed: frozenset[str] = frozenset()) -> Iterator[tuple[str, str, str, frozenset[str]]]:
    """(key path, text, locale, allowed terms) for every prose string. An object's "$copyLintAllow" list covers its strings."""
    if isinstance(value, dict):
        allowed = allowed | {t.lower() for t in value.get("$copyLintAllow", [])}
        for key, child in value.items():
            if key == "$copyLintAllow":
                continue
            yield from _json_strings(child, key if key in locales else locale, locales,
                                     f"{path}.{key}" if path else key, allowed)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from _json_strings(child, locale, locales, f"{path}[{i}]", allowed)
    elif isinstance(value, str) and not value.startswith(("http://", "https://", "#")) and " " in value:
        yield path, value, locale, allowed


def read_lines(path: Path, locales: set[str], default_locale: str) -> list[TextLine]:
    """Text lines of one file, with directives applied."""
    text = path.read_text(encoding="utf-8")
    file_allowed = frozenset(t for m in _ALLOW_FILE_RE.finditer(text) for t in _terms(m.group(1)))
    locale = locale_from_path(path, locales, default_locale)

    raw: list[tuple[int, str, str, bool]] = []
    if path.suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as err:
            raise BuildError(f"{path}: invalid JSON: {err.msg}") from err
        # JSON has no line structure worth keeping; the key path stands in for a line number.
        return [TextLine(path, 0, f"{key}: {value}", loc, file_allowed | allowed)
                for key, value, loc, allowed in _json_strings(data, locale, locales)]
    if path.suffix == ".html":
        parser = _HtmlText(locale)
        parser.feed(text)
        parser.close()
        raw = parser.entries
    else:
        in_fence = False
        for number, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
                continue
            if not in_fence:
                stripped = line.lstrip()
                prose = bool(stripped) and not stripped.startswith(("#", "|", "-", "*", ">", "<"))
                raw.append((number, line, locale, prose))

    out: list[TextLine] = []
    disabled = False
    carried: frozenset[str] = frozenset()
    for number, line, lang, prose in raw:
        if "copy-lint-disable" in line:
            disabled = True
            continue
        if "copy-lint-enable" in line:
            disabled = False
            continue
        allow = frozenset(t for m in _ALLOW_RE.finditer(line) for t in _terms(m.group(1)))
        if lang == "directive":
            carried = allow
            continue
        if disabled:
            continue
        visible = _URL_RE.sub(" ", _INLINE_CODE_RE.sub(" ", _COMMENT_RE.sub(" ", line)))
        out.append(TextLine(path, number, visible, lang, file_allowed | allow | carried, prose))
        carried = allow
    return out


def collect_files(targets: list[Path], exclude: set[Path]) -> list[Path]:
    """Text files under the targets, skipping excluded files and everything inside excluded folders."""
    def excluded(path: Path) -> bool:
        resolved = path.resolve()
        return any(resolved == e or resolved.is_relative_to(e) for e in exclude)

    files: list[Path] = []
    for target in targets:
        candidates = [target] if target.is_file() else sorted(p for p in target.rglob("*") if p.is_file())
        for path in candidates:
            if path.suffix in TEXT_SUFFIXES and not excluded(path) and "node_modules" not in path.parts:
                files.append(path)
    return files
