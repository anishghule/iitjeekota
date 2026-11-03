"""make map-fetch: downloads what the area map needs from OpenStreetMap services and pins it.

Places come from Nominatim (one request a second, as its policy asks), except a centre with a
confirmed geo fact, which uses that pin. The rivers and roads come from Overpass, and each area's
driving route to every centre from OSRM. Everything is stored as plain [lon, lat] lines in
packages/map/source, with SHA-256 hashes and the date in map.lock.json.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import time
import urllib.parse
from pathlib import Path
from typing import Any

from ..errors import BuildError
from ..jsonio import GENERATED, read_json, write_json
from ..net import https_get
from ..paths import Paths
from ..site.model import Site

MAX_BYTES = 24 * 1024 * 1024


class MapClient:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.allow = frozenset(config["allowedHosts"])

    def get(self, url: str) -> Any:
        return json.loads(https_get(url, allow=self.allow, user_agent=self.config["userAgent"], max_bytes=MAX_BYTES))

    def geocode(self, query: str) -> tuple[float, float, str]:
        url = self.config["endpoints"]["nominatim"] + "?" + urllib.parse.urlencode({"q": query, "format": "json", "limit": 1})
        hits = self.get(url)
        time.sleep(self.config["nominatimDelayMs"] / 1000)
        if not hits:
            raise BuildError(f"map: Nominatim found nothing for {query!r}; change that query in packages/map/map.json (geocode)")
        return float(hits[0]["lon"]), float(hits[0]["lat"]), hits[0].get("display_name", "")

    def overpass(self, query: str) -> list[dict[str, Any]]:
        """Tries each Overpass server in map.json order; the main one is often busy."""
        failures = []
        for endpoint in self.config["endpoints"]["overpass"]:
            try:
                return self.get(endpoint + "?" + urllib.parse.urlencode({"data": query}))["elements"]
            except BuildError as err:
                failures.append(str(err))
        raise BuildError("every Overpass server failed:\n  " + "\n  ".join(failures))

    def route(self, start: list[float], end: list[float]) -> dict[str, Any]:
        url = (f"{self.config['endpoints']['osrm']}/{start[0]},{start[1]};{end[0]},{end[1]}"
               "?overview=full&geometries=geojson")
        found = self.get(url)["routes"][0]
        # OSRM's duration is on empty roads, so it is the free-flow time in areas.json, never a 3 PM time.
        return {"km": round(found["distance"] / 1000, 2), "freeFlowMinutes": round(found["duration"] / 60),
                "line": found["geometry"]["coordinates"]}


def _places(client: MapClient, site: Site) -> dict[str, Any]:
    geo = client.config["geocode"]
    areas = {}
    for area in site.areas.values():
        query = geo["overrides"].get(area["id"]) or geo["hubs"][area["hub"]].format(name=area["names"]["en"])
        lon, lat, found = client.geocode(query)
        areas[area["id"]] = {"lonlat": [lon, lat], "query": query, "found": found}
    centres = {}
    for cid, centre in site.centres.items():
        pin, why = site.fact_value(centre["facts"]["geo"])
        if why is None:
            centres[cid] = {"lonlat": [pin["longitude"], pin["latitude"]], "from": f"fact {centre['facts']['geo']}", "approximate": False}
        else:
            query = geo["centres"].get(cid)
            if not query:
                raise BuildError(f"map: centre {cid} has no confirmed geo fact and no query in map.json geocode.centres")
            lon, lat, found = client.geocode(query)
            centres[cid] = {"lonlat": [lon, lat], "from": f"Nominatim: {query}", "found": found, "approximate": True}
    return {"areas": areas, "centres": centres}


def _bounds(places: dict[str, Any], margin: float) -> list[float]:
    points = [p["lonlat"] for group in places.values() for p in group.values()]
    lons, lats = [p[0] for p in points], [p[1] for p in points]
    return [min(lats) - margin, min(lons) - margin, max(lats) + margin, max(lons) + margin]  # south, west, north, east


def _ways(elements: list[dict[str, Any]], tag: str) -> list[dict[str, Any]]:
    return [{"kind": e["tags"].get(tag, ""), "line": [[g["lon"], g["lat"]] for g in e["geometry"]]}
            for e in elements if e.get("type") == "way" and e.get("geometry")]


def fetch_map(paths: Paths, site: Site) -> dict[str, Path]:
    config = read_json(paths.map_config)
    client = MapClient(config)
    places = _places(client, site)
    s, w, n, e = _bounds(places, config["marginDegrees"])
    box = f"({s},{w},{n},{e})"
    names = "|".join(config["rivers"]["names"])
    rivers = _ways(client.overpass(f'[out:json][timeout:90];way["waterway"="river"]["name"~"{names}",i]{box};out geom;'), "name")
    classes = "|".join(config["roads"]["classes"])
    roads = _ways(client.overpass(f'[out:json][timeout:90];way["highway"~"^({classes})$"]{box};out geom;'), "highway")
    routes = {}
    for aid, area in site.areas.items():
        if area["commute"].get("localCentre"):
            continue  # the centre is in the area itself; there is no route to draw
        # Routes to every centre, so make map can check which one is nearer by road.
        routes[aid] = {cid: client.route(places["areas"][aid]["lonlat"], place["lonlat"])
                       for cid, place in places["centres"].items()}

    paths.map_source.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, data in (("places", places), ("rivers", rivers), ("roads", roads), ("routes", routes)):
        target = paths.map_source / f"{name}.json"
        write_json(target, {"$source": f"OpenStreetMap via {config['endpoints']}", "data": data})
        written[name] = target
    lock = {name: hashlib.sha256(p.read_bytes()).hexdigest() for name, p in written.items()}
    write_json(paths.map_lock, {"$generated": GENERATED.format(source="make map-fetch"),
                                "fetched": datetime.date.today().isoformat(), "bounds": [s, w, n, e],
                                "attribution": config["attribution"], "files": lock})
    return written
