import unittest

from dsapkit.content.markdown import parse_blocks, split_bold
from dsapkit.errors import BuildError


class BlocksTest(unittest.TestCase):
    def test_headings_paragraphs_and_lists(self):
        blocks = parse_blocks(["## A heading", "Two lines\nof one paragraph.", "* one\n* two", "- dash\n- items", "1. first\n2. second", "### Smaller"], "x")
        self.assertEqual([b.kind for b in blocks], ["h2", "p", "ul", "ul", "ol", "h3"])
        self.assertEqual(blocks[1].texts, ("Two lines of one paragraph.",))
        self.assertEqual(blocks[2].texts, ("one", "two"))
        self.assertEqual(blocks[4].texts, ("first", "second"))

    def test_raw_html_is_refused(self):
        for text in ("A <script>alert(1)</script> paragraph", "<img src=x onerror=y>", "<!-- hidden -->", "see <b>this</b>"):
            with self.assertRaises(BuildError, msg=text):
                parse_blocks([text], "x")

    def test_mixed_structure_is_refused(self):
        with self.assertRaises(BuildError):
            parse_blocks(["A paragraph\n* then a list item"], "x")
        with self.assertRaises(BuildError):
            parse_blocks(["## A heading\nand text under it"], "x")

    def test_comparison_signs_in_text_are_not_html(self):
        self.assertEqual(parse_blocks(["Marks of 5 < 10 and 10 > 5."], "x")[0].kind, "p")

    def test_every_project_guide_parses(self):
        from pathlib import Path
        from dsapkit.paths import Paths
        root = Paths.discover().content / "posts" / "en"
        for file in sorted(root.glob("*.md")):
            body = file.read_text(encoding="utf-8").split("\n---\n", 1)[1]
            parse_blocks([b.strip() for b in body.split("\n\n") if b.strip()], file.name)


class BoldTest(unittest.TestCase):
    def test_bold_runs_lose_their_marks(self):
        self.assertEqual(split_bold("a **b** c"), [("a ", False), ("b", True), (" c", False)])
        self.assertEqual(split_bold("plain"), [("plain", False)])
        self.assertEqual(split_bold("**all**"), [("all", True)])


if __name__ == "__main__":
    unittest.main()
