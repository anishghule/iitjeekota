"""Checks on the site registry. Each returns problems as text; make site stops on any."""

from __future__ import annotations

from collections import defaultdict

from ..tokens import TokenSet
from .model import STANDALONE_TEMPLATES, Site

KEYWORD_EXEMPT = {"legal"}


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def check_locales(site: Site, tokens: TokenSet) -> list[str]:
    script = set(tokens.tree["type"]["latin"]["locales"]) | set(tokens.tree["type"]["devanagari"]["locales"])
    if set(site.locales) != script:
        return [f"site.json locales {sorted(site.locales)} differ from the locales tokens.json sets type for {sorted(script)}"]
    return []


def check_routes(site: Site) -> list[str]:
    problems = []
    seen_paths: dict[str, str] = {}
    max_depth = site.config["breadcrumbs"]["maxDepth"]
    for route in site.routes.values():
        unknown = [loc for loc in route.locales if loc not in site.locales]
        if unknown:
            problems.append(f"{route.id}: names in unknown locales {unknown}")
        for loc in route.locales:
            path = route.path(loc)
            if path in seen_paths:
                problems.append(f"{route.id}: path {path} is also used by {seen_paths[path]}")
            seen_paths[path] = route.id
        if route.pillar:
            parent = site.routes.get(route.pillar)
            if parent is None:
                problems.append(f"{route.id}: pillar {route.pillar!r} does not exist")
            elif not parent.is_pillar:
                problems.append(f"{route.id}: breadcrumb parent {route.pillar!r} is not a pillar")
            elif parent.pillar:
                problems.append(f"{route.id}: trail is deeper than {max_depth} (its pillar has a parent)")
            elif not set(route.locales) <= set(parent.locales):
                problems.append(f"{route.id}: exists in a locale its pillar does not")
        if route.is_pillar and route.pillar:
            problems.append(f"{route.id}: a pillar cannot have a breadcrumb parent")
        if not route.pillar and not route.is_pillar and route.template not in STANDALONE_TEMPLATES:
            problems.append(f"{route.id}: a {route.template} page needs a pillar")
        for gate in route.gates:
            if gate not in site.facts:
                problems.append(f"{route.id}: gate {gate!r} is not in facts.json")
        if route.fact:
            fact = site.facts.get(route.fact)
            if fact is None:
                problems.append(f"{route.id}: fact {route.fact!r} is not in facts.json")
            elif not fact.confirmed:
                problems.append(f"{route.id}: describes {route.fact}, which is not confirmed")
        for target in route.targets:
            if target not in site.routes:
                problems.append(f"{route.id}: supports unknown page {target!r}")
    navs = [r.nav for r in site.routes.values() if r.nav is not None]
    if len(navs) != len(set(navs)):
        problems.append("two routes share a nav position")
    return problems


def check_keywords(site: Site) -> list[str]:
    """One primary keyword per page and locale; a page's secondaries never take another page's primary."""
    problems = []
    primaries: dict[str, dict[str, str]] = defaultdict(dict)
    for route in site.routes.values():
        if route.template in KEYWORD_EXEMPT:
            continue
        for loc in route.locales:
            kw = route.keywords.get(loc)
            if kw is None:
                problems.append(f"{route.id}: no {loc} keywords")
                continue
            key = _norm(kw.primary)
            if key in primaries[loc]:
                problems.append(f"{route.id} and {primaries[loc][key]} both target {loc} {kw.primary!r}")
            primaries[loc][key] = route.id
    for route in site.routes.values():
        for loc, kw in route.keywords.items():
            for secondary in kw.secondary:
                owner = primaries[loc].get(_norm(secondary))
                if owner and owner != route.id:
                    problems.append(f"{route.id}: secondary {secondary!r} is the primary of {owner}")
    return problems


def check_commutes(site: Site) -> list[str]:
    problems = []
    cfg = site.config["commute"]
    _, why = site.fact_value(cfg["fact"], cfg["arriveBy"])
    if why:
        problems.append(f"site.json commute: {why}; commutes are given for arrival by the batch start")
    sources = site.config["commuteSources"]
    for area in site.areas.values():
        commute = area.get("commute")
        if commute is None:
            problems.append(f"area {area['id']}: no commute")
            continue
        if commute["status"] not in ("placeholder", "confirmed"):
            problems.append(f"area {area['id']}: commute status must be placeholder or confirmed")
        if commute["status"] == "confirmed" and not commute.get("checked"):
            problems.append(f"area {area['id']}: a confirmed commute says who checked it and when (checked)")
        local = commute.get("localCentre")
        if local and local != area["nearestCentre"]:
            problems.append(f"area {area['id']}: local centre {local} is not its nearest centre")
        for route in commute["routes"]:
            if route["centre"] not in site.centres:
                problems.append(f"area {area['id']}: commute to unknown centre {route['centre']!r}")
            if route["source"] not in sources:
                problems.append(f"area {area['id']}: commute source {route['source']!r} is not in site.json commuteSources")
            span = route.get("minutes")
            if span is not None and not (isinstance(span, list) and len(span) == 2 and 0 < span[0] <= span[1]):
                problems.append(f"area {area['id']}: minutes is [shortest, longest], for example [12, 16]")
        nearest =[r for r in commute["routes"] if r["centre"] == area["nearestCentre"]]
        if not local and not nearest:
            problems.append(f"area {area['id']}: no commute to its nearest centre")
        if commute["status"] == "confirmed" and nearest and not ({"minutes", "freeFlowMinutes"} & nearest[0].keys()):
            problems.append(f"area {area['id']}: a confirmed commute needs a time to the nearest centre (minutes or freeFlowMinutes)")
    return problems


def commute_notes(site: Site) -> list[str]:
    """Areas whose distances put the other centre closer than the one their page sends students to."""
    notes = []
    for area in site.areas.values():
        routes = {r["centre"]: r["km"] for r in area.get("commute", {}).get("routes", [])}
        nearest = area["nearestCentre"]
        if nearest in routes:
            closer = [c for c, km in routes.items() if c != nearest and km < routes[nearest]]
            if closer:
                notes.append(f"{area['names']['en']}: the distances put {', '.join(closer)} closer than {nearest}")
    return notes


def check_areas(site: Site) -> list[str]:
    problems = []
    for area in site.areas.values():
        if area["nearestCentre"] not in site.centres:
            problems.append(f"area {area['id']}: nearest centre {area['nearestCentre']!r} is not in centres.json")
        for n in area["neighbours"]:
            if n not in site.areas:
                problems.append(f"area {area['id']}: neighbour {n!r} is not in areas.json")
            if n == area["id"]:
                problems.append(f"area {area['id']}: lists itself as a neighbour")
        if area["tier"] not in (1, 2):
            problems.append(f"area {area['id']}: tier must be 1 or 2")
    return problems


def check_site(site: Site, tokens: TokenSet) -> list[str]:
    return check_locales(site, tokens) + check_routes(site) + check_keywords(site) + check_areas(site) + check_commutes(site)
