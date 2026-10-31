"""Turn SVG into PNG with librsvg, the same way on every machine.

Pango (librsvg's text engine) uses CoreText on macOS and fontconfig on Linux.
Renders here always use fontconfig (PANGOCAIRO_BACKEND=fc) with a private
configuration: the render fonts when text is expected, or no fonts at all for
shape-only images, so a stray <text> shows as missing glyphs instead of quietly
picking up a system font.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..errors import BuildError
from ..fonts.render import RenderFonts

INSTALL_HINT = "install librsvg: brew install librsvg (macOS) or apt-get install librsvg2-bin fontconfig (Linux)"


class Rasteriser:
    def __init__(self, fonts: RenderFonts | None = None) -> None:
        self._fonts = fonts
        exe = shutil.which("rsvg-convert")
        if not exe:
            raise BuildError(f"rsvg-convert not found: {INSTALL_HINT}")
        self._exe = exe

    def png(self, svg: str, out: Path, width: int, height: int | None = None) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as folder_name:
            folder = Path(folder_name)
            source = folder / "image.svg"
            source.write_text(svg, encoding="utf-8")
            conf = self._fonts.fontconfig(folder) if self._fonts else RenderFonts.empty_fontconfig(folder)
            env = {**os.environ, "FONTCONFIG_FILE": str(conf), "PANGOCAIRO_BACKEND": "fc"}
            size = ["-w", str(width)] + (["-h", str(height)] if height else [])
            result = subprocess.run([self._exe, *size, "-o", str(out), str(source)], env=env,
                                    capture_output=True, text=True)
            if result.returncode != 0:
                raise BuildError(f"rsvg-convert failed for {out.name}: {result.stderr.strip()}")
