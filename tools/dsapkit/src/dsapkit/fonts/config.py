"""fonts.config.json as typed data, checked against the token font roles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..errors import BuildError
from ..jsonio import read_json
from ..tokens import TokenSet

# The font role used for Hindi and Marathi (a key of font.family in tokens.json).
DEVANAGARI_ROLE = "devanagari"


@dataclass(frozen=True)
class FamilyConfig:
    role: str
    family: str
    axes: str
    subsets: tuple[str, ...]
    licence_url: str

    @property
    def slug(self) -> str:
        return self.family.lower().replace(" ", "-")

    @property
    def query(self) -> str:
        return f"{self.family}:{self.axes}"


@dataclass(frozen=True)
class SystemFace:
    name: str
    path: Path
    local: tuple[str, ...]


@dataclass(frozen=True)
class FontsConfig:
    css_api: str
    families: tuple[FamilyConfig, ...]
    metrics_variant: dict[str, str]
    fallbacks: dict[str, str]
    match_x_height: dict[str, str]
    bounds_for: dict[str, str]
    system_faces: dict[str, SystemFace]

    def family(self, role: str) -> FamilyConfig:
        for fam in self.families:
            if fam.role == role:
                return fam
        raise BuildError(f"fonts.config.json has no family for role {role!r}")


def load_fonts_config(path: Path, tokens: TokenSet) -> FontsConfig:
    raw = read_json(path)
    families = tuple(FamilyConfig(f["role"], f["family"], f["axes"], tuple(f["subsets"]), f["licenceUrl"])
                     for f in raw["families"])
    systems = {name: SystemFace(name, Path(s["path"]), tuple(s["local"])) for name, s in raw["systemFonts"].items()}
    m = raw["metrics"]
    cfg = FontsConfig(raw["cssApi"], families, m["variant"], m["fallbacks"], m["matchXHeight"], m.get("boundsFor", {}), systems)

    token_roles = set(tokens.tree["font"]["family"])
    config_roles = {f.role for f in families}
    if token_roles != config_roles:
        raise BuildError(f"fonts.config.json roles {sorted(config_roles)} must match font.family in tokens.json {sorted(token_roles)}")
    for role, stack in tokens.tree["font"]["family"].items():
        if stack[0] != cfg.family(role).family:
            raise BuildError(f"font.family.{role} starts with {stack[0]!r} but fonts.config.json vendors {cfg.family(role).family!r}")
    for role, variant in cfg.metrics_variant.items():
        if variant not in tokens.tree["type"]["scale"]:
            raise BuildError(f"fonts.config.json metrics.variant.{role}: unknown type variant {variant!r}")
    for role, system in cfg.fallbacks.items():
        if system not in systems:
            raise BuildError(f"fonts.config.json metrics.fallbacks.{role}: {system!r} is not in systemFonts")
    return cfg


def role_instance(tokens: TokenSet, cfg: FontsConfig, role: str) -> tuple[int, float]:
    """(weight, stretch %) of the type variant a role is measured at.

    The Devanagari role takes its weights from type.devanagari and has no width axis;
    the Latin roles take weight and width from the variant itself.
    """
    tree = tokens.tree
    variant = cfg.metrics_variant[role]
    if role == DEVANAGARI_ROLE:
        return int(tree["type"]["devanagari"]["weight"][variant]), 100.0
    spec = tree["type"]["scale"][variant]
    return int(spec["weight"]), float(spec["stretch"])


def role_stretch(tokens: TokenSet, role: str) -> float:
    return float(tokens.tree["font"]["stretch"].get(role, 100))
