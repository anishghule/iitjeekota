"""Type, width and height of PNG, JPEG, WebP and MP4 files, read from their headers."""

from __future__ import annotations

import struct

from ..errors import BuildError


def is_mp4(data: bytes) -> bool:
    return data[4:8] == b"ftyp"


def _boxes(data: bytes, start: int, end: int):
    """(type, content start, content end) of each MP4 box between start and end."""
    pos = start
    while pos + 8 <= end:
        size, kind = struct.unpack(">I4s", data[pos:pos + 8])
        header = 8
        if size == 1:
            size, header = struct.unpack(">Q", data[pos + 8:pos + 16])[0], 16
        elif size == 0:
            size = end - pos
        if size < header:
            return
        yield kind, pos + header, min(pos + size, end)
        pos += size


def mp4_size(data: bytes) -> tuple[int, int]:
    """Display size of the first video track, from its tkhd box.

    Width and height are 16.16 fixed point. Phones store upright video as landscape
    frames with a 90 or 270 degree matrix, so a quarter turn swaps the two.
    """
    for kind, start, end in _boxes(data, 0, len(data)):
        if kind != b"moov":
            continue
        for trak_kind, t_start, t_end in _boxes(data, start, end):
            if trak_kind != b"trak":
                continue
            for box, b_start, _b_end in _boxes(data, t_start, t_end):
                if box != b"tkhd":
                    continue
                matrix_at = b_start + (52 if data[b_start] == 1 else 40)
                a, b = struct.unpack(">ii", data[matrix_at:matrix_at + 8])
                width, height = struct.unpack(">II", data[matrix_at + 36:matrix_at + 44])
                if width and height:
                    quarter_turn = a == 0 and b != 0
                    return (height >> 16, width >> 16) if quarter_turn else (width >> 16, height >> 16)
    raise BuildError("MP4 has no video track with a frame size")


def media_type(data: bytes) -> str:
    return "video/mp4" if is_mp4(data) else image_type(data)


def media_size(data: bytes) -> tuple[int, int]:
    return mp4_size(data) if is_mp4(data) else image_size(data)


def image_size(data: bytes) -> tuple[int, int]:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X":
            w = int.from_bytes(data[24:27], "little") + 1
            h = int.from_bytes(data[27:30], "little") + 1
            return w, h
        if chunk == b"VP8 ":
            w, h = struct.unpack("<HH", data[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if chunk == b"VP8L":
            bits = int.from_bytes(data[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            length = struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + length
    raise BuildError("not a PNG, JPEG or WebP image")


def image_type(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    raise BuildError("not a PNG, JPEG or WebP image")
