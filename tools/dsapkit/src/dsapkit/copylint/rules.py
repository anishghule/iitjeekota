"""voice.json compiled into matchers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..jsonio import read_json

# Letters and combining marks of Latin and Devanagari text. Python's \b treats
# Devanagari vowel signs as non-word characters, so terms get explicit edges.
WORD_CHARS = r"\wऀ-ॿ"


def term_pattern(term: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![{WORD_CHARS}]){re.escape(term)}(?![{WORD_CHARS}])", re.IGNORECASE)


@dataclass(frozen=True)
class Term:
    term: str
    advice: str
    regex: re.Pattern[str]


@dataclass(frozen=True)
class Pattern:
    regex: re.Pattern[str]
    message: str
    severity: str


@dataclass(frozen=True)
class Readability:
    min_words: int
    min_reading_ease: float
    max_grade: float
    max_sentence_words: int


@dataclass
class LocaleRules:
    banned: list[Term] = field(default_factory=list)
    claims: list[Term] = field(default_factory=list)
    warnings: list[Term] = field(default_factory=list)
    patterns: list[Pattern] = field(default_factory=list)
    readability: Readability | None = None


@dataclass(frozen=True)
class VoiceRules:
    dash_characters: tuple[str, ...]
    dash_message: str
    spaced_hyphen: bool
    locales: dict[str, LocaleRules]
    examples: tuple[dict[str, str], ...]
    principles: tuple[str, ...]

    def for_locale(self, locale: str) -> LocaleRules:
        return self.locales.get(locale, LocaleRules())


def load_rules(path: Path) -> VoiceRules:
    raw = read_json(path)
    locales: dict[str, LocaleRules] = {}

    def rules(locale: str) -> LocaleRules:
        return locales.setdefault(locale, LocaleRules())

    for locale, items in raw["banned"].items():
        rules(locale).banned = [Term(i["term"], f"use: {i['use']}", term_pattern(i["term"])) for i in items]
    for locale, items in raw["claims"].items():
        if not locale.startswith("$"):
            rules(locale).claims = [Term(t, "a claim: needs proof, legal review and copy-lint-allow", term_pattern(t)) for t in items]
    for locale, items in raw["warnings"].items():
        if not locale.startswith("$"):
            rules(locale).warnings = [Term(t, "often padding: check you need it", term_pattern(t)) for t in items]
    for locale, items in raw["patterns"].items():
        rules(locale).patterns = [Pattern(re.compile(p["pattern"], re.IGNORECASE | re.MULTILINE), p["message"],
                                          p.get("severity", "error")) for p in items]
    for locale, r in raw.get("readability", {}).items():
        rules(locale).readability = Readability(r["minWords"], r["minReadingEase"], r["maxGrade"], r["maxSentenceWords"])
    dashes = raw["dashes"]
    return VoiceRules(tuple(dashes["characters"]), dashes["message"], bool(dashes["spacedHyphen"]), locales,
                      tuple(raw["examples"]), tuple(raw["principles"]))
