"""Media slots from packages/media/manifest.json.

Origins:
  supplied   fetched once from its recorded source (an allowed HTTPS host or a
             repository path) into packages/media/assets and pinned in media.lock.json
  awaited    D-SAP puts the file at the slot's path; until then the slot is listed
             as waiting, and once the file is there make media-fetch pins it
  committed  the file is already in the repository at the slot's path, a clean copy
             of what D-SAP supplied (the note says what it came from). Pinned like the
             others, never fetched, no source: nothing is read from resources/, which is
             gitignored, and a file too large for git (raw phone video) is kept only as
             its encoded copy
  encoded    made by make media-encode from a clean copy of an original D-SAP supplied
             (source, a path under packages/media/originals); pinned like the others, but
             never fetched from its source: that is the unprocessed original
  generated  produced by make brand
  placeholder  a licensed stand-in fetched like a supplied file

Every slot that is not decorative needs alt text. A slot's spec (minimum size,
orientation) is checked as soon as its file exists.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import BuildError
from ..images.info import media_size, media_type
from ..images.scrub import metadata_found, scrub
from ..jsonio import GENERATED, read_json, write_bytes, write_json
from ..net import https_get
from ..paths import Paths

ORIGINS = {"supplied", "awaited", "committed", "encoded", "generated", "placeholder"}
KEPT_IN_REPOSITORY = ("supplied", "awaited", "committed", "encoded", "placeholder")  # files under packages/media/assets, pinned by hash
KIND_TYPES = {"image": {"image/png", "image/jpeg", "image/webp"}, "video": {"video/mp4"}}
USER_AGENT = "dsapkit/0.1 (media library)"


@dataclass(frozen=True)
class Slot:
    id: str
    origin: str
    kind: str
    file: str
    source: str
    alt: dict[str, str]
    decorative: bool
    placeholder: bool
    note: str
    draft_locales: tuple[str, ...] = ()
    spec: dict[str, Any] = field(default_factory=dict)
    used_on: tuple[str, ...] = ()
    placeholder_allowed: bool = False

    @property
    def pinned(self) -> bool:
        """Slots whose files live in the repository and are pinned by hash."""
        return self.origin in KEPT_IN_REPOSITORY


@dataclass(frozen=True)
class Library:
    slots: list[Slot]
    allow: frozenset[str]
    limits: dict[str, int]
    keep_profile: bool = True  # scrub.keepColourProfile: images keep their colour profile, nothing else hidden


def load_library(paths: Paths) -> Library:
    raw = read_json(paths.media_manifest)
    slots, seen, problems = [], set(), []
    for entry in raw["slots"]:
        sid = entry.get("id", "?")
        for key in ("id", "origin", "file", "credit", "licence", "placeholder"):
            if key not in entry:
                problems.append(f"{sid}: missing {key}")
        origin, kind = entry.get("origin"), entry.get("kind", "image")
        if origin not in ORIGINS:
            problems.append(f"{sid}: origin must be one of {sorted(ORIGINS)}")
        if kind not in KIND_TYPES:
            problems.append(f"{sid}: kind must be one of {sorted(KIND_TYPES)}")
        if origin in ("supplied", "encoded", "placeholder") and not entry.get("source"):
            problems.append(f"{sid}: a {origin} slot needs a source")
        if origin in KEPT_IN_REPOSITORY and not (paths.root / entry.get("file", "")).resolve().is_relative_to(paths.media_assets):
            problems.append(f"{sid}: files kept in the repository live under packages/media/assets")
        decorative = bool(entry.get("decorative"))
        alt = entry.get("alt") or {}
        if not decorative and (not alt or not all(isinstance(v, str) and v.strip() for v in alt.values())):
            problems.append(f"{sid}: needs alt text (or decorative: true)")
        if sid in seen:
            problems.append(f"{sid}: duplicate id")
        seen.add(sid)
        slots.append(Slot(sid, origin or "", kind, entry.get("file", ""), entry.get("source", ""), alt, decorative,
                          bool(entry.get("placeholder")), entry.get("note", ""), tuple(entry.get("draftLocales", [])),
                          entry.get("spec", {}), tuple(entry.get("usedOn", [])), bool(entry.get("placeholderAllowed"))))
    if problems:
        raise BuildError("packages/media/manifest.json:\n  " + "\n  ".join(problems))
    return Library(slots, frozenset(raw.get("allowedHosts", [])), raw["limits"], bool(raw.get("scrub", {}).get("keepColourProfile", True)))


def load_slots(paths: Paths) -> tuple[list[Slot], frozenset[str]]:
    library = load_library(paths)
    return library.slots, library.allow


def slot_path(paths: Paths, slot_id: str) -> Path:
    for slot in load_library(paths).slots:
        if slot.id == slot_id:
            path = paths.root / slot.file
            if not path.exists():
                raise BuildError(f"media slot {slot_id}: {slot.file} is missing (run make media-fetch or make brand)")
            return path
    raise BuildError(f"no media slot {slot_id!r} in packages/media/manifest.json")


def check_file(slot: Slot, data: bytes, limits: dict[str, int]) -> list[str]:
    """Type, size limit and spec of a slot's file."""
    try:
        kind_type = media_type(data)
        width, height = media_size(data)
    except BuildError as err:
        return [f"{slot.id}: {err}"]
    problems = []
    if kind_type not in KIND_TYPES[slot.kind]:
        problems.append(f"{slot.id}: expected {slot.kind} ({', '.join(sorted(KIND_TYPES[slot.kind]))}), got {kind_type}")
    if len(data) > limits[slot.kind]:
        problems.append(f"{slot.id}: {len(data) // 1_000_000} MB is over the {limits[slot.kind] // 1_000_000} MB limit for {slot.kind}s")
    spec = slot.spec
    if width < spec.get("minWidth", 0) or height < spec.get("minHeight", 0):
        problems.append(f"{slot.id}: {width}x{height} is smaller than {spec.get('minWidth', 0)}x{spec.get('minHeight', 0)}")
    orientation = spec.get("orientation")
    actual = "landscape" if width > height else "portrait" if height > width else "square"
    if orientation and orientation != actual:
        problems.append(f"{slot.id}: should be {orientation}, is {actual} ({width}x{height})")
    return problems


def _obtain(paths: Paths, slot: Slot, allow: frozenset[str], limits: dict[str, int]) -> bytes:
    if slot.source.startswith("https://"):
        return https_get(slot.source, allow=allow, user_agent=USER_AGENT, max_bytes=limits[slot.kind])
    source = (paths.root / slot.source).resolve()
    if not source.is_relative_to(paths.root) or not source.is_file():
        raise BuildError(f"{slot.id}: source {slot.source} is not a file inside the repository")
    return source.read_bytes()


def _clean(slot: Slot, target: Path, library: Library, problems: list[str]) -> bytes | None:
    """The file's bytes with nothing hidden in them. An image is rewritten without its metadata (where it was
    taken, when, by which phone) and the clean file is the one that is pinned and shipped; a video must
    already be clean (make media-encode makes it so). Returns None, with the reason in problems, if it cannot be."""
    data = target.read_bytes()
    if slot.kind == "image":
        try:
            clean = scrub(data, library.keep_profile)
        except BuildError as err:
            problems.append(f"{slot.id}: {err}")
            return None
        if clean != data:
            write_bytes(target, clean)
        return clean
    found = metadata_found(data)
    if found:
        problems.append(f"{slot.id}: the video still carries {', '.join(found)}; make it with make media-encode")
        return None
    return data


def fetch_media(paths: Paths, refresh: bool = False) -> tuple[list[dict], list[Path]]:
    """Fetch missing supplied files (or all, with refresh), pin every file present, remove files no slot uses.

    Returns the lock entries and the paths of removed files.
    """
    library = load_library(paths)
    entries, problems = [], []
    for slot in library.slots:
        if not slot.pinned:
            continue
        target = paths.root / slot.file
        if slot.origin not in ("awaited", "committed", "encoded") and (refresh or not target.exists()):
            write_bytes(target, _obtain(paths, slot, library.allow, library.limits))
        if not target.exists():
            continue  # awaited: D-SAP has not added it yet; encoded: make media-encode has not run; committed: reported by check_media
        data = _clean(slot, target, library, problems)
        if data is None:
            continue
        found = check_file(slot, data, library.limits)
        if found:
            problems += found
            continue
        width, height = media_size(data)
        entries.append({"id": slot.id, "file": slot.file, "source": slot.source or "added by D-SAP",
                        "type": media_type(data), "width": width, "height": height, "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest()})
    if problems:
        raise BuildError("media files do not meet their slot specs:\n  " + "\n  ".join(problems))
    used = {(paths.root / s.file).resolve() for s in library.slots if s.pinned}
    removed = [f for f in sorted(paths.media_assets.rglob("*")) if f.is_file() and f.resolve() not in used]
    for stale in removed:
        stale.unlink()
    write_json(paths.media_lock, {"$generated": GENERATED.format(source="packages/media/manifest.json"), "files": entries})
    return entries, removed


def check_media(paths: Paths, require_generated: bool = True) -> list[Slot]:
    """Pinned files match the lock; awaited files may be missing; generated files exist. Returns every slot."""
    library = load_library(paths)
    lock = {e["id"]: e for e in read_json(paths.media_lock, "run make media-fetch")["files"]}
    problems = []
    for slot in library.slots:
        path = paths.root / slot.file
        if slot.pinned:
            if not path.exists():
                if slot.origin == "encoded":
                    problems.append(f"{slot.id}: {slot.file} is not made yet; run make media-encode, then make media-fetch")
                elif slot.origin != "awaited":
                    problems.append(f"{slot.id}: {slot.file} is missing")
            elif slot.id not in lock:
                problems.append(f"{slot.id}: {slot.file} is new; run make media-fetch to check and pin it")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != lock[slot.id]["sha256"]:
                problems.append(f"{slot.id}: {slot.file} changed; run make media-fetch to check and pin it")
            elif found := metadata_found(path.read_bytes(), library.keep_profile):
                problems.append(f"{slot.id}: {slot.file} still carries {', '.join(found)}; run make media-fetch")
        elif require_generated and not path.exists():
            problems.append(f"{slot.id}: {slot.file} not built yet (run make brand)")
    if problems:
        raise BuildError("media check failed:\n  " + "\n  ".join(problems))
    return library.slots


def waiting(paths: Paths, slots: list[Slot]) -> list[Slot]:
    return [s for s in slots if s.origin == "awaited" and not (paths.root / s.file).exists()]
