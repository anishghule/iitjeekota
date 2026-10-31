import unittest
from dataclasses import replace

from dsapkit.jsonio import read_json
from dsapkit.paths import Paths
from dsapkit.site.jsonld import Fixture, _fill, check_fixtures, load_fixtures
from dsapkit.site.keywords import check_planner_limits, planner_files
from dsapkit.site.links import breadcrumbs, check_links, clicks_from_home, live_links
from dsapkit.site.model import Fact, Keywords, load_site
from dsapkit.site.validate import check_commutes, check_keywords, check_routes, check_site, commute_notes
from dsapkit.tokens import load_tokens

PATHS = Paths.discover()


def project_site():
    return load_site(PATHS)


class RegistryTest(unittest.TestCase):
    def test_project_registry_is_clean(self):
        site = project_site()
        self.assertEqual(check_site(site, load_tokens(PATHS.tokens_json)) + check_links(site), [])

    def test_area_and_centre_pages_are_derived(self):
        site = project_site()
        wakad = site.routes["area-wakad"]
        self.assertEqual(wakad.path("en"), "/en/iit-jee-coaching-wakad/")
        self.assertEqual(wakad.keywords["en"].primary, "iit jee coaching in wakad")
        self.assertEqual(site.routes["centre-wakad"].keywords["en"].primary, "d-sap ghule tutorials wakad")

    def test_breadcrumbs_stop_at_three(self):
        site = project_site()
        trail = breadcrumbs(site, site.routes["area-wakad"], "en")
        self.assertEqual([c.name for c in trail], ["Home", "IIT JEE Coaching Pimpri-Chinchwad", "Wakad"])
        self.assertEqual(breadcrumbs(site, site.routes["home"], "en"), [])

    def test_every_ready_page_is_within_two_clicks(self):
        site = project_site()
        depth = clicks_from_home(site)
        for route_id, route in site.routes.items():
            if site.is_live(route_id):
                self.assertLessEqual(depth[route_id], 2, route_id)

    def test_shared_primary_keyword_is_caught(self):
        site = project_site()
        baner = site.routes["area-baner"]
        site.routes["area-baner"] = replace(baner, keywords={**baner.keywords, "en": Keywords("iit jee coaching in wakad", (), False)})
        self.assertTrue(any("both target" in p for p in check_keywords(site)))

    def test_unknown_gate_and_missing_pillar_are_caught(self):
        site = project_site()
        jee_main = site.routes["jee-main-coaching"]
        site.routes["jee-main-coaching"] = replace(jee_main, gates=("no.such.fact",), pillar="nowhere")
        problems = check_routes(site)
        self.assertTrue(any("not in facts.json" in p for p in problems))
        self.assertTrue(any("does not exist" in p for p in problems))

    def test_gated_page_is_not_live_and_not_linked(self):
        site = project_site()
        self.assertFalse(site.is_live("powered-by-kota"))
        self.assertNotIn("powered-by-kota", live_links(site, site.routes["area-wakad"]))


class CommuteTest(unittest.TestCase):
    def test_unknown_source_and_missing_nearest_route_are_caught(self):
        site = project_site()
        area = site.areas["aundh"]
        area["commute"] = {"status": "placeholder", "routes": [{"centre": "wakad", "km": 8.6, "source": "a guess"}]}
        problems = check_commutes(site)
        self.assertTrue(any("not in site.json commuteSources" in p for p in problems))
        self.assertTrue(any("no commute to its nearest centre" in p for p in problems))

    def test_confirmed_commute_needs_a_time_and_who_checked(self):
        site = project_site()
        site.areas["baner"]["nearestCentre"] = "wakad"
        site.areas["baner"]["commute"] = {"status": "confirmed", "routes": [{"centre": "wakad", "km": 5.3, "source": "d-sap"}]}
        problems = check_commutes(site)
        self.assertTrue(any("needs a time to the nearest centre" in p for p in problems))
        self.assertTrue(any("who checked it" in p for p in problems))

    def test_area_page_waits_for_a_confirmed_commute(self):
        site = project_site()
        route = {"centre": "sangvi-head-office", "km": 3.4, "freeFlowMinutes": 6, "source": "osm"}
        site.areas["aundh"]["commute"] = {"status": "placeholder", "routes": [route]}
        self.assertIn("commute.aundh", site.pending_gates(site.routes["area-aundh"]))
        site.areas["aundh"]["commute"] = {"status": "confirmed", "checked": "test", "routes": [route]}
        self.assertNotIn("commute.aundh", site.pending_gates(site.routes["area-aundh"]))

    def test_closer_centre_is_noted(self):
        site = project_site()
        self.assertEqual(commute_notes(site), [])
        site.areas["aundh"]["nearestCentre"] = "wakad"
        self.assertTrue(any(n.startswith("Aundh:") for n in commute_notes(site)))


class KeywordVolumeTest(unittest.TestCase):
    def test_lookup_ignores_case_and_spacing(self):
        site = project_site()
        self.assertEqual(site.volume("IIT  coaching in Pune")["monthly"], [10, 100])
        self.assertIsNone(site.volume("kota coaching in pune")["monthly"])
        self.assertIsNone(site.volume("never checked"))


class KeywordPlannerTest(unittest.TestCase):
    def test_project_keywords_fit_google_ads_limits(self):
        self.assertEqual(check_planner_limits(project_site()), [])

    def test_long_keyword_and_too_many_seeds_are_caught(self):
        site = project_site()
        faq = site.routes["faq"]
        site.routes["faq"] = replace(faq, keywords={**faq.keywords, "en": Keywords("word " * 11, (), False)})
        site.config["keywordPlanner"]["seedRoutes"] = list(site.routes)[:11]
        problems = check_planner_limits(site)
        self.assertTrue(any("more than 10 words" in p for p in problems))
        self.assertTrue(any("seeds" in p for p in problems))

    def test_files_cover_every_locale_and_map_back_to_pages(self):
        files = planner_files(project_site())
        self.assertEqual({"search-volume-en.txt", "search-volume-hi.txt", "search-volume-mr.txt",
                          "seed-keywords-en.txt", "keyword-map.csv"}, set(files))
        self.assertIn("en,iit jee coaching in wakad,area-wakad,primary,", files["keyword-map.csv"])


class JsonLdTest(unittest.TestCase):
    RULES = read_json(PATHS.site / "jsonld-rules.json")

    def fixture(self, site, data, page="home"):
        pending = []
        filled = _fill({**data, "$page": page}, site, pending)
        return Fixture("test", page, "en", filled, pending)

    def test_pending_fact_drops_the_property_and_confirming_restores_it(self):
        site = project_site()
        data = {"@context": "https://schema.org", "@graph": [{"@type": "WebSite", "name": "D", "url": "{{origin}}/", "email": "{{fact:contact.email}}"}]}
        site.facts["contact.email"] = Fact("contact.email", "pending", None, None, None)
        fx = self.fixture(site, data)
        self.assertNotIn("email", fx.data["@graph"][0])
        site.facts["contact.email"] = Fact("contact.email", "confirmed", "jee@example.com", "test", None)
        fx = self.fixture(site, data)
        self.assertEqual(fx.data["@graph"][0]["email"], "jee@example.com")

    def test_structured_fact_fields_fill_one_value_each(self):
        site = project_site()
        site.facts["centre.wakad.geo"] = Fact("centre.wakad.geo", "confirmed", {"latitude": 18.59, "longitude": 73.77}, "test", None)
        data = {"@graph": [{"@type": "GeoCoordinates", "latitude": "{{fact:centre.wakad.geo#latitude}}",
                            "longitude": "{{fact:centre.wakad.geo#longitude}}", "elevation": "{{fact:centre.wakad.geo#elevation}}"}]}
        fx = self.fixture(site, data, page="centre-wakad")
        node = fx.data["@graph"][0]
        self.assertEqual((node["latitude"], node["longitude"]), (18.59, 73.77))
        self.assertNotIn("elevation", node)
        self.assertTrue(any("unknown fact" in why for _, why in fx.pending))

    def test_retired_type_and_missing_required_are_errors(self):
        site = project_site()
        fx = self.fixture(site, {"@graph": [{"@type": "FAQPage"}, {"@type": "WebSite", "name": "D"}]})
        messages = [f.message for f in check_fixtures(site, self.RULES, [fx]) if f.severity == "error"]
        self.assertTrue(any("FAQPage is not used" in m for m in messages))
        self.assertTrue(any("missing required url" in m for m in messages))

    def test_breadcrumb_must_match_the_registry(self):
        site = project_site()
        wrong = {"@graph": [{"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "{{origin}}/en/"},
            {"@type": "ListItem", "position": 2, "name": "Wakad"}]}]}
        fx = self.fixture(site, wrong, page="area-wakad")
        self.assertTrue(any("does not match" in f.message for f in check_fixtures(site, self.RULES, [fx])))

    def test_project_fixtures_have_no_errors(self):
        site = project_site()
        fixtures = load_fixtures(PATHS.site / "jsonld", site)
        errors = [f"{f.fixture}: {f.message}" for f in check_fixtures(site, self.RULES, fixtures) if f.severity == "error"]
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
