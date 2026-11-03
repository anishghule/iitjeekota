"""dsapkit command line. Run `python -m dsapkit --help`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from .brand.favicons import build_favicons
from .brand.logo import build_logo
from .brand.og import OgRenderer
from .content.check import check_content
from .content.model import load_content
from .content.report import write_status
from .content.syllabus import check_syllabus, write_syllabus_doc
from .context import Context
from .copylint.lint import lint_paths
from .copylint.rules import load_rules
from .errors import BuildError
from .fonts.metrics import measure_fonts
from .fonts.vendor import fetch_fonts, verify_fonts
from .guide.build import build_guide
from .icons.build import build_icons
from .jsonio import read_json
from .media.encode import encode_all
from .media.library import check_media, fetch_media, load_library, waiting
from .media.photos import encode_photos
from .media.report import write_media_todo
from .paths import Paths
from .web.export import export_web
from .web.lint import check_not_found, check_output, lint_source
from .map.build import build_map
from .map.fetch import fetch_map
from .site.build import build_site
from .site.drift import check_drift, require_no_drift
from .site.model import load_site
from .tokens.build import build_tokens

Command = Callable[[Context, argparse.Namespace], None]


def _rel(ctx: Context, path: Path) -> str:
    return str(path.relative_to(ctx.paths.root))


def cmd_fonts(ctx: Context, _args: argparse.Namespace) -> None:
    print(f"{len(fetch_fonts(ctx.paths, ctx.fonts_config, ctx.google_fonts))} font files vendored and locked")


def cmd_fonts_verify(ctx: Context, _args: argparse.Namespace) -> None:
    print(f"{verify_fonts(ctx.paths)} font files match fonts.lock.json")


def cmd_metrics(ctx: Context, _args: argparse.Namespace) -> None:
    metrics = measure_fonts(ctx.paths, ctx.fonts_config, ctx.tokens, ctx.google_fonts)
    for role, fallback in metrics["fallbacks"].items():
        print(f"{fallback['family']}: size-adjust {fallback['sizeAdjust']}% ({role})")
    for role, adjust in metrics["sizeAdjust"].items():
        print(f"{role}: size-adjust {adjust['value']}% to match the {adjust['matches']} x-height")


def cmd_media_fetch(ctx: Context, args: argparse.Namespace) -> None:
    entries, removed = fetch_media(ctx.paths, refresh=args.refresh)
    for entry in entries:
        print(f"{entry['id']}: {entry['width']}x{entry['height']} {entry['type']} from {entry['source']}")
    for path in removed:
        print(f"removed {_rel(ctx, path)} (no slot uses it)")


def cmd_tokens(ctx: Context, args: argparse.Namespace) -> None:
    result = build_tokens(ctx.paths, args.font_base)
    print(f"tokens built ({len(result.contrast)} contrast pairs pass) into {_rel(ctx, ctx.paths.tokens_dist)}")


def cmd_icons(ctx: Context, _args: argparse.Namespace) -> None:
    print(f"{len(build_icons(ctx.paths))} icons checked and built into {_rel(ctx, ctx.paths.icons_dist)}")


def cmd_logo(ctx: Context, _args: argparse.Namespace) -> None:
    print(f"{len(build_logo(ctx.paths, ctx.logo))} logo sizes written from the official medal")


def cmd_favicons(ctx: Context, _args: argparse.Namespace) -> None:
    print(f"{len(build_favicons(ctx.paths, ctx.tokens, ctx.logo))} favicon files written")


def cmd_og(ctx: Context, args: argparse.Namespace) -> None:
    renderer = OgRenderer(ctx.paths, ctx.tokens, ctx.render_fonts, ctx.logo, ctx.text_raster)
    if args.title:
        if not args.out:
            raise BuildError("--out is needed with --title")
        renderer.render(args.locale, args.title, args.subtitle, args.out)
        print(f"wrote {args.out}")
        return
    for path in renderer.render_defaults(ctx.paths.og_copy):
        print(f"wrote {_rel(ctx, path)}")


def cmd_media_encode(ctx: Context, _args: argparse.Namespace) -> None:
    for done in encode_all(ctx.paths):
        print(f"  {done.slot}: {done.width}x{done.height}, {done.seconds:.1f} s, {done.bytes / 1_000_000:.1f} MB (no sound, no metadata); "
              f"poster {done.poster_slot}, {done.poster_bytes // 1000} KB")
    for photo in encode_photos(ctx.paths):
        print(f"  {photo.slot}: {photo.width}x{photo.height}, {photo.bytes // 1000} KB (no metadata)")
    print("encoded; run make media-fetch to check each file against its slot and pin it")


def cmd_media(ctx: Context, _args: argparse.Namespace) -> None:
    slots = check_media(ctx.paths)
    waiting_slots = waiting(ctx.paths, slots)
    print(f"{len(slots)} media slots checked, {len(waiting_slots)} files still to be added by D-SAP")
    for slot in slots:
        flags = [f for f, on in (("placeholder", slot.placeholder), (f"draft {', '.join(slot.draft_locales)}", slot.draft_locales)) if on]
        if flags:
            print(f"  {slot.id}: {'; '.join(flags)}" + (f". {slot.note}" if slot.note else ""))
    pages = {route.id: route.path("en") for route in load_site(ctx.paths).routes.values()}
    print(f"wrote {_rel(ctx, write_media_todo(ctx.paths, load_library(ctx.paths), pages))}")


def cmd_guide(ctx: Context, _args: argparse.Namespace) -> None:
    print(f"brand guide written to {_rel(ctx, build_guide(ctx))}")


def cmd_copy_lint(ctx: Context, args: argparse.Namespace) -> None:
    rules = load_rules(ctx.paths.voice_json)
    scan = read_json(ctx.paths.voice_json)["scan"]
    targets = args.paths or [ctx.paths.root / p for p in scan["include"]]
    exclude = {(ctx.paths.root / p).resolve() for p in scan["exclude"]}
    tree = ctx.tokens.tree["type"]
    locales = set(tree["latin"]["locales"]) | set(tree["devanagari"]["locales"])
    findings = lint_paths([t for t in targets if t.exists()], rules, locales, tree["latin"]["locales"][0], exclude)
    for finding in findings:
        print(finding.format(ctx.paths.root))
    errors = [f for f in findings if f.severity == "error"]
    print(f"copy lint: {len(errors)} errors, {len(findings) - len(errors)} warnings")
    if errors:
        raise BuildError(f"{len(errors)} copy errors")


def cmd_site(ctx: Context, _args: argparse.Namespace) -> None:
    result = build_site(ctx.paths, ctx.tokens)
    site = result.site
    live = [r for r in site.routes.values() if site.is_live(r.id)]
    planned = sum(r.planned for r in site.routes.values())
    print(f"site: {len(site.routes)} pages per language: {len(live)} ready, "
          f"{len(site.routes) - len(live) - planned} waiting for facts or confirmed commutes, {planned} planned posts")
    print(f"structured data rules: read from Google's docs on {result.rules_checked}, {result.rules_age_days} days ago")
    print(f"wrote {_rel(ctx, ctx.paths.site_dist)} and docs/seo/site-map.md, structured-data.md, listings-and-citations.md")


def cmd_docs_drift(ctx: Context, _args: argparse.Namespace) -> None:
    drifts = check_drift(read_json(ctx.paths.site / "jsonld-rules.json"))
    for d in drifts:
        print(f"  {'CHANGED' if d.changed else 'same   '} {d.live or 'no date'}  {d.page.url}")
    require_no_drift(drifts)
    print(f"docs drift: {len(drifts)} Google pages, none changed since the rules were read")


def cmd_map_fetch(ctx: Context, _args: argparse.Namespace) -> None:
    written = fetch_map(ctx.paths, load_site(ctx.paths))
    print(f"map data fetched and pinned: {', '.join(_rel(ctx, p) for p in written.values())}")


def cmd_map(ctx: Context, _args: argparse.Namespace) -> None:
    result = build_map(ctx.paths, load_site(ctx.paths), ctx.tokens)
    data = result.data
    approximate = [c["id"] for c in data["centres"] if c["approximate"]]
    print(f"map: {len(data['areas'])} areas, {len(data['routes'])} routes, {len(data['rivers'])} river lines, "
          f"{len(data['roads'])} road lines (data from {data['fetched']})")
    if approximate:
        print(f"  approximate pin for {', '.join(approximate)}: confirm its geo fact, then make map-fetch")
    for warning in result.warnings:
        print(f"  check commute: {warning}")
    print(f"wrote {', '.join(_rel(ctx, p) for p in result.files)}")


def cmd_web_data(ctx: Context, _args: argparse.Namespace) -> None:
    site = load_site(ctx.paths)
    report = export_web(ctx.paths, site, load_content(ctx.paths, site.locales))
    by_locale = {loc: sum(1 for _, l in report.pages if l == loc) for loc in site.locales}
    print(f"web data: {', '.join(f'{n} {loc}' for loc, n in by_locale.items())} pages; {report.files} files "
          f"in {_rel(ctx, ctx.paths.web_generated)}")
    counts = {s: sum(f.severity == s for f in report.findings) for s in ("warning", "pending")}
    print(f"structured data: {len(report.pages)} pages, no errors, {counts['warning']} warnings, "
          f"{counts['pending']} properties waiting for facts (docs/seo/structured-data-results.md)")
    for f in report.findings:
        if f.severity == "warning":
            print(f"  warning {f.page}: {f.message}")
    for line in report.left_out:
        print(f"  not shown: {line}")


def cmd_web_lint(ctx: Context, _args: argparse.Namespace) -> None:
    problems = lint_source(ctx.paths.web_src, ctx.paths.web_generated)
    dist = ctx.paths.web / "dist"
    if dist.is_dir():
        problems += check_output(dist) + check_not_found(dist)
    for problem in problems:
        print(problem.format(ctx.paths.root))
    print(f"web lint: {len(problems)} problems" + ("" if dist.is_dir() else " (no build to check: run make web)"))
    if problems:
        raise BuildError(f"{len(problems)} web lint problems")


def cmd_content(ctx: Context, _args: argparse.Namespace) -> None:
    site = load_site(ctx.paths)
    content = load_content(ctx.paths, site.locales)
    findings = check_content(content, site)
    counts = {s: sum(f.severity == s for f in findings) for s in ("error", "warning", "held", "unlinked")}
    print(f"content: {len(content.pages)} page versions, {len(content.blocks)} shared blocks; "
          f"{counts['held']} held back for facts, {counts['unlinked']} links to pages not live yet")
    for f in findings:
        if f.severity in ("error", "warning"):
            print(f"  {f.severity} {f.where}: {f.message}")
    print(f"wrote {_rel(ctx, write_status(ctx.paths, content, site, findings))}")
    syllabus = content.syllabus
    syllabus_problems = check_syllabus(syllabus)
    for problem in syllabus_problems:
        print(f"  error {problem}")
    advanced_only = sum(c.advanced_only for c in syllabus.chapters)
    print(f"syllabus: {len(syllabus.chapters)} chapters, {advanced_only} in JEE Advanced only; "
          f"wrote {_rel(ctx, write_syllabus_doc(ctx.paths, syllabus))}")
    errors = counts["error"] + len(syllabus_problems)
    if errors:
        raise BuildError(f"{errors} content errors")


def cmd_brand(ctx: Context, args: argparse.Namespace) -> None:
    for step in (cmd_tokens, cmd_icons, cmd_logo, cmd_favicons, cmd_og, cmd_media, cmd_guide):
        step(ctx, args)


COMMANDS: dict[str, tuple[Command, str]] = {
    "fonts": (cmd_fonts, "download the vendored woff2 files and write fonts.lock.json (network)"),
    "fonts-verify": (cmd_fonts_verify, "check vendored fonts against fonts.lock.json"),
    "metrics": (cmd_metrics, "measure fonts, write fallback and size-adjust metrics (macOS, network)"),
    "media-encode": (cmd_media_encode, "turn supplied videos and large photos into the files the site serves, without sound or metadata (needs ffmpeg)"),
    "media-fetch": (cmd_media_fetch, "fetch supplied media from their recorded sources and write media.lock.json"),
    "tokens": (cmd_tokens, "build packages/tokens/dist and check contrast"),
    "icons": (cmd_icons, "check icon sources and build the sprite"),
    "logo": (cmd_logo, "logo sizes from the official medal"),
    "favicons": (cmd_favicons, "favicons, app icons and the web manifest"),
    "og": (cmd_og, "Open Graph images (defaults, or one page with --title)"),
    "media": (cmd_media, "check every media slot and list placeholders and drafts"),
    "guide": (cmd_guide, "write the brand guide into docs/brand/guide"),
    "copy-lint": (cmd_copy_lint, "apply the voice rules to docs and content"),
    "site": (cmd_site, "check routes, keywords, links and structured data; write the SEO reports"),
    "docs-drift": (cmd_docs_drift, "compare Google's documentation with the structured data rules (network)"),
    "map-fetch": (cmd_map_fetch, "download the area map's OpenStreetMap data and pin it (network)"),
    "map": (cmd_map, "build the area map from the pinned OpenStreetMap data"),
    "web-data": (cmd_web_data, "write the resolved data and static files apps/web renders"),
    "web-lint": (cmd_web_lint, "check apps/web against the contract's hard rules, and its build for inline scripts and styles"),
    "content": (cmd_content, "check page copy against its template, facts and pages; write docs/content/status.md"),
    "brand": (cmd_brand, "tokens, icons, logo, favicons, OG images, media check and the brand guide"),
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dsapkit", description="Build tooling for iitjeekota.com.")
    sub = p.add_subparsers(dest="command", required=True)
    for name, (_fn, help_text) in COMMANDS.items():
        cmd = sub.add_parser(name, help=help_text)
        if name in ("tokens", "brand"):
            cmd.add_argument("--font-base", default="/fonts", help="URL path the font files are served from")
        if name in ("og", "brand"):
            cmd.add_argument("--locale", default="en")
            cmd.add_argument("--title", default="")
            cmd.add_argument("--subtitle", default="")
            cmd.add_argument("--out", type=Path)
        if name == "media-fetch":
            cmd.add_argument("--refresh", action="store_true", help="download every supplied file again")
        if name == "copy-lint":
            cmd.add_argument("paths", nargs="*", type=Path, help="files or folders (default: the scan list in voice.json)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        COMMANDS[args.command][0](Context(Paths.discover()), args)
    except BuildError as err:
        print(f"dsapkit {args.command}: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
