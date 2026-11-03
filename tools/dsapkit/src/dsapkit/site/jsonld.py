"""Check the JSON-LD the builders produce against Google's rules (packages/site/jsonld-rules.json).

The rules come from Google's live documentation: which properties each type needs, and the format of
each value (a timestamp with its timezone, hh:mm:ss, an absolute URL, a country code and so on).
A page's graph passes when it has no errors; warnings and pending notes are reported, not fatal.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from .formats import check_format
from .jsonld_build import Built
from .links import breadcrumbs
from .model import Site


@dataclass(frozen=True)
class PageGraph:
    route: str
    locale: str
    built: Built

    @property
    def name(self) -> str:
        return f"{self.route} ({self.locale})"


@dataclass(frozen=True)
class Finding:
    page: str
    severity: str  # error, warning, pending
    message: str


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


def _strings(value: Any) -> list[str]:
    """The text values of a property: a string, or the strings in a list. Objects are checked as nodes of their own."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def _empty_strings(value: Any, path: str = "") -> list[str]:
    found = []
    if isinstance(value, dict):
        for k, v in value.items():
            found += _empty_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            found += _empty_strings(v, f"{path}[{i}]")
    elif isinstance(value, str) and not value.strip():
        found.append(path)
    return found


def check_graphs(site: Site, rules: dict[str, Any], graphs: list[PageGraph]) -> list[Finding]:
    findings: list[Finding] = []
    types, retired = rules["types"], rules["retired"]
    declared = {n["@id"] for g in graphs for n in _nodes(g.built.graph) if "@id" in n}

    def rule_for(name: str) -> dict[str, Any] | None:
        rule = types.get(name)
        return types.get(rule["sameAs"]) if rule and "sameAs" in rule else rule

    for page in graphs:
        graph = page.built.graph
        pending_props = {prop for prop, _ in page.built.pending}

        def add(severity: str, message: str, page: PageGraph = page) -> None:
            findings.append(Finding(page.name, severity, message))

        for prop, why in page.built.pending:
            add("pending", f"{prop} left out: {why}")
            if why.startswith("unknown"):
                add("error", f"{prop} refers to a fact that does not exist")
        if graph.get("@context") != "https://schema.org":
            add("error", "the graph needs @context https://schema.org")
        for path in _empty_strings(graph):
            add("error", f"{path} is an empty string")
        ids = [n["@id"] for n in _nodes(graph) if "@id" in n and len(n) > 1]
        for dup in sorted({i for i in ids if ids.count(i) > 1}):
            add("error", f"@id {dup} is defined more than once")
        for node in _nodes(graph):
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
                    missing = [p for p in rule.get("recommended", []) if p not in node and p not in pending_props]
                    if missing:
                        add("warning", f"{name} lacks recommended {', '.join(missing)}")
                _check_fields(name, rule, node, add)
                for prop, limit in rule.get("maxLength", {}).items():
                    if isinstance(node.get(prop), str) and len(node[prop]) > limit:
                        add("warning", f"{name}.{prop} is {len(node[prop])} characters; Google ignores it past {limit}")
                items = node.get("itemListElement")
                if isinstance(items, list):
                    _check_items(name, rule, items, add)
                if name == "GeoCoordinates":
                    for axis in ("latitude", "longitude"):
                        decimals = str(node.get(axis, "")).partition(".")[2]
                        if len(decimals) < rule["minDecimals"]:
                            add("error", f"geo {axis} needs at least {rule['minDecimals']} decimals")
                if rule is types["Organization"]:
                    _check_logo(rule, node, add)
            _check_dates(node, add)
        for ref in _refs(graph):
            if ref not in declared:
                add("error", f"reference to {ref} is not declared in any page's graph")
        for key, value in _url_values(graph, set(rules["urlKeys"])):
            if not value.startswith("https://"):
                add("error", f"{key} must be an absolute https URL: {value}")
        _check_breadcrumb(site, page, add)
    return findings


def _check_fields(name: str, rule: dict[str, Any], node: dict[str, Any], add: Callable[[str, str], None]) -> None:
    """Each listed property must hold a value of its documented format."""
    for prop, fmt in rule.get("fields", {}).items():
        for value in _strings(node.get(prop)):
            if not check_format(fmt, value):
                add("error", f"{name}.{prop} {value!r} is not a valid {fmt} (jsonld-rules.json formats)")


def _check_logo(rule: dict[str, Any], node: dict[str, Any], add: Callable[[str, str], None]) -> None:
    logo = node.get("logo")
    minimum = rule.get("minLogoPixels")
    if isinstance(logo, dict) and minimum and min(logo.get("width", 0), logo.get("height", 0)) < minimum:
        add("error", f"logo must be at least {minimum}x{minimum} px")


def _check_dates(node: dict[str, Any], add: Callable[[str, str], None]) -> None:
    published, modified = node.get("datePublished"), node.get("dateModified")
    if isinstance(published, str) and isinstance(modified, str) and check_format("datetime", published) and check_format("datetime", modified):
        if _utc(modified) < _utc(published):
            add("error", f"dateModified {modified} is before datePublished {published}")


def _utc(stamp: str) -> float:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


def _check_items(name: str, rule: dict[str, Any], items: list[Any], add: Callable[[str, str], None]) -> None:
    """A list's items, checked against the item rules of that list type."""
    if "minItems" in rule and len(items) < rule["minItems"]:
        add("warning", f"{name} has {len(items)} items; Google needs at least {rule['minItems']}")
    positions = [i.get("position") for i in items]
    if positions != list(range(1, len(items) + 1)):
        add("error", f"{name} positions must run 1 to {len(items)}, got {positions}")
    urls = [i["url"] for i in items if "url" in i]
    if len(set(urls)) != len(urls):
        add("error", f"{name} items must each have a unique url")
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


def _check_breadcrumb(site: Site, page: PageGraph, add: Callable[[str, str], None]) -> None:
    """The page's BreadcrumbList must equal the trail the registry builds for its route."""
    lists = [n for n in _nodes(page.built.graph) if "BreadcrumbList" in _types(n)]
    expected = breadcrumbs(site, site.routes[page.route], page.locale)
    if not lists:
        if expected:
            add("error", "page has a breadcrumb trail but no BreadcrumbList")
        return
    items = lists[0]["itemListElement"]
    got = [(i.get("name"), i.get("item")) for i in items]
    want = [(c.name, c.url) for c in expected[:-1]] + [(expected[-1].name, None)]
    if got != want:
        add("error", f"breadcrumb {got} does not match the registry trail {want}")
