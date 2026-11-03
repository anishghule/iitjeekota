"""The JEE syllabus as chapters (packages/content/syllabus.json), checked against the official unit lists.

Every chapter names its JEE Main unit (an index into units.main, 1-based) and its JEE Advanced
headings (units.advanced); either may be empty but not both. Every official unit and heading must
be covered by at least one chapter, so a change to the official syllabus shows up as a failed check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..jsonio import GENERATED, read_json, write_text
from ..paths import Paths

CLASSES = {11, 12}


@dataclass(frozen=True)
class Chapter:
    id: str
    subject: str
    classes: tuple[int, ...]
    names: dict[str, str]
    main: int | None
    advanced: tuple[str, ...]
    topics: tuple[str, ...]
    advanced_also: tuple[str, ...]

    @property
    def advanced_only(self) -> bool:
        return self.main is None


@dataclass(frozen=True)
class Syllabus:
    sources: dict[str, Any]
    subjects: dict[str, dict[str, str]]  # id -> names
    subject_codes: dict[str, str]  # id -> the letter in chapter codes (P, C, M)
    units: dict[str, dict[str, list[str]]]  # exam -> subject -> official unit or heading names
    chapters: tuple[Chapter, ...]
    translations: dict[str, dict[str, Any]] = field(default_factory=dict)  # locale -> syllabus/{locale}.json

    def of(self, subject: str) -> list[Chapter]:
        return [c for c in self.chapters if c.subject == subject]

    def code(self, chapter: Chapter) -> str:
        """The chapter's code, like 11-P-03: the class it is first taught in, the subject's letter and its
        place among that subject's chapters of that class, in the order of syllabus.json. A chapter taught
        across both classes is listed with Class 11."""
        first = chapter.classes[0]
        peers = [c for c in self.of(chapter.subject) if c.classes[0] == first]
        return f"{first}-{self.subject_codes[chapter.subject]}-{peers.index(chapter) + 1:02d}"

    def value(self, key: str, field_name: str) -> tuple[Any, str | None]:
        """Values copy may quote, read like Site.fact_value:
        main#year and advanced#year (the official documents), and {all|advanced-only|subject}#chapters."""
        if key in self.sources and field_name == "year":
            return self.sources[key]["year"], None
        if field_name == "chapters":
            if key == "all":
                return len(self.chapters), None
            if key == "advanced-only":
                return sum(c.advanced_only for c in self.chapters), None
            if key in self.subjects:
                return len(self.of(key)), None
        return None, f"unknown syllabus {key}#{field_name}"


def load_syllabus(paths: Paths) -> Syllabus:
    """syllabus.json holds the structure and the English names; syllabus/{locale}.json holds one language's
    names, so a translator works in one file. Names are merged into each chapter and subject."""
    raw = read_json(paths.content_syllabus)
    folder = paths.content_syllabus.with_suffix("")
    translations = {f.stem: read_json(f) for f in sorted(folder.glob("*.json"))} if folder.is_dir() else {}

    def names(english: dict[str, str], kind: str, key: str) -> dict[str, str]:
        local = {loc: t[kind][key] for loc, t in translations.items() if key in t.get(kind, {})}
        return {**english, **local}

    chapters = tuple(Chapter(c["id"], c["subject"], tuple(c["classes"]), names(c["names"], "chapters", c["id"]),
                             c["main"], tuple(c["advanced"]), tuple(c["topics"]), tuple(c.get("advancedAlso", [])))
                     for c in raw["chapters"])
    subjects = {s["id"]: names(s["names"], "subjects", s["id"]) for s in raw["subjects"]}
    codes = {s["id"]: s["code"] for s in raw["subjects"]}
    return Syllabus(raw["sources"], subjects, codes, raw["units"], chapters, translations)


def check_syllabus(syllabus: Syllabus) -> list[str]:
    problems = []
    seen_ids = set()
    letters = list(syllabus.subject_codes.values())
    if len(set(letters)) != len(letters) or not all(len(letter) == 1 and letter.isupper() for letter in letters):
        problems.append("syllabus subjects: each needs its own single capital letter as code")
    for c in syllabus.chapters:
        where = f"syllabus chapter {c.id}"
        if c.id in seen_ids:
            problems.append(f"{where}: duplicate id")
        seen_ids.add(c.id)
        if c.subject not in syllabus.subjects:
            problems.append(f"{where}: unknown subject {c.subject!r}")
            continue
        if not c.classes or not set(c.classes) <= CLASSES:
            problems.append(f"{where}: classes must be 11, 12 or both")
        if "en" not in c.names:
            problems.append(f"{where}: needs an English name")
        if c.main is None and not c.advanced:
            problems.append(f"{where}: is in neither JEE Main nor JEE Advanced")
        main_units = syllabus.units["main"].get(c.subject, [])
        if c.main is not None and not 1 <= c.main <= len(main_units):
            problems.append(f"{where}: JEE Main unit {c.main} is not one of the {len(main_units)} {c.subject} units")
        for heading in c.advanced:
            if heading not in syllabus.units["advanced"].get(c.subject, []):
                problems.append(f"{where}: {heading!r} is not a JEE Advanced {c.subject} heading")
        if not c.topics:
            problems.append(f"{where}: needs topics")
    ids = {c.id for c in syllabus.chapters}
    for loc, t in syllabus.translations.items():
        where = f"syllabus/{loc}.json"
        for kind, expected in (("chapters", ids), ("subjects", set(syllabus.subjects))):
            given = set(t.get(kind, {}))
            problems += [f"{where}: no {kind[:-1]} name for {k}" for k in sorted(expected - given)]
            problems += [f"{where}: {k} is not a syllabus {kind[:-1]}" for k in sorted(given - expected)]
    for subject in syllabus.subjects:
        chapters = syllabus.of(subject)
        covered_main = {c.main for c in chapters}
        for n, name in enumerate(syllabus.units["main"].get(subject, []), 1):
            if n not in covered_main:
                problems.append(f"JEE Main {subject} unit {n} ({name}) has no chapter")
        covered_advanced = {h for c in chapters for h in c.advanced}
        for heading in syllabus.units["advanced"].get(subject, []):
            if heading not in covered_advanced:
                problems.append(f"JEE Advanced {subject} heading {heading!r} has no chapter")
    return problems


def _exams(c: Chapter) -> str:
    return "Advanced only" if c.advanced_only else "Main only" if not c.advanced else "Main and Advanced"


def write_syllabus_doc(paths: Paths, syllabus: Syllabus) -> Path:
    """docs/content/syllabus.md: the chapters by subject, what is Advanced only, and the sources."""
    main, adv = syllabus.sources["main"], syllabus.sources["advanced"]
    lines = ["<!-- " + GENERATED.format(source="packages/content/syllabus.json via make content") + " -->", "",
             "# JEE syllabus by chapter", "",
             f"From the {main['title']} ({main['publisher']}, published {main['published']}) and the "
             f"{adv['title']}. Topics are shortened from the official wording.", "",
             "| Subject | Chapters | Main and Advanced | Main only | Advanced only |", "| --- | --- | --- | --- | --- |"]
    for subject, names in syllabus.subjects.items():
        chapters = syllabus.of(subject)
        count = {k: sum(_exams(c) == k for c in chapters) for k in ("Main and Advanced", "Main only", "Advanced only")}
        lines.append(f"| {names['en']} | {len(chapters)} | {count['Main and Advanced']} | {count['Main only']} | {count['Advanced only']} |")
    for subject, names in syllabus.subjects.items():
        lines += ["", f"## {names['en']}", "", "| Code | Chapter | Class | JEE Main unit | JEE Advanced | Advanced adds |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for c in syllabus.of(subject):
            unit = f"{c.main}. {syllabus.units['main'][subject][c.main - 1]}" if c.main else ""
            lines.append(f"| {syllabus.code(c)} | {c.names['en']} | {', '.join(map(str, c.classes))} | {unit} | "
                         f"{', '.join(c.advanced) or 'not in the syllabus'} | {'; '.join(c.advanced_also)} |")
    lines += ["", "Sources:", "", f"- [{main['title']}]({main['url']}), read {main['read']}",
              f"- [{adv['title']}]({adv['url']}), read {adv['read']}. {adv.get('note', '')}".rstrip()]
    target = paths.content_docs / "syllabus.md"
    write_text(target, "\n".join(lines) + "\n")
    return target
