import json
import unittest
import xml.etree.ElementTree as ET

from dsapkit.errors import BuildError
from dsapkit.icons.build import _validate, load_icons
from dsapkit.icons.geometry import path_points
from dsapkit.paths import Paths

PATHS = Paths.discover()
CFG = json.loads((PATHS.icons / "icons.json").read_text())


def svg(body: str) -> ET.Element:
    return ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{body}</svg>')


class GeometryTest(unittest.TestCase):
    def test_relative_and_absolute_commands(self):
        self.assertEqual(path_points("M4 12h15"), [(4, 12), (19, 12)])
        self.assertEqual(path_points("m13 6 6 6-6 6"), [(13, 6), (19, 12), (13, 18)])
        self.assertEqual(path_points("M2 2V20Z"), [(2, 2), (2, 20)])


class RulesTest(unittest.TestCase):
    def test_every_project_icon_passes(self):
        icons = load_icons(PATHS)
        self.assertEqual({i.name for i in icons}, set(CFG["icons"]))

    def test_missing_accent_is_rejected(self):
        with self.assertRaisesRegex(BuildError, "accent"):
            _validate("demo", svg('<path d="M4 12h15"/>'), CFG)

    def test_off_grid_point_is_rejected(self):
        with self.assertRaisesRegex(BuildError, "outside"):
            _validate("demo", svg('<path class="ac" d="M4 12h25"/>'), CFG)

    def test_styling_on_the_root_is_rejected(self):
        bad = ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke="red"><path class="ac" d="M4 12h5"/></svg>')
        with self.assertRaisesRegex(BuildError, "only carry viewBox"):
            _validate("demo", bad, CFG)

    def test_unknown_element_is_rejected(self):
        with self.assertRaisesRegex(BuildError, "not allowed"):
            _validate("demo", svg('<text>x</text><path class="ac" d="M4 12h5"/>'), CFG)


if __name__ == "__main__":
    unittest.main()
