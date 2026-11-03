"""Points of SVG shapes, used to keep icon geometry on the 24px grid."""

from __future__ import annotations

import re
# Builds elements only; parsing is in icons/build.py, which refuses entity declarations.
import xml.etree.ElementTree as ET  # nosec B405

from ..errors import BuildError

Point = tuple[float, float]

_NUMBER = r"-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?"
_TOKEN_RE = re.compile(rf"[MmLlHhVvCcSsQqTtAaZz]|{_NUMBER}")
_NUMBER_RE = re.compile(_NUMBER)
_ARG_COUNT = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def path_points(d: str) -> list[Point]:
    """Absolute end and control points of path data. Arc bulges are not traced."""
    tokens = _TOKEN_RE.findall(d)
    points: list[Point] = []
    x = y = start_x = start_y = 0.0
    command = ""
    i = 0
    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1
            if command in "Zz":
                x, y = start_x, start_y
                continue
        if not command:
            raise BuildError(f"path data starts without a command: {d[:30]}")
        upper, relative = command.upper(), command.islower()
        count = _ARG_COUNT[upper]
        args = [float(t) for t in tokens[i:i + count]]
        if len(args) < count:
            raise BuildError(f"path data ends early near: {' '.join(tokens[i:i + count])}")
        i += count
        if upper == "H":
            x = x + args[0] if relative else args[0]
            points.append((x, y))
        elif upper == "V":
            y = y + args[0] if relative else args[0]
            points.append((x, y))
        elif upper == "A":
            x, y = (x + args[5], y + args[6]) if relative else (args[5], args[6])
            points.append((x, y))
        else:
            for k in range(0, count, 2):
                px, py = args[k], args[k + 1]
                points.append((x + px, y + py) if relative else (px, py))
            x, y = points[-1]
            if upper == "M":
                start_x, start_y = x, y
                command = "l" if relative else "L"  # further pairs after a move are line-tos
    return points


def element_points(el: ET.Element) -> list[Point]:
    tag = el.tag.split("}")[-1]

    def attr(name: str) -> float:
        return float(el.get(name, 0))

    if tag == "path":
        return path_points(el.get("d", ""))
    if tag == "circle":
        r = attr("r")
        return [(attr("cx") - r, attr("cy") - r), (attr("cx") + r, attr("cy") + r)]
    if tag == "ellipse":
        reach = max(attr("rx"), attr("ry"))  # holds for any rotation
        return [(attr("cx") - reach, attr("cy") - reach), (attr("cx") + reach, attr("cy") + reach)]
    if tag == "rect":
        return [(attr("x"), attr("y")), (attr("x") + attr("width"), attr("y") + attr("height"))]
    if tag == "line":
        return [(attr("x1"), attr("y1")), (attr("x2"), attr("y2"))]
    numbers = [float(n) for n in _NUMBER_RE.findall(el.get("points", ""))]
    return list(zip(numbers[0::2], numbers[1::2]))
