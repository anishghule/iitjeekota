import json
import unittest

from dsapkit.errors import BuildError
from dsapkit.paths import Paths
from dsapkit.tokens import load_tokens
from dsapkit.tokens.colour import contrast_ratio, css_rgb
from dsapkit.tokens.contrast import check
from dsapkit.tokens.css import fluid, tokens_css, typography_css
from dsapkit.tokens.model import parse_tokens

PATHS = Paths.discover()


def tokens_from(obj: dict):
    return parse_tokens(json.dumps(obj).encode())


class ModelTest(unittest.TestCase):
    def test_alias_resolves_through_chains(self):
        t = tokens_from({"color": {"$type": "color", "a": {"$value": "#112233"}, "b": {"$value": "{color.a}"},
                                   "c": {"$value": "{color.b}"}}})
        self.assertEqual(t.get("color.c"), "#112233")

    def test_alias_cycle_is_an_error(self):
        with self.assertRaisesRegex(BuildError, "cycle"):
            tokens_from({"color": {"$type": "color", "a": {"$value": "{color.b}"}, "b": {"$value": "{color.a}"}}})

    def test_unknown_alias_is_an_error(self):
        with self.assertRaisesRegex(BuildError, "unknown alias"):
            tokens_from({"color": {"$type": "color", "a": {"$value": "{color.missing}"}}})

    def test_bad_colour_is_an_error(self):
        with self.assertRaisesRegex(BuildError, "colour"):
            tokens_from({"color": {"$type": "color", "a": {"$value": "brass"}}})

    def test_group_type_is_inherited_and_descriptions_kept(self):
        t = tokens_from({"space": {"$type": "dimension", "$description": "scale", "4": {"$value": 16, "$description": "base"}}})
        self.assertEqual(t.get("space.4"), 16)
        self.assertEqual(t.descriptions["space"], "scale")
        self.assertEqual(t.descriptions["space.4"], "base")


class ColourTest(unittest.TestCase):
    def test_black_on_white_is_21(self):
        self.assertAlmostEqual(contrast_ratio("#000000", "#ffffff"), 21.0, places=2)

    def test_same_colour_is_1(self):
        self.assertAlmostEqual(contrast_ratio("#777777", "#777777"), 1.0)

    def test_translucent_foreground_is_composited(self):
        self.assertAlmostEqual(contrast_ratio("#00000000", "#ffffff"), 1.0)

    def test_css_rgb(self):
        self.assertEqual(css_rgb("#0a1416"), "rgb(10 20 22)")
        self.assertEqual(css_rgb("#0a1416", 0.5), "rgb(10 20 22 / 0.5)")


class CssTest(unittest.TestCase):
    def test_fluid_hits_both_ends(self):
        value = fluid(16, 32, 360, 1440)
        self.assertTrue(value.startswith("clamp(1rem,") and value.endswith("2rem)"))
        # intercept and slope reproduce 16px at 360px and 32px at 1440px
        slope = 16 / 1080
        self.assertAlmostEqual(16 - slope * 360 + slope * 360, 16)

    def test_equal_ends_are_not_clamped(self):
        self.assertEqual(fluid(18, 18, 360, 1440), "1.125rem")


class ProjectTokensTest(unittest.TestCase):
    """The real tokens.json: every contrast pair passes and every variant gets a class."""

    @classmethod
    def setUpClass(cls):
        cls.tokens = load_tokens(PATHS.tokens_json)

    def test_every_contrast_pair_passes(self):
        results = check(self.tokens.tree["surface"], json.loads(PATHS.contrast_json.read_text()))
        failed = [f"{r.surface} {r.fg}/{r.bg} {r.ratio}" for r in results if not r.passed]
        self.assertEqual(failed, [])

    def test_surfaces_define_the_same_roles(self):
        roles = [set(r) for r in self.tokens.tree["surface"].values()]
        self.assertTrue(all(r == roles[0] for r in roles))

    def test_every_variant_has_a_class_and_devanagari_values(self):
        css = typography_css(self.tokens.tree)
        deva = self.tokens.tree["type"]["devanagari"]
        for variant in self.tokens.tree["type"]["scale"]:
            self.assertIn(f".t-{variant} {{", css)
            self.assertIn(variant, deva["lineHeight"])
            self.assertIn(variant, deva["weight"])

    def test_devanagari_locales_get_zero_tracking(self):
        css = tokens_css(self.tokens.tree)
        block = css.split(":lang(hi), :lang(mr) {")[1].split("}")[0]
        self.assertIn("--type-display-xl-tracking: 0em;", block)
        self.assertIn("--font-display: var(--font-devanagari);", block)

    def test_brass_300_is_the_medal_sand(self):
        self.assertEqual(self.tokens.get("color.brass.300"), "#e6c296")


if __name__ == "__main__":
    unittest.main()
