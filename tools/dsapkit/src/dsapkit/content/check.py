"""Checks on page copy: structure against the template, meta lengths, the primary keyword,
references to facts and pages, and how alike pages of one template are.

Severities: error (make content fails), warning (a draft that is not ready yet), held (a
paragraph or section waiting for a fact), unlinked (a link to a page that is not live yet).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import combinations

from ..site.model import Route, Site
from .model import Content, Layout, Page, Paragraph, Post, Section, SectionSpec
from .gates import section_waiting
from .syllabus import Syllabus
from .text import LINK_RE, PLACEHOLDER_RE, resolve
from .widgets import resolve_widget

WORD_RE = re.compile(r"[\w'ऀ-ॣ०-ॿ]+")  # \w alone splits Devanagari words at vowel signs
SECTION_PART_RE = re.compile(r"^([\w-]+)\.(?:body|points|questions)\[")  # a section's content, not its heading


@dataclass(frozen=True)
class Finding:
    severity: str
    where: str
    message: str


def _norm(text: str) -> str:
    return " ".join(WORD_RE.findall(text.lower().replace("-", " ")))


def _texts(section: Section) -> Iterator[tuple[str, Paragraph]]:
    if section.heading:
        yield "heading", Paragraph(section.heading)
    for i, p in enumerate(section.paragraphs):
        yield f"body[{i}]", p
    for i, p in enumerate(section.points):
        yield f"points[{i}]", p
    for i, q in enumerate(section.questions):  # a question shows only with its answer
        yield f"questions[{i}]", Paragraph(f"{q.question}\n{q.answer.text}", q.answer.requires)


def _page_texts(page: Page) -> Iterator[tuple[str, Paragraph]]:
    yield "meta.title", Paragraph(page.title)
    yield "meta.description", Paragraph(page.description)
    yield "h1", Paragraph(page.h1)
    for i, p in enumerate(page.intro):
        yield f"intro[{i}]", p
    for section in page.sections:
        for label, p in _texts(section):
            yield f"{section.id}.{label}", p


def _resolve_all(where: str, texts: Iterator[tuple[str, Paragraph]], site: Site, syllabus: Syllabus, locale: str,
                 gated: dict[str, list[str]]) -> list[Finding]:
    """Resolves every text. gated maps a section id to the pending gates holding that whole section.
    A section whose paragraphs, points and questions are all held back is hidden, and reported once."""
    out, held, parts = [], {}, {}
    for label, p in texts:
        r = resolve(p.text, site, p.requires, syllabus, locale)
        for ref in r.unknown:
            out.append(Finding("error", where, f"{label}: unknown or malformed reference {ref}"))
        for target in r.unlinked:
            out.append(Finding("unlinked", where, f"{label}: links to {target}, not live yet (shown as plain text)"))
        part = SECTION_PART_RE.match(label)
        if part:
            parts.setdefault(part.group(1), []).append(label)
        if r.pending:
            held[label] = r.pending
    for section_id, labels in parts.items():
        if section_id not in gated and all(label in held for label in labels):
            gated[section_id] = sorted({ref for label in labels for ref in held[label]})
    for label, pending in held.items():
        part = SECTION_PART_RE.match(label)
        if not (part and part.group(1) in gated):
            out.append(Finding("held", where, f"{label}: waits for {', '.join(pending)}"))
    for section_id, gates in gated.items():
        out.append(Finding("held", where, f"section {section_id} is hidden until {', '.join(gates)}"))
    return out


def _in_range(n: int, span: tuple[int, int]) -> bool:
    return span[0] <= n <= span[1]


def _check_section(section: Section, spec: SectionSpec | None, kind: str, content: Content,
                   site: Site, locale: str) -> list[str]:
    problems = []
    sid = section.id
    if spec and spec.shared:
        block = content.blocks.get((section.block or "", locale))
        if not section.block:
            problems.append(f"section {sid} is shared: point it to a block in blocks/{locale}")
        elif block is None:
            problems.append(f"section {sid}: no block {section.block!r} in blocks/{locale}")
        elif not block.heading:
            problems.append(f"block {section.block}: needs a heading")
        return problems
    if section.block:
        problems.append(f"section {sid}: only shared sections take a block")
    if not section.heading:
        problems.append(f"section {sid}: needs a heading")
    counts = {"paragraphs": len(section.paragraphs), "items": len(section.questions) if kind == "faq" else len(section.points)}
    if spec:
        if kind in ("prose", "list") and not _in_range(counts["paragraphs"], spec.paragraphs):
            problems.append(f"section {sid}: {counts['paragraphs']} paragraphs, template allows {spec.paragraphs[0]} to {spec.paragraphs[1]}")
        if kind in ("faq", "list") and not _in_range(counts["items"], spec.items):
            problems.append(f"section {sid}: {counts['items']} {'questions' if kind == 'faq' else 'points'}, "
                            f"template allows {spec.items[0]} to {spec.items[1]}")
    elif counts["paragraphs"] + counts["items"] == 0:
        problems.append(f"section {sid}: empty")
    if kind != "faq" and section.questions:
        problems.append(f"section {sid}: questions belong in a faq section")
    if kind != "list" and section.points:
        problems.append(f"section {sid}: points belong in a list section")
    if section.action:
        to = section.action.get("to")
        if to not in content.actions:
            problems.append(f"section {sid}: action to must be one of {sorted(content.actions)}")
        if to == "page" and section.action.get("page") not in site.routes:
            problems.append(f"section {sid}: action page {section.action.get('page')!r} is not a page")
        if not section.action.get("label"):
            problems.append(f"section {sid}: action needs a label")
    return problems


def _check_structure(page: Page, layout: Layout, content: Content, site: Site) -> tuple[list[str], dict[str, list[str]]]:
    """Problems with the page's shape, and the sections held back by their gates."""
    problems, gated = [], {}
    if not _in_range(len(page.intro), layout.intro):
        problems.append(f"intro has {len(page.intro)} paragraphs, template allows {layout.intro[0]} to {layout.intro[1]}")
    specs = {s.id: s for s in layout.sections}
    fixed = [s for s in page.sections if s.id in specs]
    free = [s for s in page.sections if s.id not in specs]
    if free and layout.free is None:
        problems.append(f"sections {[s.id for s in free]} are not in the template")
    if layout.free is not None:
        if not _in_range(len(free), (layout.free["min"], layout.free["max"])):
            problems.append(f"{len(free)} page sections, template allows {layout.free['min']} to {layout.free['max']}")
        if page.sections[:len(free)] != tuple(free):
            problems.append("page sections come before the template's fixed sections")
        for s in free:
            if s.kind not in layout.free["kinds"]:
                problems.append(f"section {s.id}: kind must be one of {layout.free['kinds']}")
            else:
                problems += _check_section(s, None, s.kind, content, site, page.locale)
    ids = [s.id for s in fixed]
    if len(set(ids)) != len(ids):
        problems.append("a section appears twice")
    expected = [s.id for s in layout.sections if s.id in ids or not s.optional]
    if ids != expected:
        problems.append(f"sections {ids} should be {expected} (in that order)")
    for s in fixed:
        spec = specs[s.id]
        if s.kind and s.kind != spec.kind:
            problems.append(f"section {s.id}: the template sets kind {spec.kind}")
        problems += _check_section(s, spec, spec.kind, content, site, page.locale)
        waiting, unknown = section_waiting(spec, content, site)
        problems += [f"templates.json: section {s.id} gates on {g}, which is not a fact or media slot" for g in unknown]
        if waiting:
            gated[s.id] = waiting
    return problems, gated


def _check_meta(page: Page, route: Route, content: Content, site: Site) -> list[tuple[str, str]]:
    """(severity, message) for meta lengths and the primary keyword."""
    out = []
    title = resolve(page.title, site, syllabus=content.syllabus, locale=page.locale).text or page.title
    description = resolve(page.description, site, syllabus=content.syllabus, locale=page.locale).text or page.description
    m = content.meta
    if not title or len(title) > m["titleMax"]:
        out.append(("error", f"meta.title is {len(title)} characters, keep 1 to {m['titleMax']}"))
    if not m["descriptionMin"] <= len(description) <= m["descriptionMax"]:
        out.append(("error", f"meta.description is {len(description)} characters, keep {m['descriptionMin']} to {m['descriptionMax']}"))
    if not page.h1:
        out.append(("error", "needs an h1"))
    keywords = route.keywords.get(page.locale)
    if keywords:
        primary = _norm(keywords.primary)
        if primary not in _norm(title) and primary not in _norm(page.h1):
            out.append(("error" if page.status == "ready" else "warning",
                        f"primary keyword {keywords.primary!r} is in neither the title nor the h1"))
    return out


def _own_words(page: Page) -> list[str]:
    """The page's own words: intro and inline sections, without shared blocks, references or headings."""
    texts = [p.text for p in page.intro]
    for s in page.sections:
        if not s.block:
            texts += [p.text for label, p in _texts(s) if label != "heading"]
    plain = LINK_RE.sub(r"\1", PLACEHOLDER_RE.sub(" ", " ".join(texts)))
    return WORD_RE.findall(plain.lower())


def _shingles(words: list[str], size: int) -> set[tuple[str, ...]]:
    return {tuple(words[i:i + size]) for i in range(len(words) - size + 1)}


def similarity(content: Content, site: Site) -> list[tuple[float, Page, Page]]:
    """Jaccard similarity of word shingles for every pair of pages that share a template and locale."""
    cfg = content.similarity
    groups: dict[tuple[str, str], list[Page]] = {}
    for (rid, loc), page in content.pages.items():
        route = site.routes.get(rid)
        if route and route.template in cfg["templates"]:
            groups.setdefault((route.template, loc), []).append(page)
    pairs = []
    for pages in groups.values():
        sets = {p.route: _shingles(_own_words(p), cfg["shingle"]) for p in pages}
        for a, b in combinations(pages, 2):
            union = sets[a.route] | sets[b.route]
            if union:
                pairs.append((len(sets[a.route] & sets[b.route]) / len(union), a, b))
    return sorted(pairs, key=lambda t: -t[0])


def _check_post(post: Post, route: Route, content: Content, site: Site) -> list[Finding]:
    where = f"{post.route} ({post.locale})"
    layout = content.layout(route.id, route.template)
    if layout is None or layout.markdown is None:
        return [Finding("error", where, f"template {route.template} does not take Markdown posts")]
    rules = layout.markdown
    strict = "error" if post.status == "ready" else "warning"
    found = []
    if route.planned:
        found.append(Finding("error", where, "packages/site/blog.json still says planned; set its status to written"))
    if post.locale not in route.locales:
        found.append(Finding("error", where, f"blog.json has no {post.locale} title for this post"))
    m = content.meta
    if not post.title or len(post.title) > m["titleMax"]:
        found.append(Finding("error", where, f"title is {len(post.title)} characters, keep 1 to {m['titleMax']}"))
    if not m["descriptionMin"] <= len(post.description) <= m["descriptionMax"]:
        found.append(Finding("error", where, f"description is {len(post.description)} characters, keep {m['descriptionMin']} to {m['descriptionMax']}"))
    if post.author not in site.facts:
        found.append(Finding("error", where, f"author {post.author!r} is not a fact in facts.json"))
    keywords = route.keywords.get(post.locale)
    h1 = route.names.get(post.locale, "")
    if keywords and _norm(keywords.primary) not in _norm(post.title) and _norm(keywords.primary) not in _norm(h1):
        found.append(Finding(strict, where, f"primary keyword {keywords.primary!r} is in neither the title nor the H1 in blog.json"))
    pending = []
    for fact_id in post.requires:
        _, why = site.fact_value(fact_id)
        if why and why.startswith("unknown"):
            found.append(Finding("error", where, f"requires unknown fact {fact_id}"))
        elif why:
            pending.append(fact_id)
    words, intro = 0, None
    for i, block in enumerate(post.blocks):
        if block.startswith("# "):
            found.append(Finding("error", where, f"block {i}: the H1 is the title in blog.json; start sections at ##"))
        r = resolve(block, site, syllabus=content.syllabus, locale=post.locale)
        found += [Finding("error", where, f"block {i}: unknown or malformed reference {ref}") for ref in r.unknown]
        found += [Finding("unlinked", where, f"block {i}: links to {t}, not live yet (shown as plain text)") for t in r.unlinked]
        pending += r.pending
        n = len(WORD_RE.findall(LINK_RE.sub(r"\1", PLACEHOLDER_RE.sub(" ", block))))
        words += n
        if intro is None and not block.startswith("#"):
            intro = n
    if pending:
        found.append(Finding("held", where, f"post waits for {', '.join(sorted(set(pending)))}"))
    if words < rules["minWords"]:
        found.append(Finding(strict, where, f"{words} words, a guide needs at least {rules['minWords']}"))
    if intro is not None and intro > rules["introMaxWords"]:
        found.append(Finding(strict, where, f"the opening paragraph is {intro} words; answer the question in {rules['introMaxWords']} or fewer"))
    for target in route.targets:
        if f"(page:{target})" not in post.body:
            found.append(Finding(strict, where, f"does not link to {target}, a page this guide supports"))
    return found


def check_content(content: Content, site: Site) -> list[Finding]:
    findings = []
    for (rid, loc), post in content.posts.items():
        route = site.routes.get(rid)
        if route is None or route.template != "post":
            findings.append(Finding("error", f"{rid} ({loc})", "no such post in packages/site/blog.json"))
            continue
        findings += _check_post(post, route, content, site)
    for (rid, loc), page in content.pages.items():
        where = f"{rid} ({loc})"
        route = site.routes.get(rid)
        if route is None:
            findings.append(Finding("error", where, "no such page in packages/site"))
            continue
        if loc not in route.locales:
            findings.append(Finding("error", where, f"the page has no {loc} version in packages/site"))
        layout = content.layout(rid, route.template)
        if layout is None:
            findings.append(Finding("error", where, f"templates.json has no layout for template {route.template}"))
            continue
        if layout.waits_for:
            findings.append(Finding("error", where, f"not written in this phase: {layout.waits_for}"))
            continue
        problems, gated = _check_structure(page, layout, content, site)
        findings += [Finding("error" if page.status == "ready" else "warning", where, p) for p in problems]
        findings += [Finding(sev, where, msg) for sev, msg in _check_meta(page, route, content, site)]
        findings += _resolve_all(where, _page_texts(page), site, content.syllabus, loc, gated)
    for (bid, loc), block in content.blocks.items():
        findings += _resolve_all(f"block {bid} ({loc})", _texts(block), site, content.syllabus, loc, {})
    findings += _check_widgets(content, site)
    limit = content.similarity["max"]
    for score, a, b in similarity(content, site):
        if score > limit:
            severity = "error" if a.status == b.status == "ready" else "warning"
            findings.append(Finding(severity, f"{a.route} and {b.route} ({a.locale})",
                                    f"{score:.0%} of their wording is shared, limit {limit:.0%}"))
    return findings


def _check_widgets(content: Content, site: Site) -> list[Finding]:
    """Every widget a template names exists in the default language and resolves; other languages may
    follow later, and until then their section shows its copy without the interactive part."""
    findings = []
    default = site.config["defaultLocale"]
    named = {spec.widget for layout in [*content.layouts.values(), *content.route_layouts.values()]
             for spec in layout.sections if spec.widget}
    for name in sorted(named):
        for loc in site.locales:
            if (name, loc) not in content.widgets:
                findings.append(Finding("error" if loc == default else "held", f"widget {name} ({loc})",
                                        "missing" if loc == default else "no version in this language yet; "
                                        "its section shows the copy without the interactive part"))
    for (name, loc), raw in content.widgets.items():
        where = f"widget {name} ({loc})"
        if name not in named:
            findings.append(Finding("error", where, "no template section names this widget"))
            continue
        result = resolve_widget(raw, site, content.syllabus, loc)
        findings += [Finding("error", where, f"{path}: unknown or malformed reference {ref}") for path, ref in result.unknown]
        findings += [Finding("held", where, f"{path}: waits for {', '.join(p)}") for path, p in result.held]
    return findings


def unwritten(content: Content, site: Site) -> list[tuple[Route, str, str | None]]:
    """(route, locale, waits_for) for every page version without copy; waits_for says why a later phase writes it, else None."""
    out = []
    for route in site.routes.values():
        if route.planned:
            continue
        layout = content.layout(route.id, route.template)
        for loc in route.locales:
            if (route.id, loc) not in content.pages and (route.id, loc) not in content.posts:
                out.append((route, loc, layout.waits_for if layout else None))
    return out
