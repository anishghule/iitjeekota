"""make site: load the registry, check it, check the structured data fixtures and write the reports."""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import BuildError
from ..jsonio import read_json
from ..paths import Paths
from ..tokens import TokenSet
from .jsonld import Finding, check_fixtures, load_fixtures
from .links import check_links
from .model import Site, load_site
from .report import write_reports
from .validate import check_site


@dataclass(frozen=True)
class SiteBuild:
    site: Site
    findings: list[Finding]


def build_site(paths: Paths, tokens: TokenSet) -> SiteBuild:
    site = load_site(paths)
    problems = check_site(site, tokens) + check_links(site)
    if problems:
        raise BuildError("site registry problems:\n  " + "\n  ".join(problems))
    rules = read_json(paths.site / "jsonld-rules.json")
    fixtures = load_fixtures(paths.site / "jsonld", site)
    findings = check_fixtures(site, rules, fixtures)
    write_reports(paths, site, rules, fixtures, findings)
    errors = [f for f in findings if f.severity == "error"]
    if errors:
        raise BuildError("structured data errors:\n  " + "\n  ".join(f"{f.fixture}: {f.message}" for f in errors))
    return SiteBuild(site, findings)
