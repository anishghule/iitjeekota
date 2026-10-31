"""Run the voice rules over files and report findings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .readability import score
from .rules import LocaleRules, Term, VoiceRules
from .sources import TextLine, collect_files, read_lines

_SPACED_HYPHEN_RE = re.compile(r"(?<=\S) - (?=\S)")


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    severity: str  # "error" or "warning"
    message: str

    def format(self, root: Path) -> str:
        where = f"{self.path.relative_to(root) if self.path.is_relative_to(root) else self.path}"
        return f"{where}:{self.line}: {self.severity}: {self.message}"


def _term_hits(line: TextLine, terms: list[Term], severity: str, label: str) -> list[Finding]:
    return [Finding(line.path, line.line, severity, f"{label} {t.term!r} ({t.advice})")
            for t in terms if t.term.lower() not in line.allowed and t.regex.search(line.text)]


def lint_line(line: TextLine, rules: VoiceRules) -> list[Finding]:
    found = []
    for ch in rules.dash_characters:
        if ch in line.text:
            found.append(Finding(line.path, line.line, "error", f"dash U+{ord(ch):04X}: {rules.dash_message}"))
    if rules.spaced_hyphen and _SPACED_HYPHEN_RE.search(line.text):
        found.append(Finding(line.path, line.line, "error", f"spaced hyphen used as a dash: {rules.dash_message}"))
    local: LocaleRules = rules.for_locale(line.locale)
    found += _term_hits(line, local.banned, "error", "banned word")
    found += _term_hits(line, local.claims, "error", "claim")
    found += _term_hits(line, local.warnings, "warning", "check word")
    for p in local.patterns:
        if p.regex.search(line.text):
            found.append(Finding(line.path, line.line, p.severity, p.message))
    return found


def lint_text(text: str, rules: VoiceRules, locale: str = "en") -> list[Finding]:
    """Lint a single string (used by tests and the voice examples)."""
    line = TextLine(Path("<text>"), 1, text, locale, frozenset())
    return lint_line(line, rules)


def _readability(path: Path, lines: list[TextLine], rules: VoiceRules) -> list[Finding]:
    found = []
    for locale in {ln.locale for ln in lines}:
        target = rules.for_locale(locale).readability
        if not target or path.suffix not in {".md", ".mdx", ".html", ".txt"}:
            continue
        result = score("\n".join(ln.text for ln in lines if ln.locale == locale and ln.prose))
        if result.words < target.min_words:
            continue
        if result.reading_ease < target.min_reading_ease or result.grade > target.max_grade:
            found.append(Finding(path, 0, "warning", f"reading ease {result.reading_ease} (grade {result.grade}); "
                                 f"aim for ease {target.min_reading_ease}+ and grade {target.max_grade} or lower"))
        if result.longest_sentence > target.max_sentence_words:
            opening = " ".join(result.longest_text.split()[:8])
            found.append(Finding(path, 0, "warning", f"a sentence runs {result.longest_sentence} words, keep under "
                                 f"{target.max_sentence_words}: \"{opening}...\""))
    return found


def lint_paths(targets: list[Path], rules: VoiceRules, locales: set[str], default_locale: str,
               exclude: set[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in collect_files(targets, exclude):
        lines = read_lines(path, locales, default_locale)
        for line in lines:
            findings += lint_line(line, rules)
        findings += _readability(path, lines, rules)
    return findings
