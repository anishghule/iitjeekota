"""Minimal PNG reading and writing: 8-bit RGB or RGBA, not interlaced."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

from ..errors import BuildError

SIGNATURE = b"\x89PNG\r\n\x1a\n"
CHANNELS = {2: 3, 6: 4}  # colour type -> channels


@dataclass(frozen=True)
class Box:
    left: int
    top: int
    right: int   # exclusive
    bottom: int  # exclusive

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def square(self) -> tuple[float, float, float]:
        """(x, y, side) of the smallest square centred on this box that contains it."""
        side = max(self.width, self.height)
        return self.left + self.width / 2 - side / 2, self.top + self.height / 2 - side / 2, side


@dataclass(frozen=True)
class Pixels:
    width: int
    height: int
    channels: int
    rows: list[bytes]

    def rgba_rows(self) -> list[bytes]:
        if self.channels == 4:
            return self.rows
        return [bytes(b for i in range(0, len(row), 3) for b in (*row[i:i + 3], 255)) for row in self.rows]

    def alpha_box(self, threshold: int) -> Box:
        """Bounding box of pixels whose alpha is above `threshold` (the whole image if there is no alpha)."""
        if self.channels != 4:
            return Box(0, 0, self.width, self.height)
        left, top, right, bottom = self.width, self.height, -1, -1
        for y, row in enumerate(self.rows):
            alphas = row[3::4]
            xs = [x for x, a in enumerate(alphas) if a > threshold]
            if xs:
                left, right = min(left, xs[0]), max(right, xs[-1])
                top, bottom = min(top, y), y
        if right < 0:
            raise BuildError("image is fully transparent")
        return Box(left, top, right + 1, bottom + 1)


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def decode_png(data: bytes) -> Pixels:
    if data[:8] != SIGNATURE:
        raise BuildError("not a PNG file")
    pos, idat, header = 8, bytearray(), None
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
    if header is None:
        raise BuildError("PNG has no header")
    width, height, depth, colour, _comp, _filter, interlace = header
    if depth != 8 or colour not in CHANNELS or interlace:
        raise BuildError("only 8-bit, non-interlaced RGB or RGBA PNGs are supported")
    bpp = CHANNELS[colour]
    stride = width * bpp
    raw = zlib.decompress(bytes(idat))
    rows: list[bytes] = []
    prev = bytearray(stride)
    i = 0
    for _ in range(height):
        kind, line = raw[i], bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            left = line[x - bpp] if x >= bpp else 0
            up_left = prev[x - bpp] if x >= bpp else 0
            if kind == 1:
                line[x] = (line[x] + left) & 0xFF
            elif kind == 2:
                line[x] = (line[x] + prev[x]) & 0xFF
            elif kind == 3:
                line[x] = (line[x] + (left + prev[x]) // 2) & 0xFF
            elif kind == 4:
                line[x] = (line[x] + _paeth(left, prev[x], up_left)) & 0xFF
        rows.append(bytes(line))
        prev = line
    return Pixels(width, height, bpp, rows)


def _chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def encode_png(pixels: Pixels) -> bytes:
    """RGBA PNG with the Sub filter on every row (good for smooth images, cheap to compute)."""
    rows = pixels.rgba_rows()
    raw = bytearray()
    for row in rows:
        raw.append(1)
        raw += bytes(row[x] if x < 4 else (row[x] - row[x - 4]) & 0xFF for x in range(len(row)))
    header = struct.pack(">IIBBBBB", pixels.width, pixels.height, 8, 6, 0, 0, 0)
    return SIGNATURE + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + _chunk(b"IEND", b"")
