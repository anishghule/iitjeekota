"""Read the parts of a TrueType/OpenType font that dsapkit needs.

Tables read: head, hhea, maxp, OS/2, hmtx, cmap (formats 4 and 12), loca and the
glyf headers. Accepts sfnt bytes (.ttf, .otf, first face of a .ttc); woff2 is
compressed and not supported here, which is why the render cache keeps TTFs.
"""

from __future__ import annotations

import struct
from functools import cached_property
from pathlib import Path

from ..errors import BuildError

SFNT_TAGS = (b"\x00\x01\x00\x00", b"OTTO", b"true")

# English letter and space frequencies, used to weight the average character
# width (the method Capsize and Next.js use to size fallback fonts).
CHAR_FREQUENCY: dict[str, float] = {
    " ": 0.1818, "a": 0.0668, "b": 0.0122, "c": 0.0228, "d": 0.0348, "e": 0.1039,
    "f": 0.0182, "g": 0.0165, "h": 0.0499, "i": 0.0570, "j": 0.0013, "k": 0.0063,
    "l": 0.0329, "m": 0.0197, "n": 0.0552, "o": 0.0614, "p": 0.0158, "q": 0.0008,
    "r": 0.0490, "s": 0.0518, "t": 0.0740, "u": 0.0225, "v": 0.0080, "w": 0.0193,
    "x": 0.0012, "y": 0.0162, "z": 0.0006,
}


def is_sfnt(data: bytes) -> bool:
    return data[:4] in SFNT_TAGS or data[:4] == b"ttcf"


class Face:
    """One font face. Values are in font units unless a method says otherwise."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        base = 0
        if data[:4] == b"ttcf":
            (base,) = struct.unpack_from(">I", data, 12)
        if data[base:base + 4] not in SFNT_TAGS:
            raise BuildError("not a TrueType/OpenType font (woff2 must be decompressed first)")
        (count,) = struct.unpack_from(">H", data, base + 4)
        self._tables: dict[str, tuple[int, int]] = {}
        for i in range(count):
            tag, _checksum, offset, length = struct.unpack_from(">4sIII", data, base + 12 + i * 16)
            self._tables[tag.decode("latin-1")] = (offset, length)

    @classmethod
    def from_path(cls, path: Path) -> Face:
        return cls(path.read_bytes())

    # ------------------------------------------------------------ low level

    def _table(self, tag: str) -> int:
        if tag not in self._tables:
            raise BuildError(f"font has no {tag} table")
        offset, length = self._tables[tag]
        if offset + length > len(self._data):
            raise BuildError(f"font table {tag} runs past the end of the file")
        return offset

    def _u16(self, offset: int) -> int:
        return struct.unpack_from(">H", self._data, offset)[0]

    def _i16(self, offset: int) -> int:
        return struct.unpack_from(">h", self._data, offset)[0]

    def _u32(self, offset: int) -> int:
        return struct.unpack_from(">I", self._data, offset)[0]

    # ------------------------------------------------------------ metrics

    @cached_property
    def units_per_em(self) -> int:
        return self._u16(self._table("head") + 18)

    @cached_property
    def ascender(self) -> int:
        return self._i16(self._table("hhea") + 4)

    @cached_property
    def descender(self) -> int:
        return self._i16(self._table("hhea") + 6)

    @cached_property
    def line_gap(self) -> int:
        return self._i16(self._table("hhea") + 8)

    @cached_property
    def _os2_heights(self) -> tuple[int, int]:
        os2 = self._table("OS/2")
        if self._u16(os2) >= 2:
            return self._i16(os2 + 86), self._i16(os2 + 88)
        return 0, 0

    @cached_property
    def x_height(self) -> int:
        value = self._os2_heights[0]
        return value or self._glyph_top("x")

    @cached_property
    def cap_height(self) -> int:
        value = self._os2_heights[1]
        return value or self._glyph_top("H")

    @cached_property
    def avg_width(self) -> float:
        total = weight = 0.0
        for ch, freq in CHAR_FREQUENCY.items():
            gid = self.cmap.get(ord(ch))
            if gid is not None:
                total += self.advances[gid] * freq
                weight += freq
        if not weight:
            raise BuildError("font has no Latin lowercase glyphs to measure")
        return total / weight

    # ------------------------------------------------------------ glyphs

    @cached_property
    def cmap(self) -> dict[int, int]:
        base = self._table("cmap")
        records = [(self._u16(base + 4 + i * 8), self._u16(base + 6 + i * 8), self._u32(base + 8 + i * 8))
                   for i in range(self._u16(base + 2))]
        preference = {(3, 10): 0, (3, 1): 1}
        for platform, encoding, offset in sorted(records, key=lambda r: preference.get((r[0], r[1]), 2 if r[0] == 0 else 9)):
            sub = base + offset
            fmt = self._u16(sub)
            if fmt == 4:
                return self._cmap4(sub)
            if fmt == 12:
                return self._cmap12(sub)
        raise BuildError("font has no supported cmap subtable")

    def _cmap4(self, sub: int) -> dict[int, int]:
        seg_x2 = self._u16(sub + 6)
        ends = sub + 14
        starts = ends + seg_x2 + 2
        deltas = starts + seg_x2
        ranges = deltas + seg_x2
        out: dict[int, int] = {}
        for i in range(seg_x2 // 2):
            end, start = self._u16(ends + 2 * i), self._u16(starts + 2 * i)
            delta, range_pos = self._i16(deltas + 2 * i), ranges + 2 * i
            range_offset = self._u16(range_pos)
            if start == 0xFFFF:
                continue
            for code in range(start, end + 1):
                if range_offset == 0:
                    gid = (code + delta) & 0xFFFF
                else:
                    gid = self._u16(range_pos + range_offset + 2 * (code - start))
                    gid = (gid + delta) & 0xFFFF if gid else 0
                if gid:
                    out[code] = gid
        return out

    def _cmap12(self, sub: int) -> dict[int, int]:
        out: dict[int, int] = {}
        for i in range(self._u32(sub + 12)):
            start, end, gid = struct.unpack_from(">III", self._data, sub + 16 + i * 12)
            for code in range(start, min(end, 0x10FFFF) + 1):
                out[code] = gid + (code - start)
        return out

    @cached_property
    def advances(self) -> list[int]:
        count = self._u16(self._table("maxp") + 4)
        n_metrics = self._u16(self._table("hhea") + 34)
        hmtx = self._table("hmtx")
        widths = [self._u16(hmtx + 4 * i) for i in range(n_metrics)]
        widths.extend([widths[-1]] * max(0, count - n_metrics))
        return widths

    def glyph_bounds(self, char: str) -> tuple[int, int, int, int] | None:
        gid = self.cmap.get(ord(char))
        if gid is None or "glyf" not in self._tables:
            return None
        long_offsets = self._i16(self._table("head") + 50) == 1
        loca = self._table("loca")
        if long_offsets:
            start, end = self._u32(loca + 4 * gid), self._u32(loca + 4 * gid + 4)
        else:
            start, end = 2 * self._u16(loca + 2 * gid), 2 * self._u16(loca + 2 * gid + 2)
        if start == end:
            return None
        g = self._table("glyf") + start
        return self._i16(g + 2), self._i16(g + 4), self._i16(g + 6), self._i16(g + 8)

    def _glyph_top(self, char: str) -> int:
        bounds = self.glyph_bounds(char)
        return bounds[3] if bounds else 0

    def advance(self, text: str) -> int:
        """Sum of glyph advances, without shaping.

        Kerning and conjunct substitution only ever make real text narrower, so
        this is a safe upper bound for line breaking.
        """
        notdef = self.advances[0]
        return sum(self.advances[self.cmap[ord(c)]] if ord(c) in self.cmap else notdef for c in text)

    def describe(self, bounds_for: str = "") -> dict[str, object]:
        return {
            "unitsPerEm": self.units_per_em, "ascender": self.ascender, "descender": self.descender,
            "lineGap": self.line_gap, "xHeight": self.x_height, "capHeight": self.cap_height,
            "avgWidth": round(self.avg_width, 3),
            "glyphBounds": {c: list(b) for c in bounds_for if (b := self.glyph_bounds(c))},
        }


def fallback_overrides(web: Face, fallback: Face) -> dict[str, float]:
    """Overrides that make `fallback` take the same space as `web` (size by average width, then line metrics)."""
    size_adjust = (web.avg_width / web.units_per_em) / (fallback.avg_width / fallback.units_per_em)
    scaled_em = web.units_per_em * size_adjust
    return {
        "sizeAdjust": round(size_adjust * 100, 2),
        "ascentOverride": round(web.ascender / scaled_em * 100, 2),
        "descentOverride": round(abs(web.descender) / scaled_em * 100, 2),
        "lineGapOverride": round(web.line_gap / scaled_em * 100, 2),
    }


def x_height_match(reference: Face, other: Face) -> float:
    """size-adjust percentage that gives `other` the x-height of `reference`."""
    if not other.x_height:
        raise BuildError("font has no x-height to match")
    return round((reference.x_height / reference.units_per_em) / (other.x_height / other.units_per_em) * 100, 2)
