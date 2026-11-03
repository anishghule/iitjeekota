"""The small Markdown a guide uses, as blocks the site renders itself (no Markdown library, no raw HTML).

A guide holds `##` and `###` headings, paragraphs, bullet lists (`* ` or `- `), numbered lists
(`1. `) and, inside text, `**bold**` and `[anchor](page:route-id)` links. Anything else, and above all
raw HTML, is an error: copy stays plain words, and the page is built from typed blocks, so a guide
cannot put markup into a page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..errors import BuildError

BULLET_RE = re.compile(r"^[*-] +(.+)$")
NUMBER_RE = re.compile(r"^\d+\. +(.+)$")
HEADING_RE = re.compile(r"^(#{2,3}) +(.+)$")
HTML_RE = re.compile(r"</?[A-Za-z][^>]*>|<!--")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


@dataclass(frozen=True)
class Block:
    kind: str                  # h2, h3, p, ul, ol
    texts: tuple[str, ...]     # one text for a heading or paragraph, one per item for a list


def parse_blocks(blocks: list[str], where: str) -> list[Block]:
    out = []
    for raw in blocks:
        if HTML_RE.search(raw):
            raise BuildError(f"{where}: raw HTML is not allowed in a guide: {raw[:60]!r}")
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if heading := HEADING_RE.match(lines[0]):
            if len(lines) > 1:
                raise BuildError(f"{where}: a heading stands alone: {raw[:60]!r}")
            out.append(Block(f"h{len(heading.group(1))}", (heading.group(2),)))
        elif all(BULLET_RE.match(line) for line in lines):
            out.append(Block("ul", tuple(BULLET_RE.match(line).group(1) for line in lines)))  # type: ignore[union-attr]
        elif all(NUMBER_RE.match(line) for line in lines):
            out.append(Block("ol", tuple(NUMBER_RE.match(line).group(1) for line in lines)))  # type: ignore[union-attr]
        elif any(BULLET_RE.match(line) or NUMBER_RE.match(line) or line.startswith("#") for line in lines):
            raise BuildError(f"{where}: a list or heading mixed into a paragraph: {raw[:60]!r}")
        else:
            out.append(Block("p", (" ".join(lines),)))
    return out


def split_bold(text: str) -> list[tuple[str, bool]]:
    """(text, bold) runs of one text, with the ** marks removed."""
    runs, last = [], 0
    for match in BOLD_RE.finditer(text):
        if match.start() > last:
            runs.append((text[last:match.start()], False))
        runs.append((match.group(1), True))
        last = match.end()
    if last < len(text):
        runs.append((text[last:], False))
    return runs
