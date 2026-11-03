import tempfile
import unittest
from pathlib import Path

from dsapkit.copylint.lint import lint_paths, lint_text
from dsapkit.copylint.readability import score
from dsapkit.copylint.rules import load_rules
from dsapkit.copylint.sources import read_lines
from dsapkit.paths import Paths

PATHS = Paths.discover()
RULES = load_rules(PATHS.voice_json)
LOCALES = {"en", "hi", "mr"}


def errors(text: str, locale: str = "en") -> list[str]:
    return [f.message for f in lint_text(text, RULES, locale) if f.severity == "error"]


class RulesTest(unittest.TestCase):
    def test_dashes_fail(self):
        self.assertTrue(errors("Kota—Pune"))
        self.assertTrue(errors("Class 9–10"))
        self.assertTrue(errors("Kota - Pune"))
        self.assertFalse(errors("D-SAP in Pimpri-Chinchwad"))

    def test_banned_words_fail_as_whole_words_only(self):
        self.assertTrue(errors("A holistic plan."))
        self.assertFalse(errors("A whole plan."))

    def test_claims_need_an_allow(self):
        self.assertTrue(errors("The best coaching in Pune."))
        self.assertTrue(errors("पुणे में सर्वश्रेष्ठ कोचिंग", "hi"))

    def test_every_example_before_fails_and_after_passes(self):
        for example in RULES.examples:
            self.assertTrue(errors(example["before"]), example["before"])
            self.assertFalse(errors(example["after"]), example["after"])


class SourcesTest(unittest.TestCase):
    def lint_file(self, name: str, text: str):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / name
            path.write_text(text, encoding="utf-8")
            return lint_paths([path], RULES, LOCALES, "en", set()), read_lines(path, LOCALES, "en")

    def test_disable_region_and_allow_directive(self):
        findings, _ = self.lint_file("page.md", "Fine line.\n<!-- copy-lint-disable -->\nA holistic plan.\n"
                                     "<!-- copy-lint-enable -->\nHow to choose the best classes? <!-- copy-lint-allow: best -->\n")
        self.assertEqual([f for f in findings if f.severity == "error"], [])

    def test_html_blocks_keep_language_and_skip_code(self):
        html = '<p>Plain words.</p>\n<p lang="hi">पुणे में <b>सर्वश्रेष्ठ</b> कोचिंग</p>\n<pre>a — b</pre>'
        findings, lines = self.lint_file("page.html", html)
        self.assertEqual([ln.locale for ln in lines], ["en", "hi"])
        self.assertTrue(lines[0].prose)
        self.assertEqual(len([f for f in findings if f.severity == "error"]), 1)

    def test_json_locale_comes_from_keys(self):
        _, lines = self.lint_file("copy.json", '{"locales": {"mr": {"title": "पुण्यात IIT JEE कोचिंग"}}}')
        self.assertEqual(lines[0].locale, "mr")


class ReadabilityTest(unittest.TestCase):
    def test_short_plain_sentences_score_well(self):
        result = score("Your child writes a test every Sunday. You get the report on Monday.")
        self.assertGreater(result.reading_ease, 70)
        self.assertEqual(result.sentences, 2)

    def test_line_breaks_end_sentences(self):
        self.assertEqual(score("First block\nSecond block").sentences, 2)


if __name__ == "__main__":
    unittest.main()
