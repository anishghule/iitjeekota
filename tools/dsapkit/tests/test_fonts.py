import json
import unittest
from pathlib import Path

from dsapkit.fonts.config import load_fonts_config, role_instance
from dsapkit.fonts.google import parse_css, stretch_matches
from dsapkit.fonts.sfnt import Face, fallback_overrides
from dsapkit.paths import Paths
from dsapkit.tokens import load_tokens
from dsapkit.tokens.build import preload_files

PATHS = Paths.discover()
ARIAL = Path("/System/Library/Fonts/Supplemental/Arial.ttf")

CSS = """
/* latin */
@font-face {
  font-family: 'Archivo';
  font-style: normal;
  font-weight: 100 900;
  font-stretch: 62% 125%;
  src: url(https://fonts.gstatic.com/s/archivo/v25/a.woff2) format('woff2');
  unicode-range: U+0000-00FF;
}
@font-face {
  font-family: 'Archivo';
  font-weight: 800;
  font-stretch: semi-expanded;
  src: url(https://fonts.gstatic.com/s/archivo/v25/b.ttf) format('truetype');
}
"""


class GoogleCssTest(unittest.TestCase):
    def test_parses_subsets_and_descriptors(self):
        faces = parse_css(CSS)
        self.assertEqual(len(faces), 2)
        self.assertEqual(faces[0].subset, "latin")
        self.assertEqual(faces[0].weight, "100 900")
        self.assertEqual(faces[0].stretch, "62% 125%")
        self.assertEqual(faces[1].subset, "")

    def test_stretch_keywords(self):
        self.assertTrue(stretch_matches("semi-expanded", 112.5))
        self.assertTrue(stretch_matches("normal", 100))
        self.assertFalse(stretch_matches("normal", 112.5))


class ConfigTest(unittest.TestCase):
    def test_roles_match_tokens_and_instances_follow_variants(self):
        tokens = load_tokens(PATHS.tokens_json)
        cfg = load_fonts_config(PATHS.fonts_config, tokens)
        weight, stretch = role_instance(tokens, cfg, "display")
        variant = tokens.tree["type"]["scale"][cfg.metrics_variant["display"]]
        self.assertEqual((weight, stretch), (variant["weight"], variant["stretch"]))
        self.assertEqual(role_instance(tokens, cfg, "devanagari")[1], 100.0)


class WebFallbackTest(unittest.TestCase):
    def test_a_fallback_must_follow_its_family_in_the_token_stack(self):
        tokens = load_tokens(PATHS.tokens_json)
        cfg = load_fonts_config(PATHS.fonts_config, tokens)
        self.assertEqual([f.family for f in cfg.family("body").web_fallbacks], ["Inter"])
        stack = tokens.tree["font"]["family"]["body"]
        self.assertEqual(stack[:3], ["Google Sans Flex", "Inter", "Arial"])
        self.assertEqual([(f.family, fb) for f, fb in cfg.vendored() if f.role == "body"],
                         [("Google Sans Flex", False), ("Inter", True)])

    def test_fallbacks_are_locked_but_never_preloaded(self):
        lock = json.loads(PATHS.fonts_lock.read_text())
        inter = [f for f in lock["files"] if f["family"] == "Inter"]
        self.assertTrue(inter and all(f["fallback"] for f in inter))
        preload = preload_files(lock, "/fonts")
        self.assertTrue(preload)
        self.assertFalse([p for p in preload if "inter" in p])


class LockTest(unittest.TestCase):
    def test_every_locked_file_exists(self):
        lock = json.loads(PATHS.fonts_lock.read_text())
        missing = [f["file"] for f in lock["files"] if not (PATHS.fonts_dir / f["file"]).exists()]
        self.assertEqual(missing, [])


@unittest.skipUnless(ARIAL.exists(), "Arial is only present on macOS")
class SfntTest(unittest.TestCase):
    def test_reads_arial_metrics(self):
        face = Face.from_path(ARIAL)
        self.assertEqual(face.units_per_em, 2048)
        self.assertEqual(face.ascender, 1854)
        self.assertGreater(face.x_height, 1000)
        self.assertGreater(face.advance("JEE"), face.advance("JE"))

    def test_fallback_of_a_font_to_itself_is_neutral(self):
        face = Face.from_path(ARIAL)
        self.assertEqual(fallback_overrides(face, face)["sizeAdjust"], 100.0)


if __name__ == "__main__":
    unittest.main()
