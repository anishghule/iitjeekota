"""Breadcrumbs, hreflang alternates and the generated internal links of every page."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .model import Route, Site

FOOTER_GROUPS = {"pillars", "centres", "pages", "legal"}


@dataclass(frozen=True)
class Crumb:
    name: str
    url: str


def breadcrumbs(site: Site, route: Route, locale: str) -> list[Crumb]:
    """Home > Pillar > Page. The home page has none."""
    if route.template == "home":
        return []
    home = next(r for r in site.routes.values() if r.template == "home")
    trail = [home]
    if route.pillar:
        trail.append(site.routes[route.pillar])
    trail.append(route)
    return [Crumb(r.names[locale], site.url(r.id, locale)) for r in trail]


def alternates(site: Site, route: Route) -> dict[str, str]:
    """hreflang code -> URL for every locale the page exists in, plus x-default."""
    codes = {loc["code"]: loc["hreflang"] for loc in site.config["locales"]}
    out = {codes[loc]: site.url(route.id, loc) for loc in route.locales}
    default = site.config["xDefault"]
    if default in route.locales:
        out["x-default"] = site.url(route.id, default)
    return out


def _footer(site: Site) -> list[str]:
    groups = site.config["linking"]["footer"]
    out = []
    if "pillars" in groups:
        out += [r.id for r in site.pillars()]
    if "centres" in groups:
        out += [r.id for r in site.routes.values() if r.template == "centre"]
    if "pages" in groups:
        out += [r.id for r in site.routes.values() if r.template == "page"]
    if "legal" in groups:
        out += [r.id for r in site.routes.values() if r.template == "legal"]
    return out


def body_links(site: Site, route: Route) -> list[str]:
    """Links placed in the page body by the linking rules in site.json (targets may be gated)."""
    rules = site.config["linking"]
    children = [r.id for r in site.routes.values() if r.pillar == route.id]
    supporting_posts = [r.id for r in site.routes.values() if route.id in r.targets]
    programmes = [r.id for r in site.routes.values() if r.template == "programme"]
    links: list[str] = []
    if route.template == "home":
        links = [r.id for r in sorted((r for r in site.routes.values() if r.nav), key=lambda r: r.nav)]
        links += [r.id for r in site.pillars() if r.id not in links]
    elif route.is_pillar:
        links = children
    elif route.template == "area":
        area = site.areas[route.area]
        links = [route.pillar, f"centre-{area['nearestCentre']}"]
        links += [f"area-{n}" for n in area["neighbours"][: rules["spokeNeighbours"]]]
        links += rules["spokeAlsoLinks"] + programmes[: rules["spokeProgrammes"]]
    elif route.template == "centre":
        centre = site.centres[route.centre]
        links = [route.pillar, f"area-{centre['area']}"] + programmes
    elif route.template == "post":
        links = [route.pillar, *route.targets]
    elif route.pillar:
        links = [route.pillar] + [r.id for r in site.routes.values() if r.pillar == route.pillar and r.id != route.id]
    links += supporting_posts
    return list(dict.fromkeys(link for link in links if link != route.id))


def live_links(site: Site, route: Route) -> list[str]:
    """Body links followed by footer links, keeping only pages that are live."""
    return [link for link in dict.fromkeys(body_links(site, route) + _footer(site))
            if link != route.id and site.is_live(link)]


def clicks_from_home(site: Site) -> dict[str, int]:
    """Fewest clicks from the home page to every live page, following live links only."""
    home = next(r for r in site.routes.values() if r.template == "home")
    depth = {home.id: 0}
    queue = deque([home.id])
    while queue:
        current = queue.popleft()
        for target in live_links(site, site.routes[current]):
            if target not in depth:
                depth[target] = depth[current] + 1
                queue.append(target)
    return depth


def check_links(site: Site) -> list[str]:
    problems = []
    unknown_groups = set(site.config["linking"]["footer"]) - FOOTER_GROUPS
    if unknown_groups:
        problems.append(f"site.json linking.footer has unknown groups {sorted(unknown_groups)}; use {sorted(FOOTER_GROUPS)}")
    for route in site.routes.values():
        for target in body_links(site, route):
            if target not in site.routes:
                problems.append(f"{route.id}: links to unknown page {target!r}")
    limit = site.config["linking"]["maxClicksFromHome"]
    depth = clicks_from_home(site)
    for route in site.routes.values():
        if not site.is_live(route.id):
            continue
        if route.id not in depth:
            problems.append(f"{route.id}: live but not reachable from the home page")
        elif depth[route.id] > limit:
            problems.append(f"{route.id}: {depth[route.id]} clicks from home, limit {limit}")
    return problems
