"""docs/setup/media-to-add.md: the photos and videos D-SAP still has to put in place, with path and spec."""

from __future__ import annotations

from pathlib import Path

from ..errors import BuildError
from ..jsonio import GENERATED, write_text
from ..paths import Paths
from .library import Library, Slot

HEADER = "<!-- " + GENERATED.format(source="packages/media/manifest.json via make media") + " -->\n\n"


def _size(slot: Slot) -> str:
    spec = slot.spec
    if "minWidth" not in spec:
        return ""
    return f"{spec.get('orientation', '')}, at least {spec['minWidth']}x{spec['minHeight']}".strip(", ")


def write_media_todo(paths: Paths, library: Library, pages: dict[str, str]) -> Path:
    """Lists awaited slots, waiting first. pages maps route id to its English path, for "used on"."""
    slots = library.slots
    unknown = sorted({p for s in slots for p in s.used_on if p not in pages})
    if unknown:
        raise BuildError(f"packages/media/manifest.json usedOn names pages that do not exist: {', '.join(unknown)}")
    awaited = [s for s in slots if s.origin == "awaited"]
    missing = [s for s in awaited if not (paths.root / s.file).exists()]
    lines = [HEADER + "# Photos and videos to add", "",
             f"{len(missing)} of {len(awaited)} files still to add. Put each file at its path (same name, same "
             "extension), then run `make media-fetch`. It checks the type, size and orientation, and pins the file "
             "in `packages/media/media.lock.json`. To change what a slot needs, edit `packages/media/manifest.json`.", "",
             "Rules for every file:", "",
             "- Photos: JPEG, straight from the camera or phone, not resized or filtered. Videos: MP4 (H.264).",
             f"- Size limits: photos {library.limits['image'] // 1_000_000} MB, videos {library.limits['video'] // 1_000_000} MB.",
             "- Students' faces only with their parents' written consent. Keep the consent forms on file.",
             "- No phone numbers, prices or rank claims written in the picture; the site states those from the facts register.",
             ""]
    for title, group in (("Still to add", missing), ("Added", [s for s in awaited if s not in missing])):
        if not group:
            continue
        lines += [f"## {title}", "", "| Path | What it shows | Size | Used on |", "| --- | --- | --- | --- |"]
        for slot in group:
            used = ", ".join(f"`{pages[p]}`" for p in slot.used_on)
            shows = slot.spec.get("shows", "") + (f" {slot.note}" if slot.note else "")
            lines.append(f"| `{slot.file}` | {shows} | {_size(slot)} | {used} |")
        lines.append("")
    target = paths.root / "docs" / "setup" / "media-to-add.md"
    write_text(target, "\n".join(lines))
    return target

