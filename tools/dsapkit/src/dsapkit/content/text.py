"""The inline syntax of page copy, resolved against the site registry.

  {{fact:id}} or {{fact:id#field}}   a confirmed fact's value
  {{commute:area-id#km}}              the distance from an area to its nearest centre (areas.json)
  {{syllabus:main#year}}, {{syllabus:all#chapters}}   the syllabus documents and chapter counts (syllabus.json)
  [anchor](page:route-id)             a link to a page, by route id

A paragraph that names a pending fact or a placeholder commute, or requires a pending
fact, is held back. A link to a page that is not live yet keeps its anchor as plain text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..site.model import Site
from .syllabus import Syllabus

FACT_RE = re.compile(r"\{\{fact:([\w.-]+)(?:#(\w+))?\}\}")
COMMUTE_RE = re.compile(r"\{\{commute:([\w-]+)#(\w+)\}\}")
SYLLABUS_RE = re.compile(r"\{\{syllabus:([\w-]+)#(\w+)\}\}")
PLACEHOLDER_RE = re.compile(r"\{\{[^{}]*\}\}")  # any placeholder, for measuring a page's own words
LINK_RE = re.compile(r"\[([^\]]+)\]\(page:([\w-]+)\)")
STRAY_RE = re.compile(r"\{\{|\}\}|\]\((?!page:)[^)]*\)")  # placeholders or links in any other form


@dataclass(frozen=True)
class Part:
    """A run of resolved text; a link to a live page carries that page's route id."""
    text: str
    route: str | None = None


@dataclass(frozen=True)
class Resolved:
    text: str | None                # plain text with facts filled and anchors kept; None when held back
    pending: tuple[str, ...] = ()   # facts holding it back
    unknown: tuple[str, ...] = ()   # references to facts or pages that do not exist, or malformed syntax
    links: tuple[str, ...] = ()     # live pages it links to
    unlinked: tuple[str, ...] = ()  # pages it links to that are not live yet
    parts: tuple[Part, ...] = ()    # the text split at its live links, for rendering; empty when held back


def resolve(text: str, site: Site, requires: tuple[str, ...] = (), syllabus: Syllabus | None = None,
            locale: str | None = None) -> Resolved:
    """Resolves one text in a language (None means the default locale)."""
    pending, unknown = [], []
    for fact_id in requires:
        _, why = site.fact_value(fact_id)
        (unknown if why and why.startswith("unknown") else pending).extend([fact_id] if why else [])

    def fill(match: re.Match[str]) -> str:
        ref = match.group(0)[len("{{fact:"):-len("}}")]
        value, why = site.fact_value(match.group(1), match.group(2), locale)
        if why:
            (unknown if why.startswith("unknown") else pending).append(why.removeprefix("pending fact "))
            return ""  # the paragraph is held back, so nothing is shown in its place
        if isinstance(value, (dict, list)):
            unknown.append(f"{ref} is structured; name a field with #")
            return ""
        return str(value)

    def commute(match: re.Match[str]) -> str:
        value, why = site.commute_value(match.group(1), match.group(2))
        if why:
            (unknown if why.startswith("unknown") else pending).append(why.removeprefix("pending "))
            return ""
        return str(value)

    def syllabus_value(match: re.Match[str]) -> str:
        if syllabus is None:
            unknown.append(f"{match.group(0)} (no syllabus given)")
            return ""
        value, why = syllabus.value(match.group(1), match.group(2))
        if why:
            unknown.append(why)
            return ""
        return str(value)

    filled = SYLLABUS_RE.sub(syllabus_value, COMMUTE_RE.sub(commute, FACT_RE.sub(fill, text)))
    links, unlinked, parts, start = [], [], [], 0
    for match in LINK_RE.finditer(filled):
        anchor, target = match.group(1), match.group(2)
        live = False
        if target not in site.routes:
            unknown.append(f"page:{target}")
        elif site.is_live(target):
            links.append(target)
            live = True
        else:
            unlinked.append(target)
        if match.start() > start:
            parts.append(Part(filled[start:match.start()]))
        parts.append(Part(anchor, target if live else None))
        start = match.end()
    if start < len(filled):
        parts.append(Part(filled[start:]))
    out = "".join(p.text for p in parts)
    unknown += [f"malformed {m.group(0)!r}" for m in STRAY_RE.finditer(out)]
    if pending or unknown:
        return Resolved(None, tuple(pending), tuple(unknown), tuple(links), tuple(unlinked))
    return Resolved(out, (), (), tuple(links), tuple(unlinked), tuple(_merge(parts)))


def _merge(parts: list[Part]) -> list[Part]:
    """Joins neighbouring plain runs, so a link to a page that is not live reads as one run of text."""
    out: list[Part] = []
    for p in parts:
        if out and p.route is None and out[-1].route is None:
            out[-1] = Part(out[-1].text + p.text)
        else:
            out.append(p)
    return out
