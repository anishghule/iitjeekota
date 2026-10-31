"""Colour maths: parsing, compositing and WCAG 2 contrast."""

from __future__ import annotations

RGB = tuple[float, float, float]


def hex_rgba(value: str) -> tuple[int, int, int, float]:
    h = value.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    alpha = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return r, g, b, alpha


def composite(fg: str, bg: str) -> RGB:
    """`fg` painted over an opaque `bg`."""
    fr, fgc, fb, fa = hex_rgba(fg)
    br, bgc, bb, _ = hex_rgba(bg)
    return fr * fa + br * (1 - fa), fgc * fa + bgc * (1 - fa), fb * fa + bb * (1 - fa)


def relative_luminance(rgb: RGB) -> float:
    def linear(channel: float) -> float:
        c = channel / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    """WCAG 2 contrast ratio; a translucent foreground is composited onto the background first."""
    lum_fg = relative_luminance(composite(fg, bg))
    lum_bg = relative_luminance(composite(bg, "#ffffff"))
    high, low = max(lum_fg, lum_bg), min(lum_fg, lum_bg)
    return (high + 0.05) / (low + 0.05)


def css_rgb(value: str, alpha: float = 1.0) -> str:
    r, g, b, a = hex_rgba(value)
    total = round(alpha * a, 3)
    return f"rgb({r} {g} {b})" if total >= 1 else f"rgb({r} {g} {b} / {total:g})"
