"""Data for interactive sections (packages/content/widgets/{locale}/{name}.json), resolved like copy.

A widget is any JSON. Every string is resolved with the inline syntax of page copy (facts, commutes,
syllabus counts). An object may list "requires"; it is held back while any of those facts is
pending, and so is an object with a held string in it. A held object is dropped from the list it is
in; a held widget as a whole is not shown. Keys starting with "$" are notes. Links belong in page
copy, so a widget string with [anchor](page:id) is an error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..site.model import Site
from .syllabus import Syllabus
from .text import LINK_RE, resolve


@dataclass
class WidgetResult:
    value: Any                                                       # None when the whole widget is held back
    held: list[tuple[str, list[str]]] = field(default_factory=list)  # (path, pending facts)
    unknown: list[tuple[str, str]] = field(default_factory=list)     # (path, reference)


class _Held(Exception):
    def __init__(self, pending: list[str]) -> None:
        super().__init__()
        self.pending = pending


def resolve_widget(raw: Any, site: Site, syllabus: Syllabus, locale: str) -> WidgetResult:
    result = WidgetResult(None)

    def walk(value: Any, path: str) -> Any:
        if isinstance(value, str):
            if LINK_RE.search(value):
                result.unknown.append((path, "a page link (links belong in page copy)"))
            r = resolve(value, site, (), syllabus, locale)
            result.unknown += [(path, ref) for ref in r.unknown]
            if r.text is None:
                raise _Held(list(r.pending))
            return r.text
        if isinstance(value, list):
            out = []
            for i, item in enumerate(value):
                try:
                    out.append(walk(item, f"{path}[{i}]"))
                except _Held as held:
                    result.held.append((f"{path}[{i}]", held.pending))
            return out
        if isinstance(value, dict):
            requires = value.get("requires", [])
            pending = []
            for fact_id in requires:
                _, why = site.fact_value(fact_id)
                if why and why.startswith("unknown"):
                    result.unknown.append((path, fact_id))
                elif why:
                    pending.append(fact_id)
            if pending:
                raise _Held(pending)
            return {k: walk(v, f"{path}.{k}" if path else k) for k, v in value.items()
                    if not k.startswith("$") and k != "requires"}
        return value

    try:
        result.value = walk(raw, "")
    except _Held as held:
        result.held.append(("(whole widget)", held.pending))
    return result
