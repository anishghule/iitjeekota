"""Write docs/brand/guide: index.html (open locally) and guide.html (the same page as a fragment for publishing)."""

from __future__ import annotations

import datetime
import shutil
from importlib import resources
from pathlib import Path

from ..brand.svg import escape
from ..context import Context
from ..copylint.rules import load_rules
from ..errors import BuildError
from ..icons.build import load_icons
from ..jsonio import read_json, reset_dir, write_text
from ..media.library import check_media
from ..tokens.colour import relative_luminance, composite
from ..tokens.contrast import check
from ..tokens.css import fonts_css, rule, shadow, tokens_css, typography_css
from .sections import SECTIONS, GuideData

TITLE = "Kota Stone and Brass"
# Option B of the display face test is shown from Google Fonts; it is never shipped on the site.
COMPARISON_FONTS = "https://fonts.googleapis.com/css2?family=Martel:wght@800&family=Zilla+Slab:wght@700&display=swap"


def theme_css(tree: dict) -> str:
    """The page follows the reader's light or dark setting by switching between the two token surfaces."""
    surfaces = tree["surface"]
    lum = {name: relative_luminance(composite(roles["bg"], "#ffffff")) for name, roles in surfaces.items()}
    light, dark = max(lum, key=lum.get), min(lum, key=lum.get)

    def decls(name: str, scheme: str) -> list[str]:
        return ([f"color-scheme: {scheme};"] + [f"--{role}: {value};" for role, value in surfaces[name].items()]
                + [f"--shadow-{lvl}: {shadow(layers)};" for lvl, layers in tree["shadow"][name].items()])

    return (rule(":root", decls(light, "light"))
            + "@media (prefers-color-scheme: dark) {\n" + rule(':root:not([data-theme="light"])', decls(dark, "dark"), "  ") + "}\n"
            + rule(':root[data-theme="dark"]', decls(dark, "dark")))


def _copy_assets(ctx: Context, out: Path, lock: dict, og_locales: list[str], logo_cfg: dict) -> None:
    paths = ctx.paths
    fonts = out / "assets" / "fonts"
    fonts.mkdir(parents=True)
    for face in lock["files"]:
        shutil.copyfile(paths.fonts_dir / face["file"], fonts / face["file"])
    needed = {f"logo/{logo_cfg['fileName'].format(size=s)}" for s in logo_cfg["sizes"]}
    needed |= {f"favicon/{p.name}" for p in (paths.brand_dist / "favicon").glob("*.png")}
    needed |= {f"og/og-default-{loc}.png" for loc in og_locales}
    for rel in sorted(needed):
        src = paths.brand_dist / rel
        if not src.exists():
            raise BuildError(f"{src.relative_to(paths.root)} is missing: run make brand before make guide")
        target = out / "assets" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)


def build_guide(ctx: Context) -> Path:
    paths, tokens = ctx.paths, ctx.tokens
    tree = tokens.tree
    lock = read_json(paths.fonts_lock, "run make fonts")
    metrics = read_json(paths.fonts_metrics, "run make metrics")
    voice_raw = read_json(paths.voice_json)
    og_locales = list(read_json(paths.og_copy)["locales"])
    logo_cfg = read_json(paths.logo_json)
    favicons = read_json(paths.favicons_json)
    sprite = (paths.icons_dist / "sprite.svg")
    if not sprite.exists():
        raise BuildError("packages/icons/dist/sprite.svg is missing: run make icons")

    out = reset_dir(paths.guide)
    _copy_assets(ctx, out, lock, og_locales, logo_cfg)
    data = GuideData(
        tokens=tokens, contrast=check(tree["surface"], read_json(paths.contrast_json)), metrics=metrics,
        icons=load_icons(paths), voice=load_rules(paths.voice_json), banned=voice_raw["banned"], claims=voice_raw["claims"],
        identity=read_json(paths.identity_json), media=check_media(paths), og_locales=og_locales,
        favicons=favicons, logo_sizes=logo_cfg["sizes"],
    )

    package = resources.files("dsapkit.guide")
    css = "\n".join([tokens_css(tree), fonts_css(lock, metrics, "assets/fonts"), typography_css(tree),
                     (paths.icons_dist / "icons.css").read_text(encoding="utf-8"), theme_css(tree),
                     package.joinpath("guide.css").read_text(encoding="utf-8")])
    script = package.joinpath("guide.js").read_text(encoding="utf-8")
    contents = "".join(f'<li><a href="#{sid}">{escape(label)}</a></li>' for sid, label, _ in SECTIONS)
    body_sections = "".join(render(data) for _, _, render in SECTIONS)
    hero_alt = next(s for s in data.media if s.id == logo_cfg["slot"]).alt.get("en", "")
    today = datetime.date.today().isoformat()

    head = (f"<title>{TITLE}</title>\n"
            '<meta name="claude:viewport-fit-sides" content="cover">\n'
            f'<link rel="stylesheet" href="{COMPARISON_FONTS}">\n'
            f"<style>\n{css}\n</style>\n")
    body = (sprite.read_text(encoding="utf-8") + '<div class="page">'
            f'<header class="hero"><img class="hero-medal" src="assets/logo/{logo_cfg["fileName"].format(size=512)}" width="512" height="512" alt="{escape(hero_alt)}">'
            f'<div><h1 class="t-display-xl">{TITLE}</h1>'
            f'<p class="lede t-body-lg">The brand system for {escape(data.identity["domain"])}, the IIT JEE coaching site of '
            f'{escape(data.identity["name"])}, powered by Kota. Every colour, size, icon and image on this page is read from the source files when it is built. '
            "Change a token and run make brand: this page, the site and the 3D scenes change together.</p>"
            f'<p class="meta t-small">Built {today} from tokens.json {tokens.digest}. {len(tokens.flat)} tokens, {len(data.icons)} icons.</p></div></header>'
            f'<nav class="contents" aria-label="Contents"><ol>{contents}</ol></nav>'
            f"<main>{body_sections}</main></div>\n<script>\n{script}</script>\n")

    write_text(out / "guide.html", head + body)
    write_text(out / "index.html", '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
               '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
               f"{head}</head>\n<body>\n{body}</body>\n</html>\n")
    return out / "index.html"
