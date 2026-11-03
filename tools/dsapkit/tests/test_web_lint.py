import tempfile
import unittest
from pathlib import Path

from dsapkit.web.lint import check_not_found, check_output, lint_source


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

    def test_what_the_content_security_policy_would_block_is_found_first(self):
        self.assertEqual(self.check('<button onclick="go()">x</button>'), ["an inline event handler (onclick)"])
        self.assertEqual(self.check('<a href="javascript:go()">x</a>'), ["a javascript: URL"])
        self.assertEqual(self.check('<script src="https://cdn.example.com/a.js"></script>'),
                         ["a <script> that loads from an absolute address; the policy allows this site only"])
        self.assertEqual(self.check('<img src="//tracker.example.com/p.gif">'),
                         ["a <img> that loads from an absolute address; the policy allows this site only"])
        self.assertEqual(self.check('<link rel="stylesheet" href="https://fonts.googleapis.com/css2">'),
                         ["a <link> that loads from an absolute address; the policy allows this site only"])
        self.assertEqual(self.check('<iframe src="https://www.youtube.com/embed/x"></iframe>'),
                         ["a <iframe> that loads from an absolute address; the policy allows this site only"])

    def test_a_link_that_opens_a_new_tab_must_not_hand_it_the_page(self):
        self.assertEqual(self.check('<a href="/en/" target="_blank">x</a>'), ["a link that opens a new tab without rel=noopener"])
        self.assertEqual(self.check('<a href="/en/" target="_blank" rel="noopener noreferrer">x</a>'), [])

    def test_pages_may_name_other_pages_and_sites_without_loading_them(self):
        html = ('<link rel="canonical" href="https://iitjeekota.com/en/"><link rel="alternate" hreflang="hi-IN" href="https://iitjeekota.com/hi/">'
                '<meta property="og:image" content="https://iitjeekota.com/media/og.png"><a href="https://maps.app.goo.gl/x" rel="external">map</a>'
                '<link rel="stylesheet" href="/_astro/a.css"><img src="/media/a.jpg"><video><source src="/media/f.mp4"></video>')
        self.assertEqual(self.check(html), [])


class NotFoundTest(unittest.TestCase):
    def check(self, html: str | None) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            if html is not None:
                (Path(tmp) / "404.html").write_text(html, encoding="utf-8")
            return [p.message for p in check_not_found(Path(tmp))]

    def test_a_site_without_a_404_page_is_refused(self):
        self.assertEqual(len(self.check(None)), 1)
        self.assertIn("no 404.html", self.check(None)[0])

    def test_the_404_page_is_noindex_and_has_no_address_of_its_own(self):
        self.assertEqual(self.check('<meta name="robots" content="noindex, nofollow"><title>x</title>'), [])
        self.assertEqual(self.check('<meta name="robots" content="max-image-preview:large">'), ["the 404 page is not noindex"])
        self.assertEqual(self.check('<meta name="robots" content="noindex"><link rel="canonical" href="https://iitjeekota.com/">'),
                         ["the 404 page names an address of its own (canonical or alternate)"])


if __name__ == "__main__":
    unittest.main()
