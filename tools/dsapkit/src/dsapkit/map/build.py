"""make map: builds the area map offline from the pinned OpenStreetMap data.

Writes packages/map/dist/area-map.json (projected, simplified paths and points for the map
component) and area-map.svg (a preview in the brand colours). Fails when the pinned data no
longer matches its lock, or no longer matches the areas: a changed nearest centre needs a new
route, so run make map-fetch again.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from ..errors import BuildError
from ..jsonio import GENERATED, read_json, reset_dir, write_json, write_text
from ..paths import Paths
from ..site.model import Site
from ..tokens import TokenSet
from .geometry import Point, Projection, chain, path_d, simplify

ROUTE_END_TOLERANCE_M = 400  # OSRM snaps both ends to the nearest road


@dataclass(frozen=True)
class MapBuild:
    data: dict[str, Any]
    files: list[Path]
    warnings: list[str]  # commutes in areas.json that the road routes disagree with (commute_warnings)


def _clip(line: list[Point], box: tuple[float, float, float, float]) -> list[list[Point]]:
    """Splits a line into the runs that pass through a box, keeping one point beyond each edge."""
    x0, y0, x1, y1 = box
    inside = [x0 <= x <= x1 and y0 <= y <= y1 for x, y in line]
    runs: list[list[Point]] = []
    current: list[Point] = []
    for i, p in enumerate(line):
        near = inside[i] or (i > 0 and inside[i - 1]) or (i + 1 < len(line) and inside[i + 1])
        if near:
            current.append(p)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return [r for r in runs if len(r) >= 2]


def _load_source(paths: Paths) -> dict[str, Any]:
    lock = read_json(paths.map_lock, "run make map-fetch")
    source = {}
    for name, digest in lock["files"].items():
        path = paths.map_source / f"{name}.json"
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise BuildError(f"packages/map/source/{name}.json does not match map.lock.json; run make map-fetch")
        source[name] = read_json(path)["data"]
    return {"lock": lock, **source}


def check_map(site: Site, source: dict[str, Any]) -> list[str]:
    problems = []
    places, routes = source["places"], source["routes"]
    for aid, area in site.areas.items():
        if aid not in places["areas"]:
            problems.append(f"map: no point for area {aid}; run make map-fetch")
        if area["commute"].get("localCentre"):
            continue
        missing = [cid for cid in site.centres if cid not in routes.get(aid, {})]
        if missing:
            problems.append(f"map: no route from {aid} to {', '.join(missing)}; run make map-fetch")
    for cid in site.centres:
        if cid not in places["centres"]:
            problems.append(f"map: no pin for centre {cid}; run make map-fetch")
    return problems


def commute_warnings(site: Site, source: dict[str, Any], limits: dict[str, float]) -> list[str]:
    """Where packages/site/areas.json disagrees with the road routes from the pinned centres: a
    distance off by more than the limits in map.json, or another centre nearer by road. D-SAP
    decides; the map only reports."""
    warnings = []
    for aid, area in site.areas.items():
        by_centre = source["routes"].get(aid)
        if not by_centre or area["nearestCentre"] not in by_centre:
            continue
        nearest = area["nearestCentre"]
        stated = next((r for r in area["commute"]["routes"] if r["centre"] == nearest), None)
        road = by_centre[nearest]["km"]
        if stated and abs(road - stated["km"]) > max(limits["absoluteKm"], limits["relative"] * stated["km"]):
            warnings.append(f"{aid}: areas.json says {stated['km']} km to {nearest}; by road from the pinned centre it is {road} km")
        closer = min(by_centre, key=lambda cid: by_centre[cid]["km"])
        if closer != nearest and road - by_centre[closer]["km"] > limits["absoluteKm"]:
            warnings.append(f"{aid}: by road, {closer} ({by_centre[closer]['km']} km) is nearer than its assigned "
                            f"centre {nearest} ({road} km)")
    return warnings


def build_map(paths: Paths, site: Site, tokens: TokenSet) -> MapBuild:
    config = read_json(paths.map_config)
    source = _load_source(paths)
    problems = check_map(site, source)
    s, w, n, e = source["lock"]["bounds"]
    proj = Projection((s + n) / 2, (w + e) / 2)
    (x0, y0), (x1, y1) = proj.metres(w, s), proj.metres(e, n)
    scale = config["svg"]["width"] / (x1 - x0)
    width, height = config["svg"]["width"], (y1 - y0) * scale
    decimals = config["svg"]["decimals"]
    tol = config["simplifyMetres"]

    def to_svg(points_m: list[Point]) -> list[Point]:
        return [((x - x0) * scale, (y1 - y) * scale) for x, y in points_m]

    def metres(line: list[list[float]]) -> list[Point]:
        return [proj.metres(lon, lat) for lon, lat in line]

    box = (x0, y0, x1, y1)
    rivers = [path_d(to_svg(simplify(run, tol["river"])), decimals)
              for line in chain([metres(r["line"]) for r in source["rivers"]]) for run in _clip(line, box)]
    kinds = sorted({r["kind"] for r in source["roads"]})
    roads = [{"kind": kind, "d": path_d(to_svg(simplify(run, tol["road"])), decimals)}
             for kind in kinds
             for line in chain([metres(r["line"]) for r in source["roads"] if r["kind"] == kind])
             for run in _clip(line, box)]

    def point(lonlat: list[float]) -> dict[str, float]:
        (x, y), = to_svg([proj.metres(*lonlat)])
        return {"x": round(x, decimals), "y": round(y, decimals)}

    centres = {cid: {"id": cid, **point(c["lonlat"]), "approximate": c["approximate"]} for cid, c in source["places"]["centres"].items()}
    # An area with a centre of its own is shown by that centre's pin, not by a second point beside it.
    areas = []
    for aid, p in source["places"]["areas"].items():
        if aid not in site.areas:
            continue
        local = site.areas[aid]["commute"].get("localCentre")
        areas.append({"id": aid, "centre": local, **{k: centres[local][k] for k in ("x", "y")}} if local
                     else {"id": aid, **point(p["lonlat"])})
    routes = []
    for aid, by_centre in source["routes"].items():
        if aid not in site.areas or problems:
            continue
        cid = site.areas[aid]["nearestCentre"]
        r = {"centre": cid, **by_centre[cid]}
        line = metres(r["line"])
        end = proj.metres(*source["places"]["centres"][cid]["lonlat"])
        if math.dist(line[-1], end) > ROUTE_END_TOLERANCE_M:
            problems.append(f"map: the route from {aid} ends {math.dist(line[-1], end):.0f} m from its centre; run make map-fetch")
        routes.append({"area": aid, "centre": r["centre"], "km": r["km"], "d": path_d(to_svg(simplify(line, tol["route"])), decimals)})
    if problems:
        raise BuildError("area map problems:\n  " + "\n  ".join(problems))

    style = {k: v for k, v in config["style"].items() if not k.startswith("$")}
    data = {"$generated": GENERATED.format(source="packages/map via make map"), "fetched": source["lock"]["fetched"],
            "attribution": config["attribution"], "licence": config["licence"],
            "viewBox": [0, 0, width, round(height, decimals)], "style": style, "rivers": rivers, "roads": roads,
            "areas": areas, "centres": list(centres.values()), "routes": routes}
    out = reset_dir(paths.map_dist)
    write_json(out / "area-map.json", data)
    write_text(out / "area-map.svg", _preview_svg(data, site, tokens, style))
    warnings = commute_warnings(site, source, config["commuteCheck"])
    return MapBuild(data, [out / "area-map.json", out / "area-map.svg"], warnings)


def _preview_svg(data: dict[str, Any], site: Site, tokens: TokenSet, style: dict[str, Any]) -> str:
    """A preview of the map in the brand colours. The site draws its own from area-map.json."""
    def c(path: str) -> str:
        node: Any = tokens.tree
        for key in path.split("."):
            node = node[key]
        return node

    _, _, w, h = data["viewBox"]
    font = ", ".join(tokens.tree["font"]["family"]["body"])
    gap = style["area"] * 2
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="{escape(font)}">',
             f"<!-- {GENERATED.format(source='packages/map via make map')} -->",
             f'<rect width="{w}" height="{h}" fill="{c("surface.ink.bg")}"/>']
    parts += [f'<path d="{r["d"]}" fill="none" stroke="{c("color.stone.600")}" '
              f'stroke-width="{style["road"]["primary" if r["kind"] == "primary" else "major"]}" stroke-linecap="round"/>' for r in data["roads"]]
    parts += [f'<path d="{d}" fill="none" stroke="{c("color.river.500")}" stroke-width="{style["river"]}" '
              f'stroke-linecap="round" stroke-linejoin="round"/>' for d in data["rivers"]]
    parts += [f'<path d="{r["d"]}" fill="none" stroke="{c("color.brass.400")}" stroke-width="{style["route"]}" '
              f'stroke-dasharray="{style["routeDash"]}" stroke-linecap="round"/>' for r in data["routes"]]
    for a in data["areas"]:
        if a.get("centre"):
            continue  # drawn as its centre's pin
        name = escape(site.areas[a["id"]]["names"]["en"])
        parts.append(f'<circle cx="{a["x"]}" cy="{a["y"]}" r="{style["area"]}" fill="{c("color.chalk.50")}"/>'
                     f'<text x="{a["x"] + gap}" y="{a["y"] + style["area"]}" font-size="{style["label"]}" fill="{c("color.chalk.100")}">{name}</text>')
    for ce in data["centres"]:
        name = escape(site.centres[ce["id"]]["names"]["en"].split(", ")[-1]) + (" (approximate)" if ce["approximate"] else "")
        parts.append(f'<circle cx="{ce["x"]}" cy="{ce["y"]}" r="{style["centre"]}" fill="{c("color.brass.300")}" '
                     f'stroke="{c("color.brass.700")}" stroke-width="{style["centreRing"]}"/>'
                     f'<text x="{ce["x"] + style["centre"] + gap / 2}" y="{ce["y"] - style["centre"]}" font-size="{style["centreLabel"]}" '
                     f'font-weight="700" fill="{c("color.brass.200")}">{name}</text>')
    parts.append(f'<text x="{w - gap}" y="{h - gap}" font-size="{style["attribution"]}" text-anchor="end" '
                 f'fill="{c("color.stone.300")}">{escape(data["attribution"])}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"
