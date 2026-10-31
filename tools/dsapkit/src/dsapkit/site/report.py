"""Outputs of make site: the resolved route table, sitemap previews and the generated SEO documents."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

from ..jsonio import GENERATED, reset_dir, write_json, write_text
from ..paths import Paths
from .jsonld import Finding, Fixture
from .keywords import planner_files
from .links import alternates, body_links, breadcrumbs, clicks_from_home, live_links
from .model import Route, Site
from .validate import commute_notes

HEADER = "<!-- " + GENERATED.format(source="packages/site via make site") + " -->\n\n"


def resolved(site: Site) -> dict:
    depth = clicks_from_home(site)
    pages = []
    for route in site.routes.values():
        pages.append({
            "id": route.id, "template": route.template, "pillar": route.pillar, "nav": route.nav,
            "live": site.is_live(route.id), "pendingGates": site.pending_gates(route),
            "clicksFromHome": depth.get(route.id),
            "links": live_links(site, route),
            "locales": {
                loc: {
                    "path": route.path(loc), "url": site.url(route.id, loc), "name": route.names[loc],
                    "breadcrumbs": [{"name": c.name, "url": c.url} for c in breadcrumbs(site, route, loc)],
                    "keywords": ({"primary": route.keywords[loc].primary, "secondary": list(route.keywords[loc].secondary),
                                  "draft": route.keywords[loc].draft} if loc in route.keywords else None),
                } for loc in route.locales
            },
            "alternates": alternates(site, route),
        })
    return {"$generated": GENERATED.format(source="packages/site"), "origin": site.origin,
            "root": site.config["root"]["redirectTo"], "pages": pages}


def sitemaps(site: Site, out: Path) -> list[Path]:
    """One sitemap per locale with hreflang alternates, and an index. Live pages only."""
    written = []
    for loc in site.locales:
        entries = []
        for route in site.routes.values():
            if loc not in route.locales or not site.is_live(route.id):
                continue
            alts = "".join(f'<xhtml:link rel="alternate" hreflang="{escape(code)}" href="{escape(url)}"/>'
                           for code, url in alternates(site, route).items())
            entries.append(f"<url><loc>{escape(site.url(route.id, loc))}</loc>{alts}</url>")
        path = out / f"sitemap-{loc}.xml"
        write_text(path, '<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
                   + "\n".join(entries) + "\n</urlset>\n")
        written.append(path)
    index = "".join(f"<sitemap><loc>{site.origin}/sitemap-{loc}.xml</loc></sitemap>\n" for loc in site.locales)
    write_text(out / "sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
               f'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{index}</sitemapindex>\n')
    return written + [out / "sitemap.xml"]


def _md_row(cells: list[str]) -> str:
    return "| " + " | ".join(c.replace("|", "/") for c in cells) + " |"


def _volume(site: Site, keyword: str) -> str:
    row = site.volume(keyword)
    if row is None:
        return "not checked"
    if row["monthly"] is None:
        return "no data"
    low, high = row["monthly"]
    return f"{low} to {high}"


def _status(site: Site, route: Route) -> str:
    if route.planned:
        return "Planned for Phase 4"
    pending = site.pending_gates(route)
    return "Ready" if not pending else "Waits for " + ", ".join(f"`{g}`" for g in pending)


def site_map_doc(site: Site) -> str:
    live = [r for r in site.routes.values() if site.is_live(r.id)]
    by_template = Counter(r.template for r in site.routes.values())
    lines = [HEADER + "# Site map and keywords", "",
             f"{len(site.routes)} pages per language. {len(live)} are ready to build now; the rest wait for facts in `packages/site/facts.json` "
             "or are planned posts. "
             f"Languages: {', '.join(site.locales)}. Every URL is `{site.origin}/{{language}}/{{page}}/`; the root `/` redirects to `{site.config['root']['redirectTo']}`.",
             "", "Pages by type: " + ", ".join(f"{t} {n}" for t, n in sorted(by_template.items())) + ".", "",
             "## Structure", "",
             "Breadcrumbs never go deeper than Home, a pillar, then the page. Only pillars appear as the middle crumb.", ""]
    home = next(r for r in site.routes.values() if r.template == "home")
    lines.append(f"- **{home.names['en']}** `{home.path('en')}`")
    for pillar in site.pillars():
        lines.append(f"  - **{pillar.names['en']}** `{pillar.path('en')}` ({_status(site, pillar)})")
        for child in (r for r in site.routes.values() if r.pillar == pillar.id):
            tier = f", tier {child.tier}" if child.tier else ""
            allow = f" <!-- copy-lint-allow: {', '.join(child.allow)} -->" if child.allow else ""
            lines.append(f"    - {child.names['en']} `{child.path('en')}`{tier} ({_status(site, child)}){allow}")
    for route in site.routes.values():
        if route.template in ("page", "legal"):
            lines.append(f"  - {route.names['en']} `{route.path('en')}` ({_status(site, route)})")

    lines += ["", "## Keyword map", "",
              "One primary keyword per page and language; no page targets another page's primary. Hindi and Marathi are drafts until native keyword research. "
              "Search volumes are not shown: pull them from Google Keyword Planner and, after launch, Search Console.", "",
              _md_row(["Page", "English primary", "Monthly searches", "English secondary", "Hindi primary", "Marathi primary"]),
              _md_row(["---"] * 6)]
    for route in site.routes.values():
        if not route.keywords:
            continue
        kw = route.keywords
        allow = f" <!-- copy-lint-allow: {', '.join(route.allow)} -->" if route.allow else ""
        lines.append(_md_row([f"`{route.path('en')}`", kw["en"].primary if "en" in kw else "",
                              _volume(site, kw["en"].primary) if "en" in kw else "",
                              ", ".join(kw["en"].secondary) if "en" in kw else "",
                              kw["hi"].primary if "hi" in kw else "", kw["mr"].primary if "mr" in kw else ""]) + allow)

    if site.volumes:
        owners = {" ".join(k.lower().split()): (route.id, loc, role)
                  for route in site.routes.values() for loc, kws in route.keywords.items()
                  for k, role in [(kws.primary, "primary"), *((s, "secondary") for s in kws.secondary)]}
        lines += ["", "## Volumes from Keyword Planner", "",
                  "Google's ranges of average monthly searches for the location set in D-SAP's account. "
                  "A keyword with no data has too few searches for Google to report.", "",
                  "<!-- copy-lint-disable: searchers' queries and Google's figures, quoted as they come -->",
                  _md_row(["Keyword", "Monthly searches", "3-month change", "Yearly change", "Competition", "Page", "Role"]),
                  _md_row(["---"] * 7)]
        for key, row in site.volumes.items():
            page, _, role = owners.get(key, ("not in the map", "", ""))
            lines.append(_md_row([row["keyword"], _volume(site, key), row["threeMonthChange"] or "", row["yearChange"] or "",
                                  row["competition"] or "", page, role]))
        lines.append("<!-- copy-lint-enable -->")
        sources = [f"{i['source']}, {i['date']}. {i['note']}" for i in site.volume_imports]
        lines += ["", "Imports:", ""] + [f"- {s}" for s in sources]

    centre_names = {cid: c["names"]["en"] for cid, c in site.centres.items()}
    cfg = site.config["commute"]
    arrive_by, _ = site.fact_value(cfg["fact"], cfg["arriveBy"])
    lines += ["", "## Commutes", "",
              f"Area pages give the trip to the centre for a student arriving by {arrive_by} "
              f"(fact `{cfg['fact']}`). An area page stays unpublished while its commute is a placeholder. "
              "D-SAP checks each route, corrects `km` and `minutes` in `packages/site/areas.json` where needed, "
              "and sets `status` to `confirmed`.", "",
              _md_row(["Area", "Nearest centre", "Status", "Routes"]), _md_row(["---"] * 4)]
    for area in site.areas.values():
        commute = area["commute"]
        routes = []
        if commute.get("localCentre"):
            routes.append(f"centre is in {area['names']['en']}")
        for r in commute["routes"]:
            time = (f"{r['minutes'][0]} to {r['minutes'][1]} min" if "minutes" in r
                    else f"{r['freeFlowMinutes']} min on empty roads" if "freeFlowMinutes" in r else "time not known")
            routes.append(f"{centre_names[r['centre']]}: {r['km']} km, {time} ({r['source']})")
        status = commute["status"] + (f" ({commute['checked']})" if commute.get("checked") else "")
        lines.append(_md_row([area["names"]["en"], centre_names[area["nearestCentre"]], status, "; ".join(routes)]))
    notes = commute_notes(site)
    if notes:
        lines += ["", "To review when checking:", ""] + [f"- {n}" for n in notes]
    lines += ["", "Sources:", ""] + [f"- `{k}`: {v}" for k, v in site.config["commuteSources"].items()]

    linking = site.config["linking"]
    lines += ["", "## Internal links", "",
              "Links come from the rules in `site.json`. Every pillar links all its pages. "
              f"Each area page links its pillar, its nearest centre, {linking['spokeNeighbours']} neighbouring areas, "
              f"Powered by Kota and {linking['spokeProgrammes']} programme pages. "
              f"The footer carries these groups: {', '.join(linking['footer'])}. Links to pages that are not live yet are held back.", "",
              _md_row(["Page", "Body links", "Clicks from home"]), _md_row(["---"] * 3)]
    depth = clicks_from_home(site)
    for route in live:
        lines.append(_md_row([f"`{route.path('en')}`", str(len([t for t in body_links(site, route) if site.is_live(t)])),
                              str(depth.get(route.id, "not reachable"))]))
    return "\n".join(lines) + "\n"


def structured_data_doc(rules: dict, fixtures: list[Fixture], findings: list[Finding]) -> str:
    lines = [HEADER + "# Structured data", "",
             f"Rules checked against Google's documentation on {rules['checked']}. Fixtures in `packages/site/jsonld/` are the expected JSON-LD "
             "of each page template; the web build must produce the same output.", "",
             "## Types in use", "", _md_row(["Type", "Required", "Recommended", "Google docs updated", "Note"]), _md_row(["---"] * 5)]
    for name, rule in rules["types"].items():
        if "sameAs" in rule:
            lines.append(_md_row([name, f"as {rule['sameAs']}", "", "", ""]))
            continue
        docs = f"[{rule['updated']}]({rule['docs']})" if "docs" in rule else ""
        lines.append(_md_row([name, ", ".join(rule.get("required", [])) or "none", ", ".join(rule.get("recommended", [])), docs, rule.get("note", "")]))
    lines += ["", "## Not used", ""] + [f"- **{k}**: {v}" for k, v in rules["retired"].items()]
    lines += ["", "## Fixture results", ""]
    for fx in fixtures:
        own = [f for f in findings if f.fixture == fx.name]
        lines.append(f"### {fx.name} (`{fx.route}`, {fx.locale})")
        lines.append("")
        lines += [f"- {f.severity}: {f.message}" for f in own] or ["- Passes with nothing pending."]
        lines.append("")
    return "\n".join(lines)


def citations_doc(site: Site) -> str:
    c = site.citations
    lines = [HEADER + "# Listings, aggregators and citations", "",
             "Every listing uses these NAP lines exactly, matching each Google Business Profile character for character.", ""]
    for centre in site.centres.values():
        facts = {k: site.facts[v] for k, v in centre["facts"].items() if v in site.facts}
        phone = facts["phone"].value if facts["phone"].confirmed else "pending (`contact.phone`)"
        lines += [f"- **{centre['names']['en']}**: {facts['address'].value}. Phone: {phone}."]
    lines += ["", "## Directories and maps", "", _md_row(["Priority", "Platform", "Competitors seen", "Action"]), _md_row(["---"] * 4)]
    for p in sorted(c["listings"]["platforms"], key=lambda p: p["priority"]):
        lines.append(_md_row([str(p["priority"]), f"[{p['name']}]({p['url']})", ", ".join(p.get("seen", [])), p["action"]]))
    lines += ["", "## Education aggregators", "", c["aggregators"]["$description"], "",
              _md_row(["Priority", "Platform", "Pages", "Competitors seen", "Action"]), _md_row(["---"] * 5)]
    for p in sorted(c["aggregators"]["platforms"], key=lambda p: p["priority"]):
        pages = " ".join(f"[page {i + 1}]({u})" for i, u in enumerate(p.get("urls", [])))
        lines.append(_md_row([str(p["priority"]), p["name"], pages, ", ".join(p.get("seen", [])), p["action"]]))
    lines += ["", "## Ranked lists", "", c["listicles"]["$description"], "", _md_row(["Page", "Owner", "Competitors seen", "Action"]), _md_row(["---"] * 4)]
    for p in c["listicles"]["pages"]:
        lines.append(_md_row([f"[link]({p['url']})", p["owner"], ", ".join(p.get("seen", [])), p["action"]]))
    press = c["press"]
    gate = ", ".join(f"`{g}`" for g in press["gates"])
    lines += ["", "## Press releases", "", press["$description"], "", f"Waits for {gate}.", ""]
    lines += [f"- Example: [{u}]({u})" for u in press["examples"]]
    lines += ["", "## Community answers", "", c["community"]["$description"], ""] + [f"- {p}" for p in c["community"]["platforms"]]
    return "\n".join(lines) + "\n"


def write_reports(paths: Paths, site: Site, rules: dict, fixtures: list[Fixture], findings: list[Finding]) -> list[Path]:
    out = reset_dir(paths.site_dist)
    write_json(out / "routes.resolved.json", resolved(site))
    written = [out / "routes.resolved.json"] + sitemaps(site, out)
    for name, text in planner_files(site).items():
        write_text(out / "keyword-planner" / name, text)
        written.append(out / "keyword-planner" / name)
    docs = {"site-map.md": site_map_doc(site), "structured-data.md": structured_data_doc(rules, fixtures, findings),
            "listings-and-citations.md": citations_doc(site)}
    for name, text in docs.items():
        write_text(paths.seo_docs / name, text)
        written.append(paths.seo_docs / name)
    return written
