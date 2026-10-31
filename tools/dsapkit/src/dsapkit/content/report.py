"""docs/content/status.md: which pages have copy in which language, and what is held back."""

from __future__ import annotations

from pathlib import Path

from ..jsonio import GENERATED, write_text
from ..paths import Paths
from ..site.model import Site
from .check import Finding, similarity, unwritten
from .model import Content

HEADER = "<!-- " + GENERATED.format(source="packages/content via make content") + " -->\n\n"


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |"


def write_status(paths: Paths, content: Content, site: Site, findings: list[Finding]) -> Path:
    missing = {(r.id, loc): why for r, loc, why in unwritten(content, site)}
    lines = [HEADER + "# Content status", "",
             "Copy lives in `packages/content/pages/{locale}/{page}.json`, guides in `packages/content/posts/{locale}/{post}.md` "
             "(docs/adr/0005-content-format.md). "
             "A language version publishes when the page is live in `packages/site` and its copy is ready. "
             "Hindi and Marathi stay draft until the language experts proofread them at release.", ""]
    for loc in site.locales:
        versions = [r for r in site.routes.values() if not r.planned and loc in r.locales]
        statuses = [c.status for r in versions if (c := content.copy(r.id, loc))]
        lines.append(f"- {loc}: {statuses.count('ready')} ready, {statuses.count('draft')} draft, "
                     f"{sum(1 for r in versions if (r.id, loc) in missing)} without copy")
    lines += ["", "## Pages", "", _row(["Page", "Live", *site.locales]), _row(["---"] * (2 + len(site.locales)))]
    for route in site.routes.values():
        if route.planned:
            continue
        cells = []
        for loc in site.locales:
            written = content.copy(route.id, loc)
            cells.append(written.status if written else "waits" if missing.get((route.id, loc)) else "not written")
        lines.append(_row([f"`{route.path('en')}`", "yes" if site.is_live(route.id) else "no", *cells]))
    waits = sorted({why for why in missing.values() if why})
    if waits:
        lines += ["", "Waits:", ""] + [f"- {w}" for w in waits]
    for title, severity, intro in (
            ("Held back", "held", "Paragraphs and sections that show once their facts are confirmed in `packages/site/facts.json`."),
            ("Links to pages not live yet", "unlinked", "These anchors show as plain text until the page goes live."),
            ("Warnings", "warning", "Draft pages that would fail the checks if marked ready.")):
        group = [f for f in findings if f.severity == severity]
        if group:
            lines += ["", f"## {title}", "", intro, ""] + [f"- {f.where}: {f.message}" for f in group]
    pairs = similarity(content, site)
    if pairs:
        limit = content.similarity["max"]
        lines += ["", "## Most alike pages", "",
                  f"Share of {content.similarity['shingle']}-word runs two pages have in common, for "
                  f"{', '.join(content.similarity['templates'])} pages. The limit is {limit:.0%}.", "",
                  _row(["Pages", "Language", "Shared"]), _row(["---"] * 3)]
        lines += [_row([f"{a.route}, {b.route}", a.locale, f"{score:.0%}"]) for score, a, b in pairs[:10]]
    target = paths.content_docs / "status.md"
    write_text(target, "\n".join(lines) + "\n")
    return target
