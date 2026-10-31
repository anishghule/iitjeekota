"""Structured data fixtures: fill them from the registry and facts, then check them against Google's rules.

Fixtures in packages/site/jsonld/ are the expected JSON-LD of each page template;
"$page" names the route a fixture describes. "{{origin}}" becomes the site
origin. A value that is exactly "{{fact:id}}" takes the fact's value when
confirmed ("{{fact:id#field}}" reads one field of a structured fact, such as a
map pin); while the fact is pending the property is left out and reported. An
element carrying "$onlyIfLive": "<route>" is left out while that route is gated,
and one carrying "$onlyIfConfirmed": [fact ids] while any of those facts is pending.
Keys starting with "$" are notes and never reach the output. The web build
(Phase 7) must produce the same output; these fixtures become its tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..jsonio import read_json
from .links import breadcrumbs
from .model import Site

FACT_RE = re.compile(r"^\{\{fact:([\w.-]+)(?:#(\w+))?\}\}$")  # {{fact:id}} or {{fact:id#field}} for structured facts


@dataclass
class Fixture:
    name: str
    route: str
    locale: str
    data: dict[str, Any]
    pending: list[tuple[str, str]] = field(default_factory=list)  # (property left out, why)

    @property
    def pending_properties(self) -> set[str]:
        return {prop for prop, _ in self.pending}


@dataclass(frozen=True)
class Finding:
    fixture: str
    severity: str  # error, warning, pending
    message: str


def _fill(value: Any, site: Site, pending: list[tuple[str, str]], key: str = "") -> Any:
    """Resolve placeholders; returns None for anything that must be left out, recording why under its property."""
    if isinstance(value, str):
        match = FACT_RE.match(value)
        if match:
            filled, why = site.fact_value(match.group(1), match.group(2))
            if why:
                pending.append((key, why))
            return filled
        return value.replace("{{origin}}", site.origin)
    if isinstance(value, list):
        items = [_fill(v, site, pending, key) for v in value]
        return [v for v in items if v is not None]
    if isinstance(value, dict):
        route = value.get("$onlyIfLive")
        if route is not None:
            if route not in site.routes:
                pending.append((key, f"unknown page {route}"))
                return None
            if not site.is_live(route):
                pending.append((key, f"page {route} gated"))
                return None
        for fact_id in value.get("$onlyIfConfirmed", []):
            _, why = site.fact_value(fact_id)
            if why:
                pending.append((key, why))
                return None
        out = {}
        for child_key, child in value.items():
            if child_key.startswith("$"):
                continue
            filled = _fill(child, site, pending, child_key)
            if filled is not None:
                out[child_key] = filled
        return out
    return value


def load_fixtures(folder: Path, site: Site) -> list[Fixture]:
    fixtures = []
    for path in sorted(folder.glob("*.json")):
        raw = read_json(path)
        pending: list[str] = []
        data = _fill(raw, site, pending)
        fixtures.append(Fixture(path.stem, raw.get("$page", ""), raw.get("$locale", site.config["defaultLocale"]), data, pending))
    return fixtures


def _nodes(value: Any) -> list[dict[str, Any]]:
    """Every object with an @type, at any depth."""
    found = []
    if isinstance(value, dict):
        if "@type" in value:
            found.append(value)
        for child in value.values():
            found += _nodes(child)
    elif isinstance(value, list):
        for child in value:
            found += _nodes(child)
    return found


def _refs(value: Any) -> list[str]:
    """@id values used as references (objects holding only an @id)."""
    refs = []
    if isinstance(value, dict):
        if set(value) == {"@id"}:
            refs.append(value["@id"])
        for child in value.values():
            refs += _refs(child)
    elif isinstance(value, list):
        for child in value:
            refs += _refs(child)
    return refs


def _types(node: dict[str, Any]) -> list[str]:
    t = node["@type"]
    return t if isinstance(t, list) else [t]


def check_fixtures(site: Site, rules: dict[str, Any], fixtures: list[Fixture]) -> list[Finding]:
    findings: list[Finding] = []
    types, retired = rules["types"], rules["retired"]
    declared = {n["@id"] for f in fixtures for n in _nodes(f.data) if "@id" in n}

    def rule_for(name: str) -> dict[str, Any] | None:
        rule = types.get(name)
        return types.get(rule["sameAs"]) if rule and "sameAs" in rule else rule

    for fx in fixtures:
        def add(severity: str, message: str) -> None:
            findings.append(Finding(fx.name, severity, message))

        for prop, why in fx.pending:
            add("pending", f"{prop or 'value'} left out: {why}")
        if any(why.startswith(("unknown fact", "unknown page")) for _, why in fx.pending):
            add("error", "refers to a fact or page that does not exist")
        for node in _nodes(fx.data):
            for position, name in enumerate(_types(node)):
                if name in retired:
                    add("error", f"{name} is not used: {retired[name]}")
                    continue
                rule = rule_for(name)
                if rule is None:
                    add("error", f"{name} has no rule in jsonld-rules.json")
                    continue
                for prop in rule.get("required", []):
                    if prop not in node:
                        add("error", f"{name} is missing required {prop}")
                for prop in rule.get("forbidden", []):
                    if prop in node:
                        add("error", f"{name} must not carry {prop}")
                if position == 0:  # recommendations follow the node's first, most specific type
                    missing = [p for p in rule.get("recommended", []) if p not in node and p not in fx.pending_properties]
                    if missing:
                        add("warning", f"{name} lacks recommended {', '.join(missing)}")
                for prop, limit in rule.get("maxLength", {}).items():
                    if isinstance(node.get(prop), str) and len(node[prop]) > limit:
                        add("warning", f"{name}.{prop} is {len(node[prop])} characters; Google shows {limit}")
                items = node.get("itemListElement")
                if isinstance(items, list):
                    _check_items(name, rule, items, add)
                if name == "GeoCoordinates":
                    for axis in ("latitude", "longitude"):
                        decimals = str(node.get(axis, "")).partition(".")[2]
                        if len(decimals) < rule["minDecimals"]:
                            add("error", f"geo {axis} needs at least {rule['minDecimals']} decimals")
        for ref in _refs(fx.data):
            if ref not in declared:
                add("error", f"reference to {ref} is not declared in any fixture")
        for key, value in _url_values(fx.data, set(rules["urlKeys"])):
            if not value.startswith("https://"):
                add("error", f"{key} must be an absolute https URL: {value}")
        _check_breadcrumb(site, fx, add)
    return findings


def _check_items(name: str, rule: dict[str, Any], items: list[Any], add) -> None:
    """A list's items, checked against the item rules of that list type."""
    if "minItems" in rule and len(items) < rule["minItems"]:
        add("warning", f"{name} has {len(items)} items; Google needs at least {rule['minItems']}")
    positions = [i.get("position") for i in items]
    if positions != list(range(1, len(items) + 1)):
        add("error", f"{name} positions must run 1 to {len(items)}, got {positions}")
    item_rule = rule.get("items", {})
    for index, item in enumerate(items):
        needed = list(item_rule.get("required", []))
        if index < len(items) - 1:
            needed += item_rule.get("requiredExceptLast", [])
        for prop in needed:
            if prop not in item:
                add("error", f"{name} item {index + 1} is missing {prop}")


def _url_values(value: Any, keys: set[str]) -> list[tuple[str, str]]:
    out = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k in keys and isinstance(v, str):
                out.append((k, v))
            elif k in keys and isinstance(v, list):
                out += [(k, s) for s in v if isinstance(s, str)]
            out += _url_values(v, keys)
    elif isinstance(value, list):
        for v in value:
            out += _url_values(v, keys)
    return out


def _check_breadcrumb(site: Site, fx: Fixture, add) -> None:
    """The fixture's BreadcrumbList must equal the trail the registry builds for its route."""
    lists = [n for n in _nodes(fx.data) if "BreadcrumbList" in _types(n)]
    if fx.route not in site.routes:
        add("error", f"$page {fx.route!r} is not a route")
        return
    expected = breadcrumbs(site, site.routes[fx.route], fx.locale)
    if not lists:
        if expected:
            add("warning", "page has a breadcrumb trail but the fixture has no BreadcrumbList")
        return
    items = lists[0]["itemListElement"]
    got = [(i.get("name"), i.get("item")) for i in items]
    want = [(c.name, c.url) for c in expected[:-1]] + [(expected[-1].name, None)]
    if got != want:
        add("error", f"breadcrumb {got} does not match the registry trail {want}")
