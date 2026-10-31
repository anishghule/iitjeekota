import tempfile
import unittest
from pathlib import Path

from dsapkit.web.lint import check_output, lint_source


def lint(text: str, name: str = "C.astro") -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "src"
        src.mkdir()
        (src / name).write_text(text, encoding="utf-8")
        return [p.message for p in lint_source(src, src / "generated")]


class SourceTest(unittest.TestCase):
    def test_token_based_styles_pass(self):
        ok = """<style>
          .a { color: var(--text); font-family: var(--font-display); font-size: var(--type-h2-size);
               transition: opacity var(--dur-base) var(--ease-enter), color var(--dur-fast) var(--ease-scrub); }
        </style>
        <a href="#enquiry">x</a> <use href={`#i-${name}`}></use>"""
        self.assertEqual(lint(ok), [])

    def test_raw_values_fail(self):
        for bad, rule in [
            (".a { color: #e6c296; }", "raw colour"),
            (".a { background: rgb(0 0 0 / 0.5); }", "colour function"),
            (".a { font-family: Inter, sans-serif; }", "font family"),
            (".a { font-size: 14px; }", "font size"),
            (".a { transition: opacity 300ms var(--ease-enter); }", "duration"),
            (".a { transition: opacity var(--dur-base) ease-in-out; }", "easing"),
            (".a { color: var(--color-brass-300); }", "palette primitive"),
        ]:
            with self.subTest(bad=bad):
                self.assertTrue(any(rule in m for m in lint(f"<style>{bad}</style>")), lint(f"<style>{bad}</style>"))

    def test_urls_and_image_paths_fail_but_comments_may_mention_them(self):
        self.assertTrue(lint('<a href="https://example.com">x</a>'))
        self.assertTrue(lint('<img src="/brand/medal-64.png" />'))
        self.assertEqual(lint("/* see https://example.com and medal.png */\nconst a = 1;", "x.ts"), [])

    def test_generated_files_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            (src / "generated").mkdir(parents=True)
            (src / "generated" / "x.ts").write_text('const u = "https://example.com";', encoding="utf-8")
            self.assertEqual(lint_source(src, src / "generated"), [])


class OutputTest(unittest.TestCase):
    def check(self, html: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "index.html").write_text(html, encoding="utf-8")
            return [p.message for p in check_output(Path(tmp))]

    def test_external_scripts_and_data_blocks_pass(self):
        html = ('<script type="module" src="/_astro/a.js"></script>'
                '<script type="application/ld+json">{"@context":"https://schema.org"}</script>'
                '<script type="application/json" data-x>{}</script>')
        self.assertEqual(self.check(html), [])

    def test_inline_scripts_and_styles_fail(self):
        self.assertEqual(self.check("<script>alert(1)</script>"), ["an inline script"])
        self.assertEqual(self.check('<div style="color:red"></div>'), ["an inline style"])
        self.assertEqual(self.check("<style>a{}</style>"), ["an inline style"])


if __name__ == "__main__":
    unittest.main()
