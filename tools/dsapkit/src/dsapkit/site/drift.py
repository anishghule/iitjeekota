"""Find Google documentation that changed since the structured data rules were read from it.

jsonld-rules.json records, for every page a rule comes from, the "Last updated" date that page showed
when the rule was read. This fetches each page again (through dsapkit.net, from developers.google.com
only) and reports every page whose date is different. Google publishes no machine-readable rules, so
a person must then read the page and update the rule; this only says where to look.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from ..errors import BuildError
from ..net import https_get

ALLOWED_HOSTS = frozenset({"developers.google.com"})
USER_AGENT = "dsapkit docs-drift (reads Google Search Central documentation)"
_UPDATED = re.compile(r"Last updated (\d{4}-\d{2}-\d{2}) UTC")


@dataclass(frozen=True)
class Watched:
    url: str
    used_for: tuple[str, ...]  # rule types or topics that depend on the page
    recorded: str              # the "Last updated" date when the rule was read


@dataclass(frozen=True)
class Drift:
    page: Watched
    live: str | None  # None when the page did not show a date

    @property
    def changed(self) -> bool:
        return self.live != self.page.recorded


def watched_pages(rules: Mapping[str, Any]) -> list[Watched]:
    """Every Google page the rules depend on, once each."""
    pages: dict[str, tuple[list[str], str]] = {}
    for name, rule in rules["types"].items():
        if "docs" in rule:
            pages.setdefault(rule["docs"], ([], rule["updated"]))[0].append(name)
    for entry in rules["watch"]:
        pages.setdefault(entry["url"], ([], entry["updated"]))[0].append(entry["id"])
    return [Watched(url, tuple(used), updated) for url, (used, updated) in pages.items()]


def live_date(page_html: str) -> str | None:
    match = _UPDATED.search(page_html)
    return match.group(1) if match else None


def fetch_page(url: str) -> str:
    return https_get(url, allow=ALLOWED_HOSTS, user_agent=USER_AGENT, max_bytes=8 * 1024 * 1024).decode("utf-8", "replace")


def check_drift(rules: Mapping[str, Any], fetch: Callable[[str], str] = fetch_page) -> list[Drift]:
    return [Drift(page, live_date(fetch(page.url))) for page in watched_pages(rules)]


def require_no_drift(drifts: list[Drift]) -> None:
    changed = [d for d in drifts if d.changed]
    if changed:
        lines = [f"{d.page.url}: recorded {d.page.recorded}, now {d.live or 'no date shown'} (rules: {', '.join(d.page.used_for)})"
                 for d in changed]
        raise BuildError("Google documentation changed since the rules were read. Read these pages, update "
                         "jsonld-rules.json (the rule, 'updated' and 'checked'), then run this again:\n  " + "\n  ".join(lines))
