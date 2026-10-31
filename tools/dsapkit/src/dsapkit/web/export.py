"""make web-data: writes everything apps/web renders, already resolved (docs/adr/0007-web-app.md).

The site shows exactly what make content approves: facts filled, held paragraphs and gated
sections left out, links only to live pages. Files go to apps/web/src/generated:
  data/site.json                      locales, routes, brand, contact links, centres, areas, facts
  data/pages/{locale}/{route}.json    each live page with copy
  data/syllabus/{locale}.json         the syllabus table
  data/area-map.json, data/media.json
  public/                             fonts, favicons, brand logos, the icon sprite, media files
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..content.gates import section_waiting
from ..content.model import Content, Paragraph, Section
from ..content.text import Resolved, resolve
from ..content.widgets import resolve_widget
from ..errors import BuildError
from ..images.info import media_size
from ..jsonio import GENERATED, read_json, reset_dir, write_bytes, write_json
from ..media.library import load_library
from ..paths import Paths
from ..site.jsonld import load_fixtures
from ..site.links import alternates, breadcrumbs
from ..site.model import Route, Site

SOURCE = "make web-data"


@dataclass
class WebExport:
    pages: list[tuple[str, str]] = field(default_factory=list)  # (route, locale)
    left_out: list[str] = field(default_factory=list)           # sections and widgets not shown, and why
    files: int = 0


def _header() -> dict[str, str]:
    return {"$generated": GENERATED.format(source=SOURCE)}


class _Pages:
    """Resolves page copy for one language into the shape the site renders."""

    def __init__(self, site: Site, content: Content, locale: str, report: WebExport) -> None:
        self.site, self.content, self.locale, self.report = site, content, locale, report

    def resolved(self, p: Paragraph) -> Resolved:
        return resolve(p.text, self.site, p.requires, self.content.syllabus, self.locale)

    def plain(self, text: str, where: str) -> str:
        r = self.resolved(Paragraph(text))
        if r.text is None:
            raise BuildError(f"web export {where}: {text!r} waits for {', '.join(r.pending + r.unknown)}")
        return r.text

    def rich(self, p: Paragraph) -> list[dict[str, str]] | None:
        r = self.resolved(p)
        if r.text is None:
            return None
        out = []
        for part in r.parts:
            route = self.site.routes.get(part.route or "")
            if route is not None and self.locale in route.locales:
                out.append({"text": part.text, "path": route.path(self.locale)})
            else:
                out.append({"text": part.text})
        return out

    def many(self, paragraphs: tuple[Paragraph, ...]) -> list[list[dict[str, str]]]:
        return [r for r in (self.rich(p) for p in paragraphs) if r is not None]

    def action(self, raw: dict[str, Any] | None) -> dict[str, str] | None:
        if not raw:
            return None
        out = {"to": raw["to"], "label": self.plain(raw["label"], "action")}
        if raw["to"] == "page":
            if not self.site.is_live(raw["page"]):
                return None
            out["path"] = self.site.routes[raw["page"]].path(self.locale)
        return out

    def section(self, section: Section, kind: str, spec_component: str | None, widget: str | None,
                where: str) -> dict[str, Any] | None:
        src = self.content.blocks[(section.block, self.locale)] if section.block else section
        heading = self.resolved(Paragraph(src.heading or ""))
        body, points = self.many(src.paragraphs), self.many(src.points)
        questions = []
        for q in src.questions:
            answer = self.rich(q.answer)
            question = self.resolved(Paragraph(q.question))
            if answer is not None and question.text is not None:
                questions.append({"q": question.text, "a": answer})
        if heading.text is None or not (body or points or questions):
            self.report.left_out.append(f"{where}: every paragraph waits for facts")
            return None
        out: dict[str, Any] = {"id": section.id, "kind": kind, "heading": heading.text, "body": body}
        if spec_component:
            out["component"] = spec_component
        if points:
            out["points"] = points
        if questions:
            out["questions"] = questions
        action = self.action(section.action or src.action)
        if action:
            out["action"] = action
        if widget:
            raw = self.content.widgets.get((widget, self.locale))
            result = resolve_widget(raw, self.site, self.content.syllabus, self.locale) if raw is not None else None
            if result is None or result.value is None or result.unknown:
                self.report.left_out.append(f"{where}: widget {widget} not shown in {self.locale}")
            else:
                out["widget"] = result.value
        return out

    def page(self, route: Route) -> dict[str, Any] | None:
        page = self.content.pages.get((route.id, self.locale))
        layout = self.content.layout(route.id, route.template)
        if page is None or layout is None or layout.waits_for or layout.markdown:
            return None
        where = f"{route.id} ({self.locale})"
        specs = {s.id: s for s in layout.sections}
        sections = []
        for section in page.sections:
            spec = specs.get(section.id)
            if spec:
                waiting, _ = section_waiting(spec, self.content, self.site)
                if waiting:
                    self.report.left_out.append(f"{where} {section.id}: waits for {', '.join(waiting)}")
                    continue
            kind = spec.kind if spec else (section.kind or "prose")
            out = self.section(section, kind, spec.component if spec else None, spec.widget if spec else None,
                               f"{where} {section.id}")
            if out:
                sections.append(out)
        return {
            "route": route.id, "locale": self.locale, "template": route.template, "status": page.status,
            "meta": {"title": self.plain(page.title, f"{where} title"),
                     "description": self.plain(page.description, f"{where} description")},
            "h1": self.plain(page.h1, f"{where} h1"),
            "intro": self.many(page.intro),
            "breadcrumbs": [{"name": c.name, "path": c.url.removeprefix(self.site.origin)}
                            for c in breadcrumbs(self.site, route, self.locale)],
            "sections": sections,
        }


def _localized_facts(site: Site, locale: str) -> dict[str, Any]:
    """Every confirmed fact as it reads in one language; a field still waiting for its translation is left out."""
    out: dict[str, Any] = {}
    for fact_id, fact in site.facts.items():
        if not fact.confirmed:
            continue
        if isinstance(fact.value, dict):
            fields = {}
            for name in fact.value:
                value, why = site.fact_value(fact_id, name, locale)
                if why is None:
                    fields[name] = value
            out[fact_id] = fields
        else:
            value, why = site.fact_value(fact_id, None, locale)
            if why is None:
                out[fact_id] = value
    return out


def _contact(site: Site) -> dict[str, Any]:
    links = site.config["contactLinks"]
    out: dict[str, Any] = {"links": {k: v for k, v in links.items() if not k.startswith("$")}}
    for key, pattern in (("phone", "tel"), ("whatsapp", "whatsapp")):
        number, why = site.fact_value(f"contact.{key}")
        if why is None:
            digits = "".join(ch for ch in number if ch.isdigit())
            out[key] = {"display": number, "digits": digits, "href": links[pattern].format(e164="+" + digits, digits=digits)}
    return out


def _centres(site: Site) -> list[dict[str, Any]]:
    out = []
    for cid, centre in site.centres.items():
        facts = centre["facts"]
        address, _ = site.fact_value(facts["address"])  # the NAP line, as on the Google Business Profile
        geo, _ = site.fact_value(facts["geo"])
        maps, _ = site.fact_value(facts["maps"])
        hours, _ = site.fact_value(facts["hours"])
        directions = site.config["contactLinks"]["directions"].format(**geo) if geo else None
        out.append({"id": cid, "role": centre["role"], "area": centre["area"], "names": centre["names"],
                    "places": centre["places"],
                    "address": address, "geo": geo, "maps": maps, "directions": directions, "hours": hours,
                    "page": next((r.id for r in site.routes.values() if r.centre == cid), None)})
    return out


def _areas(site: Site) -> list[dict[str, Any]]:
    out = []
    for aid, area in site.areas.items():
        route = next((r for r in site.routes.values() if r.area == aid), None)
        nearest = next((r for r in area["commute"]["routes"] if r["centre"] == area["nearestCentre"]), None)
        commute = None
        if area["commute"]["status"] == "confirmed" and nearest is not None:
            commute = {k: nearest[k] for k in ("km", "freeFlowMinutes", "minutes", "source") if k in nearest}
        out.append({"id": aid, "names": area["names"], "hub": area["hub"], "tier": area["tier"],
                    "nearestCentre": area["nearestCentre"], "localCentre": area["commute"].get("localCentre"),
                    "page": route.id if route else None, "commute": commute})
    return out


def _syllabus(content: Content, locale: str, default: str) -> dict[str, Any]:
    s = content.syllabus
    return {
        **_header(),
        "sources": {k: {f: v[f] for f in ("exam", "year", "publisher", "url") if f in v} for k, v in s.sources.items()},
        "subjects": [{"id": sid, "name": names.get(locale, names[default])} for sid, names in s.subjects.items()],
        "chapters": [{"id": c.id, "subject": c.subject, "symbol": c.symbol, "classes": list(c.classes),
                      "name": c.names.get(locale, c.names[default]), "main": c.main, "advanced": list(c.advanced),
                      "advancedOnly": c.advanced_only,
                      # topics are in English only so far; other languages show the chapter name alone
                      **({"topics": list(c.topics), "advancedAlso": list(c.advanced_also)} if locale == default else {})}
                     for c in s.chapters],
    }


def _hashed(data: bytes, stem: str, suffix: str) -> str:
    return f"{stem}.{hashlib.sha256(data).hexdigest()[:10]}{suffix}"


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _public(paths: Paths, public: Path) -> dict[str, Any]:
    """Copies static files; returns the URLs the data refers to."""
    for font in sorted(paths.fonts_dir.glob("*.woff2")):
        _copy(font, public / "fonts" / font.name)  # fonts.css (make tokens) loads /fonts/{name}
    favicons = paths.brand_dist / "favicon"
    if not favicons.is_dir():
        raise BuildError("packages/brand/dist/favicon is missing: run make brand")
    for f in sorted(favicons.iterdir()):
        _copy(f, public / f.name)  # site.webmanifest refers to the icons at the root
    spec = read_json(paths.favicons_json)
    ico = spec["ico"]
    head = [{"rel": "icon", "href": f"/{ico['name']}", "sizes": " ".join(f"{s}x{s}" for s in ico["sizes"])}]
    head += [{"rel": "icon", "type": "image/png", "href": f"/{i['name']}", "sizes": f"{i['size']}x{i['size']}"}
             for i in spec["transparent"] if i["name"] not in spec["manifest"]["icons"]]
    # A plate with a purpose is for the web manifest (maskable); the other plate is the home-screen icon.
    head += [{"rel": "apple-touch-icon", "href": f"/{p['name']}", "sizes": f"{p['size']}x{p['size']}"}
             for p in spec["plates"] if "purpose" not in p]
    head.append({"rel": "manifest", "href": f"/{spec['manifest']['name']}"})
    logos = {}
    for f in sorted((paths.brand_dist / "logo").glob("medal-*.png")):
        _copy(f, public / "brand" / f.name)  # fixed names: structured data names /brand/medal-512.png
        logos[f.stem.removeprefix("medal-")] = f"/brand/{f.name}"
    return {"logo": logos, "headLinks": head}


def _media(paths: Paths, public: Path) -> dict[str, Any]:
    out: dict[str, Any] = {**_header(), "slots": {}}
    for slot in load_library(paths).slots:
        entry: dict[str, Any] = {"kind": slot.kind, "origin": slot.origin, "alt": slot.alt, "decorative": slot.decorative,
                                 "placeholder": slot.placeholder}
        file = paths.root / slot.file
        if slot.origin != "awaited" and file.is_file():
            data = file.read_bytes()
            name = _hashed(data, slot.id, file.suffix)
            write_bytes(public / "media" / name, data)
            width, height = media_size(data)
            entry.update({"url": f"/media/{name}", "width": width, "height": height})
        out["slots"][slot.id] = entry
    return out


def export_web(paths: Paths, site: Site, content: Content, out_dir: Path | None = None) -> WebExport:
    """Writes to apps/web/src/generated, or to out_dir (tests)."""
    report = WebExport()
    out = reset_dir(out_dir or paths.web_generated)
    data, public = out / "data", out / "public"
    default = site.config["defaultLocale"]

    pages: dict[tuple[str, str], dict[str, Any]] = {}
    for loc in site.locales:
        builder = _Pages(site, content, loc, report)
        for route in site.routes.values():
            if not site.is_live(route.id) or loc not in route.locales:
                continue
            page = builder.page(route)
            if page is not None:
                pages[(route.id, loc)] = page
    fixtures = load_fixtures(paths.site / "jsonld", site)
    for (rid, loc), page in pages.items():
        route = site.routes[rid]
        exported = {site.url(rid, other) for other in route.locales if (rid, other) in pages}
        page["meta"]["canonical"] = site.url(rid, loc)
        page["meta"]["alternates"] = {code: url for code, url in alternates(site, route).items() if url in exported}
        page["jsonld"] = [fx.data for fx in fixtures if fx.route == rid and fx.locale == loc]
        write_json(data / "pages" / loc / f"{rid}.json", {**_header(), **page})
        report.pages.append((rid, loc))

    identity = read_json(paths.identity_json)
    statics = _public(paths, public)
    write_json(data / "site.json", {
        **_header(),
        "origin": site.origin, "defaultLocale": default, "locales": site.config["locales"],
        "root": {k: v for k, v in site.config["root"].items() if not k.startswith("$")},
        "brand": {"names": identity["localNames"], "shortName": identity["shortName"],
                  "parentSite": identity["parentSite"], **statics},
        "routes": {r.id: {"template": r.template, "pillar": r.pillar, "nav": r.nav, "live": site.is_live(r.id),
                          "names": r.names, "navNames": {**r.names, **r.nav_names},
                          "paths": {l: r.path(l) for l in r.locales if (r.id, l) in pages}}
                   for r in site.routes.values() if not r.planned},
        "contact": _contact(site),
        "centres": _centres(site),
        "areas": _areas(site),
        "facts": {loc: _localized_facts(site, loc) for loc in site.locales},
    })
    for loc in site.locales:
        write_json(data / "syllabus" / f"{loc}.json", _syllabus(content, loc, default))
    area_map = paths.map_dist / "area-map.json"
    if not area_map.exists():
        raise BuildError("packages/map/dist/area-map.json is missing: run make map")
    write_json(data / "area-map.json", read_json(area_map))
    write_json(data / "media.json", _media(paths, public))
    report.files = sum(1 for f in out.rglob("*") if f.is_file())
    return report
