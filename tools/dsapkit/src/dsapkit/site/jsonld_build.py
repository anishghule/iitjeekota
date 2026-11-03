"""Builds each page's JSON-LD from the registry, the facts and the page's own data.

One builder per node type; `build_graph` picks the nodes a page's template needs (plan B5, rules in
packages/site/jsonld-rules.json). Nothing here is written by hand per page:

- Values come from data (identity.json, centres.json, areas.json, facts.json, the page's copy).
- A property whose fact is still pending is left out and reported, never filled with a placeholder.
- Dates are stored as days and become timestamps only through formats.timestamp.
- The breadcrumb comes from links.breadcrumbs, the same trail the page shows.
- Google's rules are checked afterwards by jsonld.check_graphs; this module does not repeat them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .formats import clock_time, timestamp
from .links import breadcrumbs
from .model import Route, Site

CONTEXT = "https://schema.org"


@dataclass(frozen=True)
class Brand:
    """The brand facts structured data needs, from identity.json and the exported logo."""
    names: Mapping[str, str]
    alternate_names: tuple[str, ...]
    descriptions: Mapping[str, str]
    logo_path: str   # site-relative, for example /brand/medal-512.png
    logo_size: int   # the logo is square


@dataclass(frozen=True)
class PageInfo:
    """What a page contributes: its copy and its own data. The social image is an absolute URL."""
    title: str
    description: str
    headline: str
    published: str | None = None
    modified: str | None = None
    author: str | None = None   # a fact id naming the author (posts)
    image: str | None = None


@dataclass
class Built:
    graph: dict[str, Any]
    pending: list[tuple[str, str]] = field(default_factory=list)  # (property left out, why)


class _Ctx:
    """One page being built: the lookups every node builder shares."""

    def __init__(self, site: Site, brand: Brand, route: Route, locale: str) -> None:
        self.site, self.brand, self.route, self.locale = site, brand, route, locale
        self.pending: list[tuple[str, str]] = []

    def fact(self, prop: str, fact_id: str, field_name: str | None = None) -> Any:
        """A confirmed fact for the property `prop`; None, with a note, while it is pending."""
        value, why = self.site.fact_value(fact_id, field_name, self.locale)
        if why:
            self.pending.append((prop, why))
        return value

    def url(self, route_id: str) -> str:
        return self.site.url(route_id, self.locale)

    def live(self, route_id: str) -> bool:
        return route_id in self.site.routes and self.site.is_live(route_id) and self.locale in self.site.routes[route_id].locales

    @property
    def origin(self) -> str:
        return self.site.origin

    @property
    def hreflang(self) -> str:
        return next(l["hreflang"] for l in self.site.config["locales"] if l["code"] == self.locale)

    @property
    def page_url(self) -> str:
        return self.url(self.route.id)

    @property
    def is_default_home(self) -> bool:
        return self.route.template == "home" and self.locale == self.site.config["defaultLocale"]

    def stamp(self, stored: str | None) -> str | None:
        return timestamp(stored, self.site.config["dates"]) if stored else None


def org_id(site: Site) -> str:
    return f"{site.origin}/#organization"


def website_id(site: Site) -> str:
    return f"{site.origin}/#website"


def centre_id(site: Site, centre: str, locale: str) -> str:
    return f"{site.url(f'centre-{centre}', locale)}#centre"


def _compact(node: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in node.items() if v not in (None, "", [], {})}


def _address(raw: Mapping[str, str]) -> dict[str, Any]:
    return {"@type": "PostalAddress", **raw}


def _head_office(site: Site) -> dict[str, Any]:
    return next((c for c in site.centres.values() if c["role"] == "head office"), next(iter(site.centres.values())))


def _organization(c: _Ctx) -> dict[str, Any]:
    site, brand = c.site, c.brand
    default = site.config["defaultLocale"]
    phone = c.fact("telephone", "contact.phone")
    email = c.fact("email", "contact.email")
    founded = c.fact("foundingDate", "org.founded", "year")
    founder = c.fact("founder", "org.founder", "name")
    same_as = c.fact("sameAs", "org.same-as")
    languages = [loc["name"] for loc in site.config["locales"]]
    return _compact({
        "@type": "EducationalOrganization",
        "@id": org_id(site),
        "name": brand.names[default],
        "alternateName": list(brand.alternate_names),  # the same as WebSite: Google asks for one site name
        "url": f"{site.origin}/",
        "logo": {"@type": "ImageObject", "url": site.origin + brand.logo_path, "width": brand.logo_size, "height": brand.logo_size},
        "description": brand.descriptions.get(default),
        "address": _address(_head_office(site)["address"]),
        "telephone": phone,
        "email": email,
        "contactPoint": _compact({"@type": "ContactPoint", "telephone": phone, "email": email, "contactType": "admissions",
                                  "availableLanguage": languages}) if phone or email else None,
        "sameAs": same_as,
        "foundingDate": founded,
        "founder": _compact({"@type": "Person", "name": founder, "url": c.url("about") if c.live("about") else None}) if founder else None,
    })


def _website(c: _Ctx) -> dict[str, Any]:
    site, default = c.site, c.site.config["defaultLocale"]
    return {
        "@type": "WebSite", "@id": website_id(site), "name": c.brand.names[default],
        "alternateName": list(c.brand.alternate_names), "url": f"{site.origin}/",
        "inLanguage": [loc["hreflang"] for loc in site.config["locales"]], "publisher": {"@id": org_id(site)},
    }


def _webpage(c: _Ctx, info: PageInfo) -> dict[str, Any]:
    site, route = c.site, c.route
    types = site.config["jsonld"]["pageTypes"]
    kind = types.get(f"route:{route.id}") or types.get(f"template:{route.template}") or "WebPage"
    node: dict[str, Any] = {
        "@type": kind, "@id": f"{c.page_url}#webpage", "url": c.page_url, "name": info.headline,
        "description": info.description, "inLanguage": c.hreflang, "isPartOf": {"@id": website_id(site)},
        "dateModified": c.stamp(info.modified), "datePublished": c.stamp(info.published),
    }
    if route.template != "home":
        node["breadcrumb"] = {"@id": f"{c.page_url}#breadcrumb"}
    if route.template == "area":
        centre = site.areas[route.area]["nearestCentre"]
        if c.live(f"centre-{centre}"):
            node["about"] = {"@id": centre_id(site, centre, c.locale)}
    return _compact(node)


def _breadcrumb(c: _Ctx) -> dict[str, Any] | None:
    trail = breadcrumbs(c.site, c.route, c.locale)
    if not trail:
        return None
    items = [{"@type": "ListItem", "position": i, "name": crumb.name, "item": crumb.url} for i, crumb in enumerate(trail[:-1], 1)]
    items.append({"@type": "ListItem", "position": len(trail), "name": trail[-1].name})
    return {"@type": "BreadcrumbList", "@id": f"{c.page_url}#breadcrumb", "itemListElement": items}


def _served_areas(c: _Ctx, centre: str) -> list[str]:
    """The names of the areas whose nearest centre this is, or that it stands in: where it says it serves."""
    areas = [a for a in c.site.areas.values() if a["nearestCentre"] == centre or a["commute"].get("localCentre") == centre]
    return [a["names"].get(c.locale, a["names"]["en"]) for a in areas]


def _hours(specs: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    """Opening hours as written in the facts register, with the times in the hh:mm:ss form Google asks for."""
    if not specs:
        return None
    return [{**s, **{k: clock_time(s[k]) for k in ("opens", "closes") if k in s}} for s in specs]


def _centre(c: _Ctx) -> dict[str, Any]:
    site, centre = c.site, c.site.centres[c.route.centre]
    facts = centre["facts"]
    geo = c.fact("geo", facts["geo"])
    return _compact({
        "@type": ["LocalBusiness", "EducationalOrganization"],
        "@id": centre_id(site, centre["id"], c.locale),
        "name": centre["names"].get(c.locale, centre["names"]["en"]),
        "url": c.page_url,
        "image": site.origin + c.brand.logo_path,
        "telephone": c.fact("telephone", facts["phone"]),
        "hasMap": c.fact("hasMap", facts["maps"]),
        "priceRange": c.fact("priceRange", "fees.range"),
        "geo": {"@type": "GeoCoordinates", "latitude": geo["latitude"], "longitude": geo["longitude"]} if geo else None,
        "openingHoursSpecification": _hours(c.fact("openingHoursSpecification", facts["hours"])),
        "address": _address(centre["address"]),
        "areaServed": _served_areas(c, centre["id"]),
        "parentOrganization": {"@id": org_id(site)},
    })


def _courses(c: _Ctx) -> dict[str, Any]:
    """The course list of /programmes/: one entry per live programme page, in registry order."""
    routes = [r for r in c.site.routes.values() if r.template == "programme" and c.live(r.id)]
    items = [{"@type": "ListItem", "position": i, "url": c.url(r.id)} for i, r in enumerate(routes, 1)]
    return {"@type": "ItemList", "@id": f"{c.page_url}#courses", "itemListElement": items}


def _course(c: _Ctx, info: PageInfo) -> dict[str, Any]:
    return {"@type": "Course", "@id": f"{c.page_url}#course", "name": c.route.names[c.locale], "description": info.description,
            "url": c.page_url, "provider": {"@id": org_id(c.site)}}


def _post(c: _Ctx, info: PageInfo) -> dict[str, Any]:
    name = c.fact("author", info.author, "name") if info.author else None
    about = c.url("about") if c.live("about") else None
    return _compact({
        "@type": "BlogPosting", "@id": f"{c.page_url}#post", "mainEntityOfPage": {"@id": f"{c.page_url}#webpage"},
        "headline": info.headline, "image": [info.image] if info.image else None,
        "datePublished": c.stamp(info.published), "dateModified": c.stamp(info.modified), "inLanguage": c.hreflang,
        "author": [_compact({"@type": "Person", "name": name, "url": about})] if name else None,
        "publisher": {"@id": org_id(c.site)},
    })


def build_graph(site: Site, brand: Brand, route: Route, locale: str, info: PageInfo) -> Built:
    """The JSON-LD graph of one page in one language, with what was left out and why."""
    c = _Ctx(site, brand, route, locale)
    nodes: list[dict[str, Any] | None] = []
    if c.is_default_home:
        nodes += [_organization(c), _website(c)]
    nodes.append(_webpage(c, info))
    if route.template == "centre":
        nodes.append(_centre(c))
    elif route.template == "programme":
        nodes.append(_course(c, info))
    elif route.template == "post":
        nodes.append(_post(c, info))
    if route.id == site.config["jsonld"]["courseListRoute"]:
        nodes.append(_courses(c))
    nodes.append(_breadcrumb(c))
    return Built({"@context": CONTEXT, "@graph": [n for n in nodes if n]}, list(dict.fromkeys(c.pending)))  # the same fact can be asked for twice
