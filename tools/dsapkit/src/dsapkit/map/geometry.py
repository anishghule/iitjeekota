"""Plane geometry for the area map: a local projection, line simplification and joining ways."""

from __future__ import annotations

import math
from dataclasses import dataclass

EARTH_RADIUS_M = 6_371_008.8
Point = tuple[float, float]


@dataclass(frozen=True)
class Projection:
    """Equirectangular around an origin: accurate to a fraction of a percent across a city."""
    lat0: float
    lon0: float

    def metres(self, lon: float, lat: float) -> Point:
        x = math.radians(lon - self.lon0) * math.cos(math.radians(self.lat0)) * EARTH_RADIUS_M
        y = math.radians(lat - self.lat0) * EARTH_RADIUS_M
        return x, y


def _distance_to_segment(p: Point, a: Point, b: Point) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def simplify(points: list[Point], tolerance: float) -> list[Point]:
    """Douglas-Peucker: keeps the points that move the line by more than `tolerance`."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        worst, index = 0.0, -1
        for i in range(first + 1, last):
            d = _distance_to_segment(points[i], points[first], points[last])
            if d > worst:
                worst, index = d, i
        if worst > tolerance:
            keep[index] = True
            stack += [(first, index), (index, last)]
    return [p for p, k in zip(points, keep) if k]


def chain(lines: list[list[Point]]) -> list[list[Point]]:
    """Joins lines that share an end point into longer lines (OpenStreetMap splits a river into many ways)."""
    pending = [list(line) for line in lines if len(line) >= 2]
    joined: list[list[Point]] = []
    while pending:
        line = pending.pop()
        grew = True
        while grew:
            grew = False
            for i, other in enumerate(pending):
                if other[0] == line[-1]:
                    line += other[1:]
                elif other[-1] == line[-1]:
                    line += other[-2::-1]
                elif other[-1] == line[0]:
                    line = other[:-1] + line
                elif other[0] == line[0]:
                    line = other[:0:-1] + line
                else:
                    continue
                pending.pop(i)
                grew = True
                break
        joined.append(line)
    return joined


def path_d(points: list[Point], decimals: int) -> str:
    """An SVG path for a line."""
    fmt = f"{{:.{decimals}f}}"
    head, *rest = points
    return "M" + " ".join(f"{fmt.format(x)} {fmt.format(y)}" for x, y in [head]) + "".join(
        f"L{fmt.format(x)} {fmt.format(y)}" for x, y in rest)
