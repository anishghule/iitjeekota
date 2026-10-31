import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from dsapkit.content.gates import section_waiting
from dsapkit.content.model import SectionSpec, load_content
from dsapkit.content.widgets import resolve_widget
from dsapkit.paths import Paths
from dsapkit.site.model import load_site
from dsapkit.web.export import export_web

PATHS = Paths.discover()


def confirmed(site, fact_id, value):
    site.facts[fact_id] = replace(site.facts[fact_id], status="confirmed", value=value)


def pending(site, fact_id):
    site.facts[fact_id] = replace(site.facts[fact_id], status="pending", value=None)


class WidgetTest(unittest.TestCase):
    def setUp(self):
        self.site = load_site(PATHS)
        self.syllabus = load_content(PATHS, self.site.locales).syllabus
        confirmed(self.site, "batch.size", "30")
        pending(self.site, "fees")

    def resolve(self, raw):
        return resolve_widget(raw, self.site, self.syllabus, "en")

    def test_facts_fill_and_notes_drop(self):
        r = self.resolve({"$note": "x", "size": "{{fact:batch.size}} students", "n": 3})
        self.assertEqual(r.value, {"size": "30 students", "n": 3})

    def test_an_item_waiting_for_a_fact_leaves_its_list(self):
        r = self.resolve({"rows": [{"a": "kept"}, {"a": "held", "requires": ["fees"]}, "{{fact:fees}}"]})
        self.assertEqual(r.value, {"rows": [{"a": "kept"}]})
        self.assertEqual([path for path, _ in r.held], ["rows[1]", "rows[2]"])

    def test_a_widget_waiting_as_a_whole_is_not_shown(self):
        r = self.resolve({"requires": ["fees"], "rows": []})
        self.assertIsNone(r.value)

    def test_unknown_facts_and_page_links_are_errors(self):
        self.assertTrue(self.resolve({"requires": ["no.such.fact"]}).unknown)
        self.assertTrue(self.resolve({"a": "see [fees](page:fees-and-batches)"}).unknown)


class MediaGateTest(unittest.TestCase):
    def test_a_section_waits_for_an_awaited_slot(self):
        site = load_site(PATHS)
        content = load_content(PATHS, site.locales)
        content.media["home/classroom-film"] = "awaited"
        spec = SectionSpec("classroom", "prose", gates=("media:home/classroom-film",))
        self.assertEqual(section_waiting(spec, content, site), (["media:home/classroom-film"], []))
        content.media["home/classroom-film"] = "supplied"
        self.assertEqual(section_waiting(spec, content, site), ([], []))
        self.assertEqual(section_waiting(SectionSpec("x", "prose", gates=("media:nope",)), content, site)[1], ["media:nope"])


class ExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        site = load_site(PATHS)
        cls.report = export_web(PATHS, site, load_content(PATHS, site.locales), Path(cls.tmp.name))
        cls.data = Path(cls.tmp.name) / "data"
        cls.site = site

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def page(self, locale, route):
        return json.loads((self.data / "pages" / locale / f"{route}.json").read_text(encoding="utf-8"))

    def test_only_live_pages_are_written(self):
        for route, locale in self.report.pages:
            self.assertTrue(self.site.is_live(route), route)

    def test_gated_sections_are_left_out_and_facts_are_filled(self):
        home = self.page("en", "home")
        ids = [s["id"] for s in home["sections"]]
        self.assertNotIn("results", ids)  # waits for results.verified
        self.assertNotIn("{{", json.dumps(home))

    def test_links_point_only_at_live_pages(self):
        for route, locale in self.report.pages:
            for part in _parts(self.page(locale, route)):
                if "path" in part:
                    target = next(r for r in self.site.routes.values() if r.path(locale) == part["path"])
                    self.assertTrue(self.site.is_live(target.id), part)

    def test_site_data_has_no_pending_facts(self):
        site = json.loads((self.data / "site.json").read_text(encoding="utf-8"))
        for fact_id in site["facts"]["en"]:
            self.assertTrue(self.site.facts[fact_id].confirmed, fact_id)


def _parts(value):
    if isinstance(value, dict):
        if "text" in value and set(value) <= {"text", "path"}:
            yield value
        for v in value.values():
            yield from _parts(v)
    elif isinstance(value, list):
        for v in value:
            yield from _parts(v)


if __name__ == "__main__":
    unittest.main()
