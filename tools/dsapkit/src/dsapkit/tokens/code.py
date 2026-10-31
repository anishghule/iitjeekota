"""TypeScript and Python modules carrying the resolved tokens."""

from __future__ import annotations

import json
import pprint
from typing import Any


def typescript_module(tree: dict[str, Any], header: str) -> str:
    return (
        f"// {header}\n\n"
        f"export const tokens = {json.dumps(tree, indent=2, ensure_ascii=False)} as const;\n\n"
        "export type Tokens = typeof tokens;\n"
        f"export const surfaces = {json.dumps(list(tree['surface']))} as const;\n"
        "export type SurfaceName = (typeof surfaces)[number];\n"
        f"export const typeVariants = {json.dumps(list(tree['type']['scale']))} as const;\n"
        "export type TypeVariant = (typeof typeVariants)[number];\n"
        "export type IconSize = keyof typeof tokens.icon.size;\n"
        "export type MaterialName = keyof typeof tokens.material;\n\n"
        "/** A CSS custom property reference: cssVar('accent') is 'var(--accent)'. */\n"
        "export const cssVar = (name: string): string => `var(--${name})`;\n"
    )


def python_module(tree: dict[str, Any], header: str) -> str:
    return (
        f'"""{header}"""\n\n'
        "from typing import Any, Final\n\n"
        f"TOKENS: Final[dict[str, Any]] = {pprint.pformat(tree, width=100, sort_dicts=False)}\n"
    )
