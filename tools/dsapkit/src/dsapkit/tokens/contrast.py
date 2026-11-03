"""Check every colour pair in contrast.json on every surface."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ..errors import BuildError
from .colour import contrast_ratio


@dataclass(frozen=True)
class ContrastResult:
    surface: str
    fg: str
    bg: str
    fg_value: str
    bg_value: str
    ratio: float
    level: str
    minimum: float
    use: str

    @property
    def passed(self) -> bool:
        return self.ratio >= self.minimum

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "passed": self.passed}


def check(surfaces: dict[str, dict[str, str]], config: dict[str, Any]) -> list[ContrastResult]:
    levels: dict[str, float] = config["levels"]
    results = []
    for surface, roles in surfaces.items():
        for pair in config["pairs"]:
            for key in ("fg", "bg"):
                if pair[key] not in roles:
                    raise BuildError(f"contrast.json: surface {surface} has no role {pair[key]}")
            if pair["min"] not in levels:
                raise BuildError(f"contrast.json: unknown level {pair['min']}")
            results.append(ContrastResult(
                surface=surface, fg=pair["fg"], bg=pair["bg"],
                fg_value=roles[pair["fg"]], bg_value=roles[pair["bg"]],
                ratio=round(contrast_ratio(roles[pair["fg"]], roles[pair["bg"]]), 2),
                level=pair["min"], minimum=levels[pair["min"]], use=pair["use"],
            ))
    return results


def to_markdown(results: list[ContrastResult]) -> str:
    lines = ["| Surface | Foreground | Background | Ratio | Needs | Result | Use |",
             "|---|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r.surface} | `{r.fg}` {r.fg_value} | `{r.bg}` {r.bg_value} | {r.ratio:.2f}:1 | "
                     f"{r.level} {r.minimum:g}:1 | {'Pass' if r.passed else 'FAIL'} | {r.use} |")
    return "\n".join(lines) + "\n"
