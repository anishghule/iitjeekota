"""make web-lint: the contract's hard rules (CLAUDE.md section 2), checked on apps/web.

Source (apps/web/src, not the generated folder): no raw colours, font families, font sizes,
durations or easings, no palette primitives, no URL strings and no image paths. Values come from
tokens, data and the route and media registries.
Output (apps/web/dist): no executable inline script and no inline style, so the Content Security
Policy can stay strict (docs/adr/0007-web-app.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SOURCE_SUFFIXES = {".astro", ".ts", ".css"}

SOURCE_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("a raw colour; use a surface role", re.compile(r"(?<![\w&/{$-])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")),
    ("a colour function; use a surface role", re.compile(r"\b(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb)\(")),
    ("a font family; use var(--font-*)", re.compile(r"font-family\s*:(?!\s*(?:var\(|inherit))")),
    ("a raw font size; use a type token", re.compile(r"font-size\s*:\s*[\d.]+(?:px|rem|em|pt)\b")),
    ("a raw duration; use var(--dur-*)", re.compile(r"(?:transition|animation)[\w-]*\s*:[^;{}]*?(?<![\w-])\d*\.?\d+m?s\b")),
    ("a raw easing; use var(--ease-*)",
     re.compile(r"cubic-bezier\(|(?:transition|animation)[\w-]*\s*:[^;{}]*(?<![\w-])(?:ease|ease-in|ease-out|ease-in-out|linear)(?![\w-])")),
    ("a palette primitive; use a surface role", re.compile(r"--color-[a-z]+-\d+")),
    ("a URL; use the route registry or site data", re.compile(r"https?://")),
    ("an image or media path; use a media slot", re.compile(r"[\"'`/][\w./-]*\.(?:png|jpe?g|webp|avif|gif|mp4|ico)[\"'`?]")),
]

COMMENT_RE = re.compile(r"/\*.*?\*/|<!--.*?-->|(?<![:\"'])//[^\n]*", re.S)
SCRIPT_RE = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.S | re.I)
DATA_SCRIPT_RE = re.compile(r"\btype\s*=\s*[\"']application/(?:ld\+)?json[\"']", re.I)


@dataclass(frozen=True)
class Problem:
    file: Path
    line: int
    message: str

    def format(self, root: Path) -> str:
        return f"{self.file.relative_to(root)}:{self.line}: {self.message}"


def _blank_comments(text: str) -> str:
    """Comments may explain values; blank them, keeping line numbers."""
    return COMMENT_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def lint_source(src: Path, generated: Path) -> list[Problem]:
    problems = []
    for file in sorted(p for p in src.rglob("*") if p.suffix in SOURCE_SUFFIXES and p.is_file()):
        if file.is_relative_to(generated):
            continue
        text = _blank_comments(file.read_text(encoding="utf-8"))
        for message, pattern in SOURCE_RULES:
            for match in pattern.finditer(text):
                problems.append(Problem(file, text.count("\n", 0, match.start()) + 1, f"{message}: {match.group(0).strip()!r}"))
    return problems


def check_output(dist: Path) -> list[Problem]:
    problems = []
    for file in sorted(dist.rglob("*.html")):
        html = file.read_text(encoding="utf-8")
        line = lambda pos: html.count("\n", 0, pos) + 1  # noqa: E731
        for m in SCRIPT_RE.finditer(html):
            attrs = m.group(1)
            if "src=" not in attrs and not DATA_SCRIPT_RE.search(attrs):
                problems.append(Problem(file, line(m.start()), "an inline script"))
        for m in re.finditer(r"<style\b|\sstyle\s*=", html, re.I):
            problems.append(Problem(file, line(m.start()), "an inline style"))
    return problems
