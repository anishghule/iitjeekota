"""The site registry: fixed routes from routes.json, plus area, centre and blog post routes derived from their data files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..errors import BuildError
from ..jsonio import read_json
from ..paths import Paths

PILLAR_TEMPLATES = {"pillar"}
POST_STATUSES = {"planned", "written"}
STANDALONE_TEMPLATES = {"home", "page", "legal"}


@dataclass(frozen=True)
class Keywords:
    primary: str
    secondary: tuple[str, ...]
    draft: bool


@dataclass(frozen=True)
class Fact:
    id: str
    status: str
    value: Any  # text, or structured data such as a map pin
    source: str | None
    note: str | None
    localized: dict[str, Any] = field(default_factory=dict)  # locale -> the value in that language, same shape

    @property
    def confirmed(self) -> bool:
        return self.status == "confirmed"


LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")  # a value with words in it needs a translation; digits and phone numbers do not


@dataclass(frozen=True)
class Route:
    id: str
    template: str
    slug: str
    names: dict[str, str]
    pillar: str | None = None
    keywords: dict[str, Keywords] = field(default_factory=dict)
    gates: tuple[str, ...] = ()
    nav: int | None = None
    nav_names: dict[str, str] = field(default_factory=dict)  # shorter link text for the header, where a name is long
    is_pillar: bool = False
    area_hub: str | None = None
    area: str | None = None
    centre: str | None = None
    tier: int | None = None
    fact: str | None = None
    targets: tuple[str, ...] = ()  # for blog posts: the pages a post supports
    allow: tuple[str, ...] = ()    # claim words cleared for this page's copy (copy-lint-allow)
    planned: bool = False          # proposed content (blog plan), not a page yet

    @property
    def locales(self) -> list[str]:
        return list(self.names)

    def path(self, locale: str) -> str:
        return f"/{locale}/" + (f"{self.slug}/" if self.slug else "")


@dataclass
class Site:
    config: dict[str, Any]
    locales: list[str]
    routes: dict[str, Route]
    facts: dict[str, Fact]
    areas: dict[str, dict[str, Any]]
    centres: dict[str, dict[str, Any]]
    blog: dict[str, Any]
    citations: dict[str, Any]
    volumes: dict[str, dict[str, Any]] = field(default_factory=dict)  # normalised keyword -> Keyword Planner row
    volume_imports: list[dict[str, Any]] = field(default_factory=list)  # where and when each batch of volumes came from

    def volume(self, keyword: str) -> dict[str, Any] | None:
        return self.volumes.get(" ".join(keyword.lower().split()))

    @property
    def origin(self) -> str:
        return self.config["origin"].rstrip("/")

    def url(self, route_id: str, locale: str) -> str:
        return self.origin + self.routes[route_id].path(locale)

    def fact_value(self, fact_id: str, field_name: str | None = None, locale: str | None = None) -> tuple[Any, str | None]:
        """A confirmed fact's value, or one field of a structured fact, in a language. Returns (value, None),
        or (None, why) where why starts with "unknown" for a wrong reference and "pending" otherwise.
        Outside the default locale, a value with words in it needs that language's value (localized in
        facts.json); until then it is pending, so copy never mixes English words into another script."""
        fact = self.facts.get(fact_id)
        ref = fact_id + (f"#{field_name}" if field_name else "")
        if fact is None:
            return None, f"unknown fact {ref}"
        if not fact.confirmed:
            return None, f"pending fact {fact_id}"
        value = fact.value
        if field_name is not None:
            if not isinstance(value, dict) or field_name not in value:
                return None, f"unknown fact {ref}"
            value = value[field_name]
        if locale is None or locale == self.config["defaultLocale"] or not isinstance(value, str):
            return value, None
        local = fact.localized.get(locale)
        if isinstance(local, dict) and field_name is not None:
            local = local.get(field_name)
        if isinstance(local, str):
            return local, None
        if LATIN_WORD_RE.search(value):
            return None, f"pending fact {ref} in {locale}"
        return value, None

    COMMUTE_FIELDS = ("km",)

    def commute_value(self, area_id: str, field_name: str) -> tuple[Any, str | None]:
        """A field of the route from an area to its nearest centre, read like fact_value.
        A placeholder commute counts as pending; an area with the centre in it has no route."""
        area = self.areas.get(area_id)
        ref = f"{area_id}#{field_name}"
        if area is None or field_name not in self.COMMUTE_FIELDS:
            return None, f"unknown commute {ref}"
        route = next((r for r in area["commute"]["routes"] if r["centre"] == area["nearestCentre"]), None)
        if route is None:
            return None, f"unknown commute {ref}: the centre is in {area_id}"
        if area["commute"]["status"] != "confirmed":
            return None, f"pending commute.{area_id}"
        return route[field_name], None

    def pending_gates(self, route: Route) -> list[str]:
        """Pending facts the page names, plus gates its data implies: an area page waits until D-SAP
        confirms its commute (the doorway guard in the plan, B2)."""
        pending = [g for g in route.gates if g in self.facts and not self.facts[g].confirmed]
        if route.area and self.areas[route.area]["commute"]["status"] != "confirmed":
            pending.append(f"commute.{route.area}")
        return pending

    def is_live(self, route_id: str) -> bool:
        """A page can go live when it is not just planned and none of its gating facts is pending."""
        route = self.routes[route_id]
        return not route.planned and not self.pending_gates(route)

    def pillars(self) -> list[Route]:
        return [r for r in self.routes.values() if r.is_pillar]


def _keywords(raw: dict[str, Any] | None) -> dict[str, Keywords]:
    return {loc: Keywords(k["primary"], tuple(k.get("secondary", [])), bool(k.get("draft"))) for loc, k in (raw or {}).items()}


def _from_pattern(pattern: dict[str, Any], names: dict[str, str]) -> dict[str, Keywords]:
    out = {}
    for loc, p in pattern.items():
        if loc.startswith("$") or loc not in names:
            continue
        name = names[loc].lower() if loc == "en" else names[loc]
        out[loc] = Keywords(p["primary"].format(name=name), tuple(s.format(name=name) for s in p["secondary"]), bool(p.get("draft")))
    return out


def load_site(paths: Paths) -> Site:
    root = paths.site
    config = read_json(root / "site.json")
    locales = [loc["code"] for loc in config["locales"]]
    facts = {f["id"]: Fact(f["id"], f["status"], f.get("value"), f.get("source"), f.get("note"), f.get("localized", {}))
             for f in read_json(root / "facts.json")["facts"]}
    areas = {a["id"]: a for a in read_json(root / "areas.json")["areas"]}
    centres = {c["id"]: c for c in read_json(root / "centres.json")["centres"]}
    blog = read_json(root / "blog.json")
    citations = read_json(root / "citations.json")
    volumes_raw = read_json(root / "keyword-volumes.json") if (root / "keyword-volumes.json").exists() else {"imports": [], "keywords": []}
    imports = {i["id"] for i in volumes_raw["imports"]}
    volumes = {}
    for row in volumes_raw["keywords"]:
        if row["import"] not in imports:
            raise BuildError(f"keyword-volumes.json: {row['keyword']!r} names unknown import {row['import']!r}")
        volumes[" ".join(row["keyword"].lower().split())] = row

    routes: dict[str, Route] = {}

    def add(route: Route) -> None:
        if route.id in routes:
            raise BuildError(f"duplicate route id {route.id!r}")
        routes[route.id] = route

    hub_pillars: dict[str, str] = {}
    collectors: dict[str, str] = {}
    for r in read_json(root / "routes.json")["routes"]:
        route = Route(
            id=r["id"], template=r["template"], slug=r["slug"], names=r["names"], pillar=r.get("pillar"),
            keywords=_keywords(r.get("keywords")), gates=tuple(r.get("gates", [])), nav=r.get("nav"),
            is_pillar=r["template"] in PILLAR_TEMPLATES or bool(r.get("pillarRole")), area_hub=r.get("areaHub"),
            fact=r.get("fact"), nav_names=r.get("navNames", {}),
        )
        add(route)
        if route.area_hub:
            hub_pillars[route.area_hub] = route.id
        if "collects" in r:
            collectors[r["collects"]] = route.id
    for kind in ("centres", "posts"):
        if kind not in collectors:
            raise BuildError(f"routes.json: no pillar collects {kind}")

    for area in areas.values():
        if area["hub"] not in hub_pillars:
            raise BuildError(f"area {area['id']}: hub {area['hub']!r} has no pillar with that areaHub")
        add(Route(id=f"area-{area['id']}", template="area", slug=f"iit-jee-coaching-{area['id']}", names=area["names"],
                  pillar=hub_pillars[area["hub"]], keywords=_from_pattern(config["areaKeywords"], area["names"]),
                  area=area["id"], tier=area["tier"]))

    centres_pillar = routes[collectors["centres"]]
    for centre in centres.values():
        if centre["area"] not in areas:
            raise BuildError(f"centre {centre['id']}: area {centre['area']!r} is not in areas.json")
        gates = tuple(centre["facts"][k] for k in config["centreGates"])
        add(Route(id=f"centre-{centre['id']}", template="centre", slug=f"{centres_pillar.slug}/{centre['id']}",
                  names=centre["names"], pillar=centres_pillar.id,
                  keywords=_from_pattern(config["centreKeywords"], areas[centre["area"]]["names"]),
                  centre=centre["id"], gates=gates))

    blog_route = collectors["posts"]
    for post in blog["posts"]:
        if post["status"] not in POST_STATUSES:
            raise BuildError(f"blog.json post {post['id']}: status must be one of {sorted(POST_STATUSES)}")
        names = {loc: title for loc, title in post["title"].items()}
        keywords = {loc: Keywords(q, (), False) for loc, q in post["query"].items()}
        add(Route(id=f"post-{post['id']}", template="post", slug=blog["slugPattern"].format(slug=post["id"]), names=names,
                  pillar=blog_route, keywords=keywords, targets=tuple(post.get("targets", [])),
                  gates=tuple(post.get("gates", [])), allow=tuple(post.get("$copyLintAllow", [])),
                  planned=post["status"] == "planned"))

    return Site(config, locales, routes, facts, areas, centres, blog, citations, volumes, volumes_raw["imports"])
