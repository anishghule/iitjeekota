"""robots.txt and the sitemaps, written from data (packages/site/crawl.json) and the pages that were exported.

A sitemap lists only pages the site really builds, each with its hreflang alternates (every language
that page exists in, including itself, and x-default). lastmod is written only where the page's own
data says when it last changed: Google uses lastmod only if it is consistently accurate, and ignores
priority and changefreq, so those are never written.
"""

from __future__ import annotations

from typing import Any, Mapping
from xml.sax.saxutils import escape

from .formats import timestamp
from .links import alternates
from .model import Site

XML = '<?xml version="1.0" encoding="UTF-8"?>\n'
URLSET = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
SITEMAP_INDEX = "sitemap.xml"


def robots_txt(site: Site, crawl: Mapping[str, Any], indexing: bool) -> str:
    """Before launch nothing may be crawled; after it, the policy in crawl.json."""
    if not indexing:
        return "# Not launched yet: every page is also noindex.\nUser-agent: *\nDisallow: /\n"
    signal = ", ".join(f"{k}={v}" for k, v in crawl["contentSignal"].items())
    lines = ["User-agent: *", f"Content-Signal: {signal}", "Allow: /", *(f"Disallow: {path}" for path in crawl["disallow"])]
    for agent in crawl["blockedAgents"]:
        lines += ["", f"User-agent: {agent}", "Disallow: /"]
    lines += ["", f"Sitemap: {site.origin}/{SITEMAP_INDEX}"]
    return "\n".join(lines) + "\n"


def _lastmod(modified: str | None, dates: Mapping[str, str]) -> str:
    if not modified:
        return ""
    value = timestamp(modified, dict(dates)) if "T" in modified else modified
    return f"<lastmod>{value}</lastmod>"


def sitemap_files(site: Site, pages: set[tuple[str, str]], modified: Mapping[tuple[str, str], str | None]) -> dict[str, str]:
    """File name -> XML: one sitemap per language and an index over them."""
    files: dict[str, str] = {}
    for loc in site.locales:
        entries = []
        for route in site.routes.values():
            if (route.id, loc) not in pages:
                continue
            links = "".join(f'<xhtml:link rel="alternate" hreflang="{escape(code)}" href="{escape(url)}"/>'
                            for code, url in alternates(site, route).items()
                            if any(site.url(route.id, other) == url and (route.id, other) in pages for other in route.locales))
            entries.append(f"<url><loc>{escape(site.url(route.id, loc))}</loc>{_lastmod(modified.get((route.id, loc)), site.config['dates'])}{links}</url>")
        if entries:
            files[f"sitemap-{loc}.xml"] = XML + URLSET + "\n".join(entries) + "\n</urlset>\n"
    index = "".join(f"<sitemap><loc>{site.origin}/{name}</loc></sitemap>\n" for name in files)
    files[SITEMAP_INDEX] = XML + f'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{index}</sitemapindex>\n'
    return files
