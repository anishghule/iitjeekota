"""Small SVG toolkit: escaping, number formatting, attributes and affine placement of path templates."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from xml.sax.saxutils import escape as _escape

from ..errors import BuildError

SVG_NS = "http://www.w3.org/2000/svg"
_PATH_TOKEN = re.compile(r"[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?")
_TEMPLATE_COMMANDS = {"M": 2, "L": 2, "C": 6, "Q": 4, "Z": 0}


def escape(text: str) -> str:
    return _escape(text, {'"': "&quot;"})


def num(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def attrs(values: dict[str, object]) -> str:
    return " ".join(f'{k}="{escape(str(v))}"' for k, v in values.items() if v is not None)


@dataclass(frozen=True)
class Affine:
    """x' = a*x + c*y + e, y' = b*x + d*y + f (the SVG matrix order)."""

    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0

    @classmethod
    def translate(cls, x: float, y: float) -> Affine:
        return cls(e=x, f=y)

    @classmethod
    def scale(cls, sx: float, sy: float | None = None) -> Affine:
        return cls(a=sx, d=sx if sy is None else sy)

    @classmethod
    def rotate(cls, degrees: float) -> Affine:
        r = math.radians(degrees)
        return cls(a=math.cos(r), b=math.sin(r), c=-math.sin(r), d=math.cos(r))

    def __matmul__(self, other: Affine) -> Affine:
        """self @ other applies `other` first, then `self`."""
        return Affine(
            a=self.a * other.a + self.c * other.b, b=self.b * other.a + self.d * other.b,
            c=self.a * other.c + self.c * other.d, d=self.b * other.c + self.d * other.d,
            e=self.a * other.e + self.c * other.f + self.e, f=self.b * other.e + self.d * other.f + self.f,
        )

    def apply(self, x: float, y: float) -> tuple[float, float]:
        return self.a * x + self.c * y + self.e, self.b * x + self.d * y + self.f


def place(template: str, m: Affine) -> str:
    """Transform a template path (absolute M, L, C, Q, Z only) by `m` and return new path data."""
    tokens = _PATH_TOKEN.findall(template)
    out: list[str] = []
    command = ""
    i = 0
    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            if command not in _TEMPLATE_COMMANDS:
                raise BuildError(f"template paths may only use absolute M, L, C, Q, Z (found {command!r})")
            out.append(command)
            i += 1
            if command == "Z":
                continue
        count = _TEMPLATE_COMMANDS[command]
        values = [float(t) for t in tokens[i:i + count]]
        if len(values) < count:
            raise BuildError(f"template path ends early: {template}")
        i += count
        for k in range(0, count, 2):
            x, y = m.apply(values[k], values[k + 1])
            out.append(f"{num(x)} {num(y)}")
    return " ".join(out)


def circle_path(cx: float, cy: float, r: float) -> str:
    return (f"M{num(cx - r)} {num(cy)}A{num(r)} {num(r)} 0 1 0 {num(cx + r)} {num(cy)}"
            f"A{num(r)} {num(r)} 0 1 0 {num(cx - r)} {num(cy)}Z")
