"""Vendor the site's woff2 files and pin them in fonts.lock.json."""

from __future__ import annotations

import hashlib

from ..errors import BuildError
from ..jsonio import GENERATED, read_json, write_bytes, write_json
from ..paths import Paths
from .config import FontsConfig
from .google import GoogleFonts


def fetch_fonts(paths: Paths, cfg: FontsConfig, client: GoogleFonts) -> list[dict]:
    entries: list[dict] = []
    keep: set[str] = set()
    for fam in cfg.families:
        faces = [f for f in client.web_faces(fam.query) if f.subset in fam.subsets]
        missing = set(fam.subsets) - {f.subset for f in faces}
        if missing:
            raise BuildError(f"{fam.family}: Google Fonts returned no {sorted(missing)} subset")
        for face in faces:
            data = client.woff2(face.url)
            name = f"{fam.slug}-{face.subset}-{face.weight.replace(' ', '-')}.woff2"
            write_bytes(paths.fonts_dir / name, data)
            keep.add(name)
            entries.append({
                "family": fam.family, "role": fam.role, "subset": face.subset, "style": face.style,
                "weight": face.weight, "stretch": face.stretch, "unicodeRange": face.unicode_range,
                "file": name, "url": face.url, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            })
        licence = f"{fam.slug}-LICENCE.txt"
        write_bytes(paths.fonts_dir / licence, client.text(fam.licence_url))
        keep.add(licence)
    for stale in paths.fonts_dir.iterdir():
        if stale.name not in keep:
            stale.unlink()
    write_json(paths.fonts_lock, {"$generated": GENERATED.format(source="fonts.config.json"), "files": entries})
    return entries


def verify_fonts(paths: Paths) -> int:
    lock = read_json(paths.fonts_lock, "run make fonts")
    problems = []
    for entry in lock["files"]:
        path = paths.fonts_dir / entry["file"]
        if not path.exists():
            problems.append(f"missing {entry['file']}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            problems.append(f"hash mismatch {entry['file']}")
    if problems:
        raise BuildError("font files do not match fonts.lock.json:\n  " + "\n  ".join(problems))
    return len(lock["files"])
