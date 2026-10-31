"""Measure each font role and compute fallback overrides and size matching (fonts.metrics.json)."""

from __future__ import annotations

from ..errors import BuildError
from ..jsonio import GENERATED, write_json
from ..paths import Paths
from ..tokens import TokenSet
from .config import FontsConfig, role_instance
from .google import GoogleFonts
from .sfnt import Face, fallback_overrides, x_height_match


def measure_fonts(paths: Paths, cfg: FontsConfig, tokens: TokenSet, client: GoogleFonts) -> dict:
    faces: dict[str, Face] = {}
    out: dict = {"$generated": GENERATED.format(source="fonts.config.json and tokens.json"),
                 "faces": {}, "fallbacks": {}, "sizeAdjust": {}}
    for fam in cfg.families:
        weight, stretch = role_instance(tokens, cfg, fam.role)
        face = Face(client.instance(fam.family, weight, stretch))
        faces[fam.role] = face
        out["faces"][fam.role] = {"family": fam.family, "weight": weight, "stretch": stretch,
                                  **face.describe(cfg.bounds_for.get(fam.role, ""))}
    for role, system_name in cfg.fallbacks.items():
        system = cfg.system_faces[system_name]
        if not system.path.exists():
            raise BuildError(f"{system_name} not found at {system.path}; run make metrics on macOS or update systemFonts")
        fallback = Face.from_path(system.path)
        out["faces"][system_name] = {"path": str(system.path), **fallback.describe()}
        out["fallbacks"][role] = {"family": f"{cfg.family(role).family} Fallback", "local": list(system.local),
                                  **fallback_overrides(faces[role], fallback)}
    for role, reference in cfg.match_x_height.items():
        out["sizeAdjust"][role] = {"matches": reference, "value": x_height_match(faces[reference], faces[role])}
    write_json(paths.fonts_metrics, out)
    return out
