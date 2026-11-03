import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from dsapkit.content.gates import section_waiting
from dsapkit.content.model import SectionSpec, load_content
from dsapkit.content.widgets import resolve_widget
from dsapkit.errors import BuildError
from dsapkit.paths import Paths
from dsapkit.site.model import load_site
from dsapkit.web.export import name_lines, export_web

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


    def test_guides_become_typed_blocks_with_an_author_and_dates(self):
        post = self.page("en", "post-kota-or-pune")
        self.assertEqual(post["template"], "post")
        self.assertEqual(post["author"], {"name": "Prof. Ghule", "path": "/en/about/"})
        self.assertRegex(post["dates"]["published"], r"^\d{4}-\d{2}-\d{2}$")
        kinds = {b["type"] for b in post["blocks"]}
        self.assertLessEqual(kinds, {"h2", "h3", "p", "ul", "ol"})
        self.assertNotIn("**", json.dumps(post["blocks"]))
        self.assertNotIn("{{", json.dumps(post))

    def test_a_guide_that_waits_for_a_fact_is_not_published(self):
        self.assertFalse((self.data / "pages" / "en" / "post-foundation-when-to-start.json").exists())

    def test_pillars_list_the_pages_under_them_by_their_own_headings(self):
        programmes = self.page("en", "programmes")
        spokes = next(s for s in programmes["sections"] if s["id"] == "spokes")
        paths = [l["path"] for l in spokes["links"]]
        self.assertIn("/en/class-11-jee/", paths)
        self.assertIn("/en/fees-and-batches/", paths)
        self.assertTrue(all(l["name"] and l["description"] for l in spokes["links"]))
        pune = next(s for s in self.page("en", "pune")["sections"] if s["id"] == "spokes")
        self.assertIn("/en/iit-jee-coaching-aundh/", [l["path"] for l in pune["links"]])

    def test_area_pages_end_with_links_to_the_pages_around_them(self):
        related = self.page("en", "area-aundh")["related"]
        paths = [r["path"] for r in related]
        self.assertIn("/en/iit-jee-coaching-pune/", paths)
        self.assertIn("/en/centres/sangvi-head-office/", paths)
        self.assertNotIn("/en/iit-jee-coaching-aundh/", paths)
        self.assertNotIn("related", self.page("en", "home"))

    def test_every_page_carries_its_dates(self):
        for route, locale in self.report.pages:
            self.assertIn("dates", self.page(locale, route))

    def test_the_contact_page_has_centres_and_no_embedded_map(self):
        contact = self.page("en", "contact")
        self.assertEqual([s["id"] for s in contact["sections"]], ["visit", "enquiry"])
        self.assertEqual(contact["sections"][0]["component"], "ContactCentres")

    def test_areas_carry_every_confirmed_route_to_the_centres(self):
        site = json.loads((self.data / "site.json").read_text(encoding="utf-8"))
        aundh = next(a for a in site["areas"] if a["id"] == "aundh")
        self.assertEqual({r["centre"] for r in aundh["routes"]}, {"sangvi-head-office", "wakad"})
        self.assertEqual(aundh["neighbours"][0], "baner")

    def test_a_rebuild_changes_no_file_so_a_deployment_never_moves_a_date(self):
        """Google distrusts a lastmod that changes on every deployment. Nothing time-dependent may enter an export."""
        import hashlib
        import time
        def tree(root):
            return {str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(Path(root).rglob("*")) if f.is_file()}
        time.sleep(1.1)  # a clock-based value would differ by now
        with tempfile.TemporaryDirectory() as second:
            site = load_site(PATHS)
            export_web(PATHS, site, load_content(PATHS, site.locales), Path(second))
            self.assertEqual(tree(second), tree(self.tmp.name))

    def test_every_date_comes_from_the_page_and_nowhere_else(self):
        """The visible date, the sitemap lastmod and the structured data's dateModified are the page's own `dates.modified`."""
        import re
        from dsapkit.site.formats import timestamp
        offsets = self.site.config["dates"]
        sitemap = {}
        for locale in self.site.locales:
            xml = (self.data.parent / "public" / f"sitemap-{locale}.xml")
            if xml.exists():
                for loc, mod in re.findall(r"<loc>([^<]+)</loc>(?:<lastmod>([^<]+)</lastmod>)?", xml.read_text(encoding="utf-8")):
                    sitemap[loc] = mod
        for route, locale in self.report.pages:
            page = self.page(locale, route)
            modified = page["dates"]["modified"]
            url = self.site.url(route, locale)
            self.assertEqual(sitemap.get(url) or None, modified, url)
            webpage = next(n for n in page["jsonld"][0]["@graph"] if n["@type"] in ("WebPage", "CollectionPage", "AboutPage", "ContactPage"))
            self.assertEqual(webpage.get("dateModified"), timestamp(modified, offsets) if modified else None, url)

    def test_a_page_without_a_modified_date_states_none(self):
        """No date is invented for a page that has none: no lastmod, no dateModified."""
        import re
        site = load_site(PATHS)
        content = load_content(PATHS, site.locales)
        for key, page in list(content.pages.items()):
            content.pages[key] = replace(page, published=None, modified=None)
        with tempfile.TemporaryDirectory() as bare:
            export_web(PATHS, site, content, Path(bare))
            sitemap = (Path(bare) / "public" / "sitemap-en.xml").read_text(encoding="utf-8")
            dated = re.findall(r"<loc>([^<]+)</loc><lastmod>", sitemap)
            self.assertTrue(all("/blogs/" in url for url in dated), dated)  # only the guides keep their own dates
            home = json.loads((Path(bare) / "data" / "pages" / "en" / "home.json").read_text(encoding="utf-8"))
            self.assertNotIn("dateModified", json.dumps(home["jsonld"]))
            self.assertEqual(home["dates"], {"published": None, "modified": None})

    def test_the_navbar_is_programmes_to_contact_with_results_and_no_area_hub(self):
        routes = json.loads((self.data / "site.json").read_text(encoding="utf-8"))["routes"]
        order = [i for i, _ in sorted(((i, r["nav"]) for i, r in routes.items() if r["nav"]), key=lambda x: x[1])]
        self.assertEqual(order, ["programmes", "fees-and-batches", "powered-by-kota", "centres", "jee-syllabus", "results", "contact"])
        self.assertIsNone(routes["pimpri-chinchwad"]["nav"])
        self.assertEqual({r["areaHub"] for r in routes.values() if r["areaHub"]}, {"pune", "pimpri-chinchwad"})

    def test_brand_lines_join_to_the_brand_name(self):
        brand = json.loads((self.data / "site.json").read_text(encoding="utf-8"))["brand"]
        for locale, name in brand["names"].items():
            self.assertEqual(" ".join(brand["nameLines"][locale]), name)

    def test_brand_lines_that_drift_from_the_name_fail(self):
        identity = {"localNames": {"en": "A B"}, "nameLines": {"en": ["A", "C"]}}
        with self.assertRaises(BuildError):
            name_lines(identity)


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
