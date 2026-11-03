"""English readability: Flesch reading ease, Flesch-Kincaid grade and sentence length."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]?")  # a line break ends a sentence: each block of copy stands alone
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")


def syllables(word: str) -> int:
    w = word.lower().strip("'")
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(_VOWEL_GROUP_RE.findall(w)))


@dataclass(frozen=True)
class Score:
    words: int
    sentences: int
    reading_ease: float
    grade: float
    longest_sentence: int
    longest_text: str


def score(text: str) -> Score:
    sentences = [s.strip() for s in _SENTENCE_RE.findall(text) if _WORD_RE.search(s)]
    words = _WORD_RE.findall(text)
    if not words or not sentences:
        return Score(0, 0, 100.0, 0.0, 0, "")
    syl = sum(syllables(w) for w in words)
    wps, spw = len(words) / len(sentences), syl / len(words)
    longest = max(sentences, key=lambda s: len(_WORD_RE.findall(s)))
    return Score(len(words), len(sentences), round(206.835 - 1.015 * wps - 84.6 * spw, 1),
                 round(0.39 * wps + 11.8 * spw - 15.59, 1), len(_WORD_RE.findall(longest)), longest)
