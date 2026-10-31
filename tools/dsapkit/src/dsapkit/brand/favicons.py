"""Favicons, app icons and the web app manifest, all rendered from the official medal."""

from __future__ import annotations

import struct
from pathlib import Path

from ..jsonio import read_json, reset_dir, write_bytes, write_json
from ..paths import Paths
from ..tokens import TokenSet
from .logo import OfficialLogo


def ico_container(images: list[tuple[int, bytes]]) -> bytes:
    """An .ico holding PNG images (read by every current browser)."""
    header = struct.pack("<HHH", 0, 1, len(images))
    entries, blobs = b"", b""
    offset = 6 + 16 * len(images)
    for size, data in images:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
        blobs += data
        offset += len(data)
    return header + entries + blobs


def build_favicons(paths: Paths, tokens: TokenSet, logo: OfficialLogo) -> list[Path]:
    cfg = read_json(paths.favicons_json)
    identity = read_json(paths.identity_json)
    background = tokens.tree["surface"][identity["iconSurface"]]["bg"]
    out = reset_dir(paths.brand_dist / "favicon")
    written = []
    for item in cfg["transparent"]:
        write_bytes(out / item["name"], logo.png(item["size"]))
        written.append(out / item["name"])
    write_bytes(out / cfg["ico"]["name"], ico_container([(s, logo.png(s)) for s in cfg["ico"]["sizes"]]))
    written.append(out / cfg["ico"]["name"])
    for item in cfg["plates"]:
        write_bytes(out / item["name"], logo.plate(item["size"], background, item["scale"]))
        written.append(out / item["name"])

    sizes = {i["name"]: i for i in cfg["transparent"] + cfg["plates"]}
    write_json(out / cfg["manifest"]["name"], {
        "name": identity["appName"],
        "short_name": identity["shortName"],
        "start_url": identity["startUrl"],
        "scope": "/",
        "display": cfg["manifest"]["display"],
        "background_color": background,
        "theme_color": background,
        "icons": [{"src": f"/{name}", "sizes": f"{sizes[name]['size']}x{sizes[name]['size']}", "type": "image/png",
                   **({"purpose": sizes[name]["purpose"]} if "purpose" in sizes[name] else {})}
                  for name in cfg["manifest"]["icons"]],
    })
    written.append(out / cfg["manifest"]["name"])
    return written
