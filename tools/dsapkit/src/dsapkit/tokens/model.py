"""DTCG-style token model: collect, resolve aliases, validate types."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import BuildError

ALIAS_RE = re.compile(r"^\{([^{}]+)\}$")
HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
NUMBER_TYPES = {"dimension", "number", "percentage", "duration", "fontWeight"}
TYPE_FAMILIES = {"display", "body"}


@dataclass(frozen=True)
class Token:
    path: tuple[str, ...]
    type: str
    value: Any
    description: str = ""

    @property
    def name(self) -> str:
        return ".".join(self.path)


@dataclass(frozen=True)
class TokenSet:
    """Resolved tokens: `flat` maps dotted names to values, `tree` nests them."""

    flat: dict[str, Any]
    tree: dict[str, Any]
    digest: str
    descriptions: dict[str, str] = field(default_factory=dict)

    def get(self, name: str) -> Any:
        if name not in self.flat:
            raise BuildError(f"no token named {name}")
        return self.flat[name]


def _collect(node: dict[str, Any], path: tuple[str, ...], inherited: str,
             descriptions: dict[str, str]) -> list[Token]:
    group_type = node.get("$type", inherited)
    if "$description" in node and path:
        descriptions[".".join(path)] = node["$description"]
    out: list[Token] = []
    for key, child in node.items():
        if key.startswith("$"):
            continue
        child_path = path + (key,)
        if not isinstance(child, dict):
            raise BuildError(f"{'.'.join(child_path)}: expected an object with $value")
        if "$value" in child:
            token_type = child.get("$type", group_type)
            if not token_type:
                raise BuildError(f"{'.'.join(child_path)}: no $type on the token or its group")
            token = Token(child_path, token_type, child["$value"], child.get("$description", ""))
            if token.description:
                descriptions[token.name] = token.description
            out.append(token)
        else:
            out.extend(_collect(child, child_path, group_type, descriptions))
    return out


def _resolve(value: Any, index: dict[str, Token], stack: tuple[str, ...]) -> Any:
    if isinstance(value, str):
        match = ALIAS_RE.match(value)
        if not match:
            return value
        ref = match.group(1)
        if ref in stack:
            raise BuildError(f"alias cycle: {' -> '.join(stack + (ref,))}")
        if ref not in index:
            raise BuildError(f"{stack[-1]}: unknown alias {{{ref}}}")
        return _resolve(index[ref].value, index, stack + (ref,))
    if isinstance(value, list):
        return [_resolve(v, index, stack) for v in value]
    if isinstance(value, dict):
        return {k: _resolve(v, index, stack) for k, v in value.items()}
    return value


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate(token: Token, value: Any) -> None:
    def need(ok: bool, message: str) -> None:
        if not ok:
            raise BuildError(f"{token.name}: {message} (got {value!r})")

    kind = token.type
    if kind == "color":
        need(isinstance(value, str) and bool(HEX_RE.match(value)), "colour must be #rrggbb or #rrggbbaa")
    elif kind in NUMBER_TYPES:
        need(_is_number(value), f"{kind} must be a number")
    elif kind == "string":
        need(isinstance(value, str), "must be a string")
    elif kind == "list":
        need(isinstance(value, list) and all(isinstance(v, str) for v in value), "must be a list of strings")
    elif kind == "fontFamily":
        need(isinstance(value, list) and bool(value) and all(isinstance(f, str) for f in value),
             "must be a non-empty list of family names")
    elif kind == "cubicBezier":
        need(isinstance(value, list) and len(value) == 4 and all(_is_number(x) for x in value), "must be four numbers")
        need(0 <= value[0] <= 1 and 0 <= value[2] <= 1, "x control points must be between 0 and 1")
    elif kind == "fluidType":
        keys = {"min", "max", "lineHeight", "tracking", "weight", "family", "stretch"}
        need(isinstance(value, dict) and keys <= value.keys(), f"needs {sorted(keys)}")
        need(value["family"] in TYPE_FAMILIES, f"family must be one of {sorted(TYPE_FAMILIES)}")
        need(value["min"] <= value["max"], "min must not be larger than max")
    elif kind == "fluidDimension":
        need(isinstance(value, dict) and _is_number(value.get("min")) and _is_number(value.get("max")), "needs min and max")
    elif kind == "shadow":
        need(isinstance(value, list) and bool(value), "must be a list of layers")
        for layer in value:
            need(all(_is_number(layer.get(k)) for k in ("offsetX", "offsetY", "blur", "spread")),
                 "each layer needs offsetX, offsetY, blur and spread")
            need(isinstance(layer.get("color"), str) and bool(HEX_RE.match(layer["color"])), "layer colour must be hex")
    elif kind == "material":
        need(isinstance(value, dict) and isinstance(value.get("color"), str), "needs a colour")
    else:
        raise BuildError(f"{token.name}: unknown $type {kind}")


def _nest(flat: dict[str, Any]) -> dict[str, Any]:
    tree: dict[str, Any] = {}
    for name, value in flat.items():
        parts = name.split(".")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return tree


def parse_tokens(raw: bytes) -> TokenSet:
    descriptions: dict[str, str] = {}
    tokens = _collect(json.loads(raw), (), "", descriptions)
    index = {t.name: t for t in tokens}
    flat: dict[str, Any] = {}
    for token in tokens:
        value = _resolve(token.value, index, (token.name,))
        _validate(token, value)
        flat[token.name] = value
    return TokenSet(flat, _nest(flat), hashlib.sha256(raw).hexdigest()[:12], descriptions)


def load_tokens(path: Path) -> TokenSet:
    if not path.exists():
        raise BuildError(f"missing {path}")
    try:
        return parse_tokens(path.read_bytes())
    except json.JSONDecodeError as err:
        raise BuildError(f"{path}: invalid JSON at line {err.lineno}: {err.msg}") from err
