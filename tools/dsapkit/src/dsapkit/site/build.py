"""make site: load the registry, check it, check the structured data rules are fresh and write the reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..errors import BuildError
from ..jsonio import read_json
from ..paths import Paths
from ..tokens import TokenSet
from .links import check_links
from .model import Site, load_site
from .report import write_reports
from .security import check_security, check_security_txt, security_age
from .validate import check_site


@dataclass(frozen=True)
class SiteBuild:
    site: Site
    rules_checked: str
    rules_age_days: int


def rules_age(rules: dict, today: date) -> int:
    """Days since the structured data rules were last read from Google's documentation.

    A rule is only as good as the day it was read: past staleAfterDays it must be read again
    (plan B5: quarterly), so an old copy of Google's guidance cannot pass quietly."""
    age = (today - date.fromisoformat(rules["checked"])).days
    if age > rules["staleAfterDays"]:
        raise BuildError(f"jsonld-rules.json was read from Google's docs on {rules['checked']}, {age} days ago "
                         f"(limit {rules['staleAfterDays']}). Run make docs-drift, re-read the pages it names, "
                         "then update the rules and 'checked'.")
    return age


def build_site(paths: Paths, tokens: TokenSet, today: date | None = None) -> SiteBuild:
    site = load_site(paths)
    problems = check_site(site, tokens) + check_links(site)
    if problems:
        raise BuildError("site registry problems:\n  " + "\n  ".join(problems))
    rules = read_json(paths.site / "jsonld-rules.json")
    age = rules_age(rules, today or date.today())
    security = read_json(paths.site / "security.json")
    security_age(security, today or date.today())
    weak = check_security(security) + check_security_txt(security, today or date.today())
    if weak:
        raise BuildError("packages/site/security.json:\n  " + "\n  ".join(weak))
    write_reports(paths, site, rules)
    return SiteBuild(site, rules["checked"], age)
