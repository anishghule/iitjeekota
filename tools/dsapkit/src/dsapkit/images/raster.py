"""Image operations for small, sharp renditions: crop, gamma-correct downscale, sharpen, round mask.

Pixels are held as premultiplied, linear-light floats, which is what makes a
downscale correct: averaging sRGB values directly darkens fine bright detail
(the medal's relief) and smears edges. A downscale first averages whole blocks
(area filter, for the large integer part of the ratio), then resamples to the
exact size with a Lanczos-3 filter; an unsharp mask can then restore edge contrast.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from operator import mul

from ..tokens.colour import hex_rgba
from .png import Pixels

_TO_LINEAR = [((i / 255) / 12.92) if i / 255 <= 0.04045 else (((i / 255) + 0.055) / 1.055) ** 2.4 for i in range(256)]


def _to_srgb(v: float) -> int:
    v = 0.0 if v <= 0 else 1.0 if v >= 1 else v
    s = v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
    return int(round(s * 255))


def _lanczos(x: float, a: int = 3) -> float:
    if x == 0:
        return 1.0
    if abs(x) >= a:
        return 0.0
    px = math.pi * x
    return a * math.sin(px) * math.sin(px / a) / (px * px)


@dataclass
class Image:
    width: int
    height: int
    planes: list[list[float]]  # r, g, b premultiplied by a, then a; all linear light, row-major

    # ------------------------------------------------------------ conversion

    @classmethod
    def from_pixels(cls, px: Pixels, x: int = 0, y: int = 0, w: int | None = None, h: int | None = None) -> Image:
        """Read a region (default: all) into linear light. Parts outside the source are transparent."""
        w, h = w or px.width, h or px.height
        rows = px.rgba_rows()
        planes: list[list[float]] = [[0.0] * (w * h) for _ in range(4)]
        r, g, b, a = planes
        for j in range(h):
            sy = y + j
            if not 0 <= sy < px.height:
                continue
            row = rows[sy]
            for i in range(w):
                sx = x + i
                if not 0 <= sx < px.width:
                    continue
                k = sx * 4
                alpha = row[k + 3] / 255
                if alpha:
                    o = j * w + i
                    r[o], g[o], b[o], a[o] = (_TO_LINEAR[row[k]] * alpha, _TO_LINEAR[row[k + 1]] * alpha,
                                              _TO_LINEAR[row[k + 2]] * alpha, alpha)
        return cls(w, h, planes)

    def to_pixels(self) -> Pixels:
        r, g, b, a = self.planes
        rows = []
        for j in range(self.height):
            row = bytearray()
            for i in range(self.width):
                o = j * self.width + i
                alpha = min(max(a[o], 0.0), 1.0)
                if alpha <= 0:
                    row += b"\0\0\0\0"
                    continue
                row += bytes((_to_srgb(r[o] / alpha), _to_srgb(g[o] / alpha), _to_srgb(b[o] / alpha), int(round(alpha * 255))))
            rows.append(bytes(row))
        return Pixels(self.width, self.height, 4, rows)

    # ------------------------------------------------------------ resampling

    def _box(self, factor: int) -> Image:
        w, h = self.width // factor, self.height // factor
        area = factor * factor
        out = []
        for plane in self.planes:
            dst = [0.0] * (w * h)
            for j in range(h):
                for i in range(w):
                    total = 0.0
                    for dy in range(factor):
                        base = (j * factor + dy) * self.width + i * factor
                        total += sum(plane[base:base + factor])
                    dst[j * w + i] = total / area
            out.append(dst)
        return Image(w, h, out)

    @staticmethod
    def _weights(src: int, dst: int) -> tuple[int, list[tuple[int, list[float]]]]:
        """Lanczos-3 taps per output sample: (padding needed, [(first source index + padding, taps)])."""
        scale = src / dst
        stretch = max(scale, 1.0)
        support = 3 * stretch
        count = int(2 * support) + 1
        pad = count + 1
        table = []
        for i in range(dst):
            centre = (i + 0.5) * scale - 0.5
            start = int(math.floor(centre - support)) + 1
            taps = [_lanczos((start + k - centre) / stretch) for k in range(count)]
            total = sum(taps)
            table.append((start + pad, [t / total for t in taps]))
        return pad, table

    @staticmethod
    def _filter_lines(lines: list[list[float]], pad: int, table: list[tuple[int, list[float]]]) -> list[list[float]]:
        """Apply the taps along each line; lines are padded by repeating their end values."""
        out = []
        for line in lines:
            padded = [line[0]] * pad + line + [line[-1]] * pad
            out.append([sum(map(mul, padded[s:s + len(taps)], taps)) for s, taps in table])
        return out

    def _resample(self, w: int, h: int) -> Image:
        col_pad, cols = self._weights(self.width, w)
        row_pad, rows = self._weights(self.height, h)
        out = []
        for plane in self.planes:
            horizontal = self._filter_lines([plane[y * self.width:(y + 1) * self.width] for y in range(self.height)], col_pad, cols)
            columns = [list(col) for col in zip(*horizontal)]          # w columns of height samples
            vertical = self._filter_lines(columns, row_pad, rows)        # w columns of h samples
            out.append([vertical[x][y] for y in range(h) for x in range(w)])
        return Image(w, h, out)

    def resize(self, size: int) -> Image:
        """Square downscale to `size`: area average by the integer part of the ratio, then Lanczos-3."""
        image = self
        factor = min(self.width, self.height) // size
        if factor > 1:
            image = image._box(factor)
        if (image.width, image.height) != (size, size):
            image = image._resample(size, size)
        return image

    # ------------------------------------------------------------ finishing

    def sharpen(self, radius: float, amount: float) -> Image:
        """Unsharp mask on the colour planes: out = in + amount * (in - gaussian blur)."""
        reach = max(1, int(math.ceil(radius * 3)))
        kernel = [math.exp(-(k * k) / (2 * radius * radius)) for k in range(-reach, reach + 1)]
        norm = sum(kernel)
        kernel = [k / norm for k in kernel]
        w, h = self.width, self.height

        def blur(plane: list[float]) -> list[float]:
            tmp = [sum(plane[y * w + min(max(x + k - reach, 0), w - 1)] * c for k, c in enumerate(kernel))
                   for y in range(h) for x in range(w)]
            return [sum(tmp[min(max(y + k - reach, 0), h - 1) * w + x] * c for k, c in enumerate(kernel))
                    for y in range(h) for x in range(w)]

        alpha = self.planes[3]
        out = []
        for plane in self.planes[:3]:
            soft = blur(plane)
            out.append([min(max(v + amount * (v - s), 0.0), a) for v, s, a in zip(plane, soft, alpha)])
        return Image(w, h, out + [alpha[:]])

    def round_mask(self, diameter_fraction: float = 1.0) -> Image:
        """Keep only an antialiased centred circle (supersampled coverage per pixel)."""
        w, h = self.width, self.height
        cx, cy, radius = w / 2, h / 2, min(w, h) * diameter_fraction / 2
        grid = 4
        cover = []
        for y in range(h):
            for x in range(w):
                inside = sum(1 for sy in range(grid) for sx in range(grid)
                             if (x + (sx + 0.5) / grid - cx) ** 2 + (y + (sy + 0.5) / grid - cy) ** 2 <= radius * radius)
                cover.append(inside / (grid * grid))
        return Image(w, h, [[v * c for v, c in zip(plane, cover)] for plane in self.planes])

    def on_background(self, colour: str, canvas: int, scale: float) -> Image:
        """This image, scaled into a `canvas` square at `scale` of its side, over an opaque colour."""
        inner = max(1, round(canvas * scale))
        small = self.resize(inner)
        r0, g0, b0, _ = hex_rgba(colour)
        bg = (_TO_LINEAR[r0], _TO_LINEAR[g0], _TO_LINEAR[b0])
        planes = [[bg[c]] * (canvas * canvas) for c in range(3)] + [[1.0] * (canvas * canvas)]
        off = (canvas - inner) // 2
        for j in range(inner):
            for i in range(inner):
                s = j * inner + i
                d = (j + off) * canvas + i + off
                a = small.planes[3][s]
                for c in range(3):
                    planes[c][d] = small.planes[c][s] + bg[c] * (1 - a)
        return Image(canvas, canvas, planes)
