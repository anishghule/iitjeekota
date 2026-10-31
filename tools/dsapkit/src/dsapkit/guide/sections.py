"""HTML for each section of the brand guide. Every value shown is read from the build inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..brand.svg import escape as e
from ..copylint.lint import lint_text
from ..copylint.rules import VoiceRules
from ..icons.build import Icon
from ..media.library import Slot
from ..tokens import TokenSet
from ..tokens.contrast import ContrastResult
from ..tokens.css import fluid

SAMPLE = {
    "display-xl": "IIT JEE coaching, powered by Kota",
    "display": "Two years, planned week by week",
    "h1": "IIT JEE coaching in Wakad",
    "h2": "How the weekly test works",
    "body-lg": "Every Sunday your child writes a test. On Monday you see what went right and what to fix next.",
    "body": "Physics, Chemistry and Mathematics are taught in the same week, so no subject falls behind while another races ahead.",
    "small": "Fees include printed modules and the test series. Ask at the centre for the next batch dates.",
}
SAMPLE_DEVANAGARI = {
    "hi": {"display": "पुणे में IIT JEE कोचिंग, कोटा के साथ",
           "body": "भौतिकी, रसायन और गणित एक ही हफ्ते में पढ़ाए जाते हैं, ताकि कोई विषय पीछे न रहे।"},
    "mr": {"display": "पुण्यात IIT JEE कोचिंग, कोटाच्या साथीने",
           "body": "भौतिकशास्त्र, रसायनशास्त्र आणि गणित एकाच आठवड्यात शिकवले जातात, त्यामुळे कोणताही विषय मागे पडत नाही."},
}
LOCALE_NAMES = {"en": "English", "hi": "Hindi", "mr": "Marathi"}


@dataclass(frozen=True)
class GuideData:
    tokens: TokenSet
    contrast: list[ContrastResult]
    metrics: dict[str, Any]
    icons: list[Icon]
    voice: VoiceRules
    banned: dict[str, list[dict[str, str]]]
    claims: dict[str, list[str]]
    identity: dict[str, Any]
    media: list[Slot]
    og_locales: list[str]
    favicons: dict[str, Any]
    logo_sizes: list[int]


def section(sid: str, title: str, intro: str, body: str) -> str:
    return (f'<section id="{sid}" aria-labelledby="{sid}-title">\n<header><h2 id="{sid}-title" class="t-display">{e(title)}</h2>\n'
            f'<p class="t-body-lg">{intro}</p></header>\n{body}\n</section>\n')


def table(head: list[str], rows: list[list[str]], numeric: frozenset[int] = frozenset()) -> str:
    th = "".join(f'<th scope="col"{" class=num" if i in numeric else ""}>{e(h)}</th>' for i, h in enumerate(head))
    body = "\n".join("<tr>" + "".join(f'<td{" class=num" if i in numeric else ""}>{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'\n<div class="table-wrap"><table><thead><tr>{th}</tr></thead><tbody>\n{body}\n</tbody></table></div>\n'


def chip(value: str) -> str:
    return f'<span class="chip" style="background:{e(value)}"></span><code>{e(value)}</code>'


# ------------------------------------------------------------------ sections


def logo(d: GuideData) -> str:
    slot = next(s for s in d.media if s.id == "brand/logo-medal")
    materials = d.tokens.tree["material"]
    rows = [[f"<code>material.{e(name)}</code>",
             " ".join(f"{e(k)} <b>{e(str(v))}</b>" for k, v in spec.items() if k != "color"),
             chip(spec["color"]), e(d.tokens.descriptions.get(f"material.{name}", ""))]
            for name, spec in materials.items() if name.startswith("medal-")]
    sizes = "".join(f'<figure><img src="assets/logo/medal-{s}.png" width="{min(s, 160)}" height="{min(s, 160)}" alt="">'
                    f"<figcaption>{s} px</figcaption></figure>" for s in d.logo_sizes if s <= 256)
    favs = "".join(f'<figure><img src="assets/favicon/{f["name"]}" width="{f["size"]}" height="{f["size"]}" alt="">'
                   f'<figcaption>{f["size"]} px</figcaption></figure>' for f in d.favicons["transparent"] if f["size"] <= 32)
    body = (
        '<div class="surface-pair">'
        f'<div data-surface="ink"><div class="logo-stage"><img src="assets/logo/medal-512.png" width="512" height="512" alt="{e(slot.alt.get("en", ""))}"></div>'
        '<p class="note">On ink, the page colour of the site.</p></div>'
        '<div data-surface="chalk"><div class="logo-stage"><img src="assets/logo/medal-512.png" width="512" height="512" alt=""></div>'
        '<p class="note">On chalk, for light sections, documents and print.</p></div></div>'
        f'<div class="size-row">{sizes}{favs}</div>'
        '<ul class="rules">'
        '<li>The logo is the official D-SAP medal, media slot <code>brand/logo-medal</code>, pulled from dsapghuletutorials.com and pinned by hash. It is never redrawn or recoloured.</li>'
        '<li>The build finds the medal inside the image from its transparency and centres it, so every size, favicon and OG image shares one crop.</li>'
        '<li>Leave clear space of a quarter of the medal\'s width around it. Smallest size on screen: 32 px, except the browser tab icon.</li>'
        '<li>On the site the medal also appears in 3D as struck metal. The same image is the face texture, and a normal map gives it relief. '
        'The materials below set the finish. This follows the v3.2 medal (scene.js) and is built in Phase 5.</li>'
        "</ul>"
        + table(["Material", "Settings", "Colour", "Use"], rows)
    )
    return section("logo", "Logo", "One medal, used as it is. The 3D version adds light and metal, not a new drawing.", body)


def colour(d: GuideData) -> str:
    families = []
    for family, steps in d.tokens.tree["color"].items():
        desc = d.tokens.descriptions.get(f"color.{family}", "")
        cells = "".join(f'<figure class="swatch"><span style="background:{e(v)}"></span><figcaption><b>{e(family)} {e(step)}</b>'
                        f'<code>{e(v)}</code></figcaption></figure>' for step, v in steps.items())
        families.append(f'<div class="stack"><h3 class="t-h2">{e(family.capitalize())}</h3>'
                        + (f'<p class="note">{e(desc)}</p>' if desc else "") + f'<div class="swatches">{cells}</div></div>')
    surfaces = d.tokens.tree["surface"]
    names = list(surfaces)
    roles = list(surfaces[names[0]])
    rows = [[f"<code>--{e(role)}</code>"] + [chip(surfaces[s][role]) for s in names] for role in roles]
    body = "".join(families) + '<div class="stack"><h3 class="t-h2">Surface roles</h3>' \
        '<p class="note">Components only use these roles. A section sets <code>data-surface</code> and every role follows.</p>' \
        + table(["Role"] + [s.capitalize() for s in names], rows) + "</div>"
    return section("colour", "Colour", "Kota stone greys, brass from the medal, chalk for light pages. River blue is kept for the map.", body)


def contrast(d: GuideData) -> str:
    rows = [[e(r.surface), f"<code>{e(r.fg)}</code>", f"<code>{e(r.bg)}</code>",
             f"{r.ratio:.2f}:1", f"{e(r.level)} {r.minimum:g}:1",
             f'<span class="pill {"pass" if r.passed else "fail"}">{"Pass" if r.passed else "Fail"}</span>', e(r.use)]
            for r in d.contrast]
    passed = sum(r.passed for r in d.contrast)
    return section("contrast", "Contrast",
                   f"{passed} of {len(d.contrast)} pairs pass. The token build stops if any pair falls below its minimum.",
                   table(["Surface", "Text or mark", "On", "Ratio", "Needs", "Result", "Use"], rows, {3}))


def depth(d: GuideData) -> str:
    def panel(surface: str) -> str:
        levels = "".join(f'<div style="box-shadow:var(--shadow-{n})">Level {n}</div>' for n in d.tokens.tree["shadow"][surface])
        return (f'<div data-surface="{surface}"><h3 class="t-h2">{surface.capitalize()}</h3>'
                '<p class="t-body">Three subjects, one weekly plan.</p><p class="t-small" style="color:var(--text-muted)">Muted text for dates and notes.</p>'
                '<div><span class="big-number">3</span> <span class="t-body-lg">subjects</span></div>'
                f'<div class="depth">{levels}</div>'
                f'<label class="field" for="field-{surface}"><span class="t-small">Parent phone</span>'
                f'<input id="field-{surface}" inputmode="tel" value="98765 43210"></label>'
                '<div><button class="button" type="button">Book a demo class '
                '<svg class="icon icon--md" aria-hidden="true"><use href="#i-arrow-right"></use></svg></button></div></div>')
    return section("depth", "Surfaces and depth",
                   "Depth comes from light and shadow. Cards never get outlines; only form fields carry a stroke, because they must.",
                   f'<div class="surface-pair">{panel("ink")}{panel("chalk")}</div>')


def type_(d: GuideData) -> str:
    tree = d.tokens.tree
    vmin, vmax = tree["type"]["viewport"]["min"], tree["type"]["viewport"]["max"]
    specimens = []
    for variant, spec in tree["type"]["scale"].items():
        family = tree["font"]["family"][spec["family"]][0]
        meta = (f"<code>.t-{e(variant)}</code> {family} {spec['weight']}, {spec['min']} to {spec['max']} px "
                f"({vmin} to {vmax} px screens), line height {spec['lineHeight']}, tracking {spec['tracking']} em")
        specimens.append(f'<div class="specimen"><p class="t-{e(variant)}">{e(SAMPLE[variant])}</p><p class="spec">{meta}</p></div>')
    deva = tree["type"]["devanagari"]
    deva_rows = []
    for loc in deva["locales"]:
        sample = SAMPLE_DEVANAGARI.get(loc)
        if not sample:
            continue
        deva_rows.append(f'<div class="specimen" lang="{loc}"><p class="t-display">{e(sample["display"])}</p>'
                         f'<p class="t-body">{e(sample["body"])}</p>'
                         f'<p class="spec" lang="en">{LOCALE_NAMES.get(loc, loc)}, Mukta. Draft text for type testing; native review in Phase 4.</p></div>')
    size_adjust = d.metrics["sizeAdjust"]
    fallbacks = d.metrics["fallbacks"]
    fb_rows = [[e(fb["family"]), e(", ".join(fb["local"][:2])), f"{fb['sizeAdjust']}%", f"{fb['ascentOverride']}%",
                f"{fb['descentOverride']}%"] for fb in fallbacks.values()]
    sa = "".join(f"<li>{e(role.capitalize())} is set {v['value']}% larger so its x-height matches {e(v['matches'])} text.</li>"
                 for role, v in size_adjust.items())
    option_a = (f'<div class="option panel"><h3 class="t-h2">A. Archivo and Mukta <span class="chosen">Chosen</span></h3>'
                f'<p class="t-display">{e(SAMPLE["display-xl"])}</p>'
                f'<p class="t-display" lang="hi">{e(SAMPLE_DEVANAGARI["hi"]["display"])}</p>'
                f'<p class="t-display" lang="mr">{e(SAMPLE_DEVANAGARI["mr"]["display"])}</p></div>')
    option_b = (f'<div class="option panel"><h3 class="t-h2">B. Zilla Slab and Martel</h3>'
                f'<p class="t-display slab-latin">{e(SAMPLE["display-xl"])}</p>'
                f'<p class="t-display slab-deva" lang="hi">{e(SAMPLE_DEVANAGARI["hi"]["display"])}</p>'
                f'<p class="t-display slab-deva" lang="mr">{e(SAMPLE_DEVANAGARI["mr"]["display"])}</p></div>')
    body = (
        '<div class="stack">' + "".join(specimens) + "</div>"
        '<div class="stack"><h3 class="t-h2">Hindi and Marathi</h3>'
        '<p class="note">Same variants, set in Mukta: taller lines for the vowel signs and no letter-spacing, so the headline stroke stays joined.</p>'
        + "".join(deva_rows) + "</div>"
        '<div class="stack"><h3 class="t-h2">Display face test</h3>'
        '<p class="note">The same headline in both options and all three languages. A is chosen: Archivo\'s wide, heavy cut stays clear on a phone and sits well beside the 3D medal; '
        "Mukta matches its weight in Devanagari. B echoes the medal's slab lettering but reads like print and competes with the medal itself. "
        "Recorded in docs/adr/0003-display-typeface.md.</p>"
        f'<div class="options">{option_a}{option_b}</div></div>'
        '<div class="stack"><h3 class="t-h2">Fallbacks and size matching</h3>'
        '<p class="note">While a web font loads, a local font stands in with these overrides, so the page does not jump when the real font arrives.</p>'
        + table(["Fallback face", "Uses", "Size adjust", "Ascent", "Descent"], fb_rows, {2, 3, 4})
        + f'<ul class="rules">{sa}</ul></div>'
    )
    return section("type", "Type", "Archivo for headlines, Inter for reading, Mukta for Hindi and Marathi. Sentence case, no labels above headings.", body)


def space(d: GuideData) -> str:
    tree = d.tokens.tree
    vmin, vmax = tree["type"]["viewport"]["min"], tree["type"]["viewport"]["max"]
    bars = "".join(f'<div class="bar"><code>--space-{e(k)}</code><span style="width:{v}px"></span></div>'
                   for k, v in tree["space"].items() if k != "fluid")
    fluid_rows = [[f"<code>--space-{e(k)}</code>", f"{v['min']} to {v['max']} px", f"<code>{e(fluid(v['min'], v['max'], vmin, vmax))}</code>",
                   e(d.tokens.descriptions.get(f"space.fluid.{k}", ""))] for k, v in tree["space"]["fluid"].items()]
    radii = "".join(f'<figure><span style="border-radius:{"9999px" if v >= 9999 else f"{v}px"}"></span><figcaption>{e(k)}</figcaption></figure>'
                    for k, v in tree["radius"].items())
    layout_rows = [[f"<code>{e(k)}</code>", e(str(v))] for k, v in tree["layout"].items()]
    layout_rows += [[f"<code>breakpoint.{e(k)}</code>", f"{v} px"] for k, v in tree["breakpoint"].items()]
    body = (f'<div class="bars">{bars}</div>' + table(["Fluid space", "Range", "CSS", "Use"], fluid_rows)
            + '<div class="stack"><h3 class="t-h2">Radius</h3><p class="note">Radius marks what a thing is, not every box. Buttons are round, panels large, inputs medium.</p>'
            f'<div class="radii">{radii}</div></div>' + table(["Layout", "Value"], layout_rows))
    return section("space", "Space and shape", "A 4 px scale for parts of a component and fluid space between sections.", body)


def icons(d: GuideData) -> str:
    cells = "".join(f'<figure><svg class="icon" aria-hidden="true"><use href="#i-{e(i.name)}"></use></svg>'
                    f"<figcaption><b>{e(i.name)}</b><span>{e(i.meaning)}</span></figcaption></figure>" for i in d.icons)
    rules = ('<ul class="rules"><li>24 px grid, 1.75 stroke, round ends and joins. One brass accent stroke per icon.</li>'
             "<li>Icons take the text colour; the accent follows the surface. Never place an icon inside a coloured circle.</li>"
             "<li>No emoji and no mixed icon packs. WhatsApp buttons use the chat icon with the word WhatsApp; the WhatsApp logo is not redrawn.</li></ul>")
    return section("icons", "Icons", f"{len(d.icons)} icons drawn for this site. Add one by placing an SVG in packages/icons/svg and describing it in icons.json.",
                   rules + f'<div class="icons">{cells}</div>')


def motion(d: GuideData) -> str:
    tree = d.tokens.tree
    curves = []
    for name, (x1, y1, x2, y2) in tree["motion"]["ease"].items():
        def p(x: float, y: float) -> str:
            return f"{10 + x * 180:.1f} {190 - y * 180:.1f}"
        curves.append(
            f'<div class="curve"><h3 class="t-h2">{e(name.capitalize())}</h3>'
            f'<svg viewBox="0 0 200 200" role="img" aria-label="Ease curve {e(name)}"><path class="axis" d="M10 10V190H190"/>'
            f'<path class="line" d="M{p(0, 0)}C{p(x1, y1)} {p(x2, y2)} {p(1, 1)}"/></svg>'
            f'<p class="spec"><code>--ease-{e(name)}</code> cubic-bezier({x1}, {y1}, {x2}, {y2}). {e(d.tokens.descriptions.get(f"motion.ease.{name}", ""))}</p>'
            f'<div class="track" id="track-{e(name)}"><i style="transition-timing-function:var(--ease-{e(name)})"></i></div>'
            f'<div><button class="button" type="button" data-play="track-{e(name)}" aria-pressed="false">Play</button></div></div>')
    dur_rows = [[f"<code>--dur-{e(k)}</code>", f"{v} ms"] for k, v in tree["motion"]["duration"].items()]
    auto = tree["motion"]["autoscroll"]
    auto_rows = [[f"<code>{e(k)}</code>", e(str(v)), e(d.tokens.descriptions.get(f"motion.autoscroll.{k}", ""))] for k, v in auto.items()]
    body = (f'<div class="curves">{"".join(curves)}</div>' + table(["Duration", "Value"], dur_rows, {1})
            + '<div class="stack"><h3 class="t-h2">Autoscroll in pinned 3D sections</h3>'
            '<p class="note">After a pause the page keeps moving in the reader\'s direction, at their own speed within these limits. Any touch, wheel or key stops it; a visible switch turns it off; it never runs with reduced motion.</p>'
            + table(["Setting", "Value", "Meaning"], auto_rows) + "</div>")
    return section("motion", "Motion", "Things arrive with weight and settle. Nothing bounces. With reduced motion every duration becomes zero.", body)


def voice(d: GuideData) -> str:
    principles = "".join(f"<li>{e(p)}</li>" for p in d.voice.principles)
    examples = []
    for ex in d.voice.examples:
        why = "; ".join(dict.fromkeys(f.message for f in lint_text(ex["before"], d.voice)))
        examples.append(f'<div class="example panel"><div><p class="before">{e(ex["before"])}</p><p class="why">{e(why)}</p></div>'
                        f'<p class="t-body-lg">{e(ex["after"])}</p></div>')
    banned = "".join(f'<li>{e(b["term"])} <span>{e(b["use"])}</span></li>' for b in d.banned.get("en", []))
    claims = "".join(f"<li>{e(c)}</li>" for loc, words in d.claims.items() if not loc.startswith("$") for c in words)
    body = (f'<ul class="rules">{principles}</ul>'
            '<div class="stack"><h3 class="t-h2">Before and after</h3><p class="note">The red notes are what the copy linter reports for each "before". Every "after" passes.</p>'
            "\n<!-- copy-lint-disable -->\n"  # from here the section quotes bad copy on purpose
            '<div class="examples">\n' + "\n".join(examples) + "\n</div></div>\n"
            '<div class="stack"><h3 class="t-h2">Words we do not use</h3><p class="note">With what to say instead. The linter stops the build on these, and on every em or en dash.</p>'
            f'<ul class="words">{banned}</ul></div>'
            '<div class="stack"><h3 class="t-h2">Claims that need proof</h3><p class="note">Allowed only after legal review, marked in the source with copy-lint-allow. Blogs may ask "how to choose the best..." as a question.</p>'
            f'<ul class="words">{claims}</ul></div>'
            "\n<!-- copy-lint-enable -->\n")
    return section("voice", "Voice", "Write like a senior teacher talking to a parent at the front desk. Short, plain and specific.", body)


def images(d: GuideData) -> str:
    og = "".join(f'<figure><img src="assets/og/og-default-{loc}.png" width="1200" height="630" alt="">'
                 f"<figcaption>Default share image, {LOCALE_NAMES.get(loc, loc)}</figcaption></figure>" for loc in d.og_locales)
    plates = d.favicons["plates"] + [f for f in d.favicons["transparent"] if f["size"] >= 192]
    apps = "".join(f'<figure><img src="assets/favicon/{e(p["name"])}" width="{min(p["size"], 120)}" height="{min(p["size"], 120)}" alt="">'
                   f'<figcaption>{e(p["name"])}</figcaption></figure>' for p in plates)
    flagged = [s for s in d.media if s.placeholder or s.draft_locales]
    rows = [[f"<code>{e(s.id)}</code>", e(s.origin), "Placeholder" if s.placeholder else "Ready",
             e(", ".join(LOCALE_NAMES.get(x, x) for x in s.draft_locales)) or "None", e(s.note)] for s in flagged]
    body = (f'<div class="og-grid">{og}</div><div class="app-icons">{apps}</div>'
            '<div class="stack"><h3 class="t-h2">Media still to confirm</h3>'
            + table(["Slot", "Origin", "Status", "Draft languages", "Note"], rows) + "</div>")
    return section("images", "Share images and app icons", "Built from the official medal, the tokens and og/layout.json. Text is measured with the real fonts.", body)


def files(_d: GuideData) -> str:
    rows = [
        ["Colours, type, space, motion, 3D materials", "<code>packages/tokens/tokens.json</code>", "<code>make tokens</code>"],
        ["Contrast pairs", "<code>packages/tokens/contrast.json</code>", "<code>make tokens</code>"],
        ["Fonts and fallbacks", "<code>packages/tokens/fonts.config.json</code>", "<code>make fonts metrics</code>"],
        ["Icons", "<code>packages/icons/svg</code>, <code>icons.json</code>", "<code>make icons</code>"],
        ["Logo source and sizes", "<code>packages/media/manifest.json</code>, <code>packages/brand/logo.json</code>", "<code>make media-fetch logo</code>"],
        ["Favicons and manifest", "<code>packages/brand/favicons.json</code>, <code>identity.json</code>", "<code>make favicons</code>"],
        ["Share images", "<code>packages/brand/og/layout.json</code>, <code>og/copy.json</code>", "<code>make og</code>"],
        ["Voice rules", "<code>packages/brand/voice.json</code>", "<code>make copy-lint</code>"],
        ["This page", "<code>tools/dsapkit/src/dsapkit/guide</code>", "<code>make guide</code>"],
    ]
    return section("files", "Where things live", "Change the file, run the command, and every output follows. Nothing generated is edited by hand.",
                   table(["To change", "Edit", "Then run"], rows))


SECTIONS = [("logo", "Logo", logo), ("colour", "Colour", colour), ("contrast", "Contrast", contrast),
            ("depth", "Surfaces", depth), ("type", "Type", type_), ("space", "Space", space), ("icons", "Icons", icons),
            ("motion", "Motion", motion), ("voice", "Voice", voice), ("images", "Images", images), ("files", "Files", files)]
