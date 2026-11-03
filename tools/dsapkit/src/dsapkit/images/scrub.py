"""Take everything personal out of images, and check that nothing is left.

Phone photos and videos carry hidden data: where they were taken (GPS), when, which phone, a
thumbnail, sometimes a second hidden copy of the picture. Every image the site ships goes through
`scrub`, which rebuilds the file from only the parts needed to draw it (JPEG, PNG and WebP, losslessly:
the picture itself is not re-encoded). `metadata_found` reads a file as shipped and says what is still
in it; make media and make web-lint use it on the final files, not on the originals.

What stays: the picture data, the parts a decoder needs, and, if the manifest says so
(scrub.keepColourProfile), the colour profile, because dropping it can change how the colours look.
What goes: EXIF, XMP, IPTC, comments, thumbnails, maker notes, text chunks, timestamps, and anything
stored after the end of the picture.

A photo that is only upright because of its EXIF orientation tag cannot be scrubbed: removing the tag
would show it sideways, and rotating a JPEG without losing quality needs a tool we do not depend on.
It is refused with a request to save it upright.
"""

from __future__ import annotations

import struct
from typing import Iterator

from ..errors import BuildError
from .info import boxes, image_type, is_mp4

_STANDALONE = {0x01, *range(0xD0, 0xDA)}  # TEM, RSTn, SOI, EOI: no length field
_JPEG_STRUCTURE = {0xC4, 0xCC, 0xDA, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF, *(m for m in range(0xC0, 0xD0) if m not in (0xC8,))}
_PNG_KEEP = {b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND", b"gAMA", b"cHRM", b"sRGB", b"cICP", b"acTL", b"fcTL", b"fdAT"}
_WEBP_KEEP = {b"VP8 ", b"VP8L", b"VP8X", b"ALPH", b"ANIM", b"ANMF"}
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_ICC = "colour profile"


def _orientation(tiff: bytes) -> int | None:
    """The EXIF orientation (1 to 8) in a TIFF block, or None when there is none."""
    if len(tiff) < 8 or tiff[:2] not in (b"II", b"MM"):
        return None
    end = "<" if tiff[:2] == b"II" else ">"
    try:
        (offset,) = struct.unpack(end + "I", tiff[4:8])
        (count,) = struct.unpack(end + "H", tiff[offset:offset + 2])
        for n in range(count):
            at = offset + 2 + 12 * n
            tag, kind, _, value = struct.unpack(end + "HHII", tiff[at:at + 12])
            if tag == 0x0112 and kind == 3:
                return value >> 16 if end == ">" else value & 0xFFFF
    except struct.error:
        return None
    return None


def _refuse_sideways(tiff: bytes) -> None:
    turn = _orientation(tiff)
    if turn not in (None, 1):
        raise BuildError("this photo is upright only because of a hidden orientation tag (EXIF orientation "
                         f"{turn}). Rotate it upright in Photos or Preview, export it again, and add the new file.")


# JPEG ---------------------------------------------------------------------------------------------

def _jpeg_parts(data: bytes) -> tuple[list[tuple[int | None, bytes]], int]:
    """(marker, payload) for each segment, and (None, entropy-coded bytes) after each scan header; plus where the picture ends."""
    if data[:2] != b"\xff\xd8":
        raise BuildError("not a JPEG")
    parts: list[tuple[int | None, bytes]] = []
    i, n = 2, len(data)
    while i < n:
        if data[i] != 0xFF:
            raise BuildError("JPEG is damaged: expected a marker")
        while i < n and data[i] == 0xFF:
            i += 1
        marker, i = data[i], i + 1
        if marker == 0xD9:
            return parts + [(marker, b"")], i
        if marker in _STANDALONE:
            parts.append((marker, b""))
            continue
        (length,) = struct.unpack(">H", data[i:i + 2])
        parts.append((marker, data[i + 2:i + length]))
        i += length
        if marker == 0xDA:
            j = i
            while j < n:
                if data[j] == 0xFF and j + 1 < n and (data[j + 1] == 0 or 0xD0 <= data[j + 1] <= 0xD7 or data[j + 1] == 0xFF):
                    j += 2 if data[j + 1] != 0xFF else 1
                    continue
                if data[j] == 0xFF:
                    break
                j += 1
            parts.append((None, data[i:j]))
            i = j
    raise BuildError("JPEG has no end marker")


def _jpeg_rebuild(data: bytes, keep_profile: bool) -> tuple[bytes, list[str]]:
    parts, end = _jpeg_parts(data)
    out, removed = [b"\xff\xd8"], []
    for marker, payload in parts:
        if marker is None:
            out.append(payload)
        elif marker in _STANDALONE:
            out.append(bytes([0xFF, marker]))
        else:
            kept = payload
            if marker in _JPEG_STRUCTURE:
                pass
            elif marker == 0xE0 and payload[:5] == b"JFIF\0":
                if len(payload) > 14 and (payload[12] or payload[13]):  # a thumbnail picture inside the header
                    removed.append("thumbnail")
                kept = payload[:12] + b"\0\0"
            elif marker == 0xEE and payload[:5] == b"Adobe":
                pass  # tells a decoder how to read the colours; no personal data
            elif marker == 0xE2 and payload[:12] == b"ICC_PROFILE\0" and keep_profile:
                pass
            else:
                if marker == 0xE1 and payload[:6] == b"Exif\0\0":
                    _refuse_sideways(payload[6:])
                removed.append(_jpeg_label(marker, payload))
                continue
            out.append(bytes([0xFF, marker]) + struct.pack(">H", len(kept) + 2) + kept)
    if end < len(data):
        removed.append("data after the end of the picture")
    return b"".join(out), sorted(set(removed))


def _jpeg_label(marker: int, payload: bytes) -> str:
    if marker == 0xE1:
        return "EXIF" if payload[:6] == b"Exif\0\0" else "XMP" if b"xmp" in payload[:40].lower() else "metadata (APP1)"
    if marker == 0xE2 and payload[:12] == b"ICC_PROFILE\0":
        return _ICC
    if marker == 0xED:
        return "IPTC"
    if marker == 0xFE:
        return "comment"
    return f"metadata (APP{marker - 0xE0})" if 0xE0 <= marker <= 0xEF else f"unknown segment {marker:#04x}"


# PNG ----------------------------------------------------------------------------------------------

def _png_chunks(data: bytes) -> Iterator[tuple[bytes, bytes]]:
    """(type, the whole chunk as stored) for each chunk up to IEND."""
    if data[:8] != _PNG_SIGNATURE:
        raise BuildError("not a PNG")
    i = 8
    while i + 12 <= len(data):
        (length,) = struct.unpack(">I", data[i:i + 4])
        kind, whole = data[i + 4:i + 8], data[i:i + 12 + length]
        yield kind, whole
        i += 12 + length
        if kind == b"IEND":
            return
    raise BuildError("PNG has no end chunk")


def _png_rebuild(data: bytes, keep_profile: bool) -> tuple[bytes, list[str]]:
    out, removed, last = [_PNG_SIGNATURE], [], 8
    for kind, whole in _png_chunks(data):
        last += len(whole)
        if kind in _PNG_KEEP or (kind == b"iCCP" and keep_profile):
            out.append(whole)
            continue
        if kind == b"eXIf":
            _refuse_sideways(whole[8:-4])
        removed.append(_ICC if kind == b"iCCP" else kind.decode("latin-1"))
    if last < len(data):
        removed.append("data after the end of the picture")
    return b"".join(out), sorted(set(removed))


# WebP ---------------------------------------------------------------------------------------------

def _webp_rebuild(data: bytes, keep_profile: bool) -> tuple[bytes, list[str]]:
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise BuildError("not a WebP")
    end = min(len(data), 8 + struct.unpack("<I", data[4:8])[0])
    chunks, removed, i = [], [], 12
    while i + 8 <= end:
        kind, (size,) = data[i:i + 4], struct.unpack("<I", data[i + 4:i + 8])
        payload = data[i + 8:i + 8 + size]
        i += 8 + size + (size & 1)
        if kind == b"EXIF":
            _refuse_sideways(payload[6:] if payload[:6] == b"Exif\0\0" else payload)
        if kind in _WEBP_KEEP or (kind == b"ICCP" and keep_profile):
            if kind == b"VP8X" and payload:
                flags = payload[0] & ~0x0C & (0xFF if keep_profile else ~0x20)  # clear the EXIF and XMP flags
                payload = bytes([flags]) + payload[1:]
            chunks.append(kind + struct.pack("<I", len(payload)) + payload + (b"\0" if len(payload) & 1 else b""))
        else:
            removed.append(_ICC if kind == b"ICCP" else kind.decode("latin-1").strip())
    if i < len(data):
        removed.append("data after the end of the picture")
    body = b"WEBP" + b"".join(chunks)
    return b"RIFF" + struct.pack("<I", len(body)) + body, sorted(set(removed))


# Public -------------------------------------------------------------------------------------------

_REBUILD = {"image/jpeg": _jpeg_rebuild, "image/png": _png_rebuild, "image/webp": _webp_rebuild}


def scrub(data: bytes, keep_profile: bool = True) -> bytes:
    """The same picture with nothing but what is needed to draw it."""
    return _REBUILD[image_type(data)](data, keep_profile)[0]


def metadata_found(data: bytes, keep_profile: bool = True) -> list[str]:
    """What a shipped file still carries beyond its picture: an empty list means it is clean."""
    if is_mp4(data):
        return mp4_metadata_found(data)
    return _REBUILD[image_type(data)](data, keep_profile)[1]


# MP4 ----------------------------------------------------------------------------------------------

_MP4_PERSONAL = {b"udta": "user data", b"meta": "metadata", b"uuid": "extension data (often XMP)", b"XMP_": "XMP",
                 b"\xa9xyz": "location", b"loci": "location", b"ilst": "tags", b"keys": "tags", b"cprt": "copyright note"}
_MP4_TIMED = (b"mvhd", b"tkhd", b"mdhd")


def _empty_user_data(data: bytes, begin: int, stop: int) -> bool:
    """A user-data box that is only the empty shell some muxers write: one meta box holding a handler and an empty tag list."""
    children = list(boxes(data, begin, stop))
    if [k for k, _, _ in children] != [b"meta"]:
        return False
    _, start, end = children[0]
    inner = list(boxes(data, start + 4, end))  # a meta box starts with 4 bytes of version and flags
    return [k for k, _, _ in inner] == [b"hdlr", b"ilst"] and inner[1][1] == inner[1][2]


def mp4_metadata_found(data: bytes) -> list[str]:
    """Boxes that hold where, when or who, and any creation or modification time that is not zero."""
    found: set[str] = set()

    def walk(start: int, end: int) -> None:
        for kind, begin, stop in boxes(data, start, end):
            if kind == b"udta" and _empty_user_data(data, begin, stop):
                continue
            if kind in _MP4_PERSONAL:
                found.add(_MP4_PERSONAL[kind])
                if kind == b"udta":
                    walk(begin, stop)  # say what is in it, such as a location
            elif kind in _MP4_TIMED and stop - begin >= 12:
                span = 16 if data[begin] == 1 else 8  # creation and modification time: 64-bit in version 1, else 32-bit
                if any(data[begin + 4:begin + 4 + span]):
                    found.add("creation or modification time")
            elif kind in (b"moov", b"trak", b"mdia"):
                walk(begin, stop)

    walk(0, len(data))
    return sorted(found)
