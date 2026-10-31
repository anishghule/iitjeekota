"""Keyword Planner files: what to paste into Google Ads, and the map that ties each keyword back to its page."""

from __future__ import annotations

import csv
import io

from ..errors import BuildError
from .model import Site


def keyword_rows(site: Site) -> list[tuple[str, str, str, str]]:
    """(locale, keyword, page id, role) for every keyword in the registry, primaries first."""
    rows = []
    for route in site.routes.values():
        for locale, kw in route.keywords.items():
            rows.append((locale, kw.primary, route.id, "primary"))
            rows += [(locale, s, route.id, "secondary") for s in kw.secondary]
    return rows


def check_planner_limits(site: Site) -> list[str]:
    cfg = site.config["keywordPlanner"]
    problems = [f"{page}: {locale} keyword {kw!r} is longer than {cfg['maxLength']} characters"
                for locale, kw, page, _ in keyword_rows(site) if len(kw) > cfg["maxLength"]]
    problems += [f"{page}: {locale} keyword {kw!r} has more than {cfg['maxWords']} words"
                 for locale, kw, page, _ in keyword_rows(site) if len(kw.split()) > cfg["maxWords"]]
    seeds = cfg["seedRoutes"]
    if len(seeds) > cfg["maxSeeds"]:
        problems.append(f"site.json keywordPlanner has {len(seeds)} seeds; Keyword Planner takes {cfg['maxSeeds']}")
    problems += [f"site.json keywordPlanner seed {s!r} is not a route" for s in seeds if s not in site.routes]
    return problems


def planner_files(site: Site) -> dict[str, str]:
    problems = check_planner_limits(site)
    if problems:
        raise BuildError("keyword planner limits:\n  " + "\n  ".join(problems))
    rows = keyword_rows(site)
    files = {}
    for locale in site.locales:
        unique = list(dict.fromkeys(kw for loc, kw, _, _ in rows if loc == locale))
        files[f"search-volume-{locale}.txt"] = "\n".join(unique) + "\n"
    seeds = [site.routes[r].keywords["en"].primary for r in site.config["keywordPlanner"]["seedRoutes"]]
    files["seed-keywords-en.txt"] = "\n".join(seeds) + "\n"
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["locale", "keyword", "page", "role", "url"])
    for locale, kw, page, role in rows:
        writer.writerow([locale, kw, page, role, site.url(page, locale) if locale in site.routes[page].locales else ""])
    files["keyword-map.csv"] = out.getvalue()
    return files
