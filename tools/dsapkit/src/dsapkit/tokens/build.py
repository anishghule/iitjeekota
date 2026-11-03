"""Build packages/tokens/dist from tokens.json, contrast.json and the font lock and metrics."""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..errors import BuildError
from ..jsonio import GENERATED, read_json, reset_dir, write_json, write_text
from ..paths import Paths
from . import code, css
from .contrast import ContrastResult, check, to_markdown
from .model import TokenSet, load_tokens


@dataclass(frozen=True)
class TokenBuild:
    tokens: TokenSet
    contrast: list[ContrastResult]


def _check_font_stacks(tokens: TokenSet, metrics: dict) -> None:
    """Every '<Family> Fallback' named in a token font stack must have computed metrics."""
    known = {f["family"] for f in metrics["fallbacks"].values()}
    for role, stack in tokens.tree["font"]["family"].items():
        for name in stack:
            if name.endswith(" Fallback") and name not in known:
                raise BuildError(f"font.family.{role} uses {name!r} but fonts.metrics.json has no such fallback; run make metrics")


def preload_files(lock: dict, base_url: str, roles: tuple[str, ...] = ("display", "body")) -> list[str]:
    """Latin files of the fonts the first screen needs. Web fallbacks are not preloaded: they are
    fetched only if the page ends up needing them."""
    return [f"{base_url.rstrip('/')}/{f['file']}" for f in lock["files"]
            if f["subset"] == "latin" and f["role"] in roles and not f["fallback"]]


def build_tokens(paths: Paths, font_base_url: str = "/fonts") -> TokenBuild:
    tokens = load_tokens(paths.tokens_json)
    tree = tokens.tree
    header = GENERATED.format(source=f"tokens.json {tokens.digest}")
    results = check(tree["surface"], read_json(paths.contrast_json))
    lock = read_json(paths.fonts_lock, "run make fonts")
    metrics = read_json(paths.fonts_metrics, "run make metrics")
    _check_font_stacks(tokens, metrics)

    out = reset_dir(paths.tokens_dist)
    write_text(out / "tokens.css", f"/* {header} */\n\n" + css.tokens_css(tree))
    write_text(out / "typography.css", f"/* {header} */\n\n" + css.typography_css(tree))
    write_text(out / "breakpoints.css", f"/* {header} */\n\n" + css.breakpoints_css(tree))
    write_text(out / "fonts.css", f"/* {header} */\n\n" + css.fonts_css(lock, metrics, font_base_url))
    write_text(out / "tokens.ts", code.typescript_module(tree, header))
    write_text(out / "tokens.py", code.python_module(tree, header))
    write_json(out / "tokens.resolved.json", {"$generated": header, **tree})
    write_json(out / "tokens.descriptions.json", tokens.descriptions)
    write_json(out / "fonts.preload.json", preload_files(lock, font_base_url))
    write_text(out / "contrast.json", json.dumps([r.as_dict() for r in results], indent=2) + "\n")
    write_text(out / "contrast.md", f"<!-- {header} -->\n\n" + to_markdown(results))

    failed = [r for r in results if not r.passed]
    if failed:
        lines = [f"{r.surface}: {r.fg} on {r.bg} is {r.ratio}:1, needs {r.minimum:g}:1 ({r.use})" for r in failed]
        raise BuildError("contrast check failed:\n  " + "\n  ".join(lines))
    return TokenBuild(tokens, results)
