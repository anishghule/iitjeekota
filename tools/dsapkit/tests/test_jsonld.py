import unittest
from dataclasses import replace
from datetime import date

from dsapkit.content.model import page_dates
from dsapkit.errors import BuildError
from dsapkit.jsonio import read_json
from dsapkit.paths import Paths
from dsapkit.site import formats
from dsapkit.site.build import rules_age
from dsapkit.site.jsonld import PageGraph, check_graphs
from dsapkit.site.jsonld_build import Brand, Built, PageInfo, build_graph
from dsapkit.site.model import Fact, load_site

PATHS = Paths.discover()
RULES = read_json(PATHS.site / "jsonld-rules.json")
IDENTITY = read_json(PATHS.identity_json)
BRAND = Brand(IDENTITY["localNames"], tuple(IDENTITY["alternateNames"]), IDENTITY["description"], "/brand/medal-512.png", 512)
DATES = {"offset": "+05:30", "timeOfDay": "09:00:00"}


def info(route="Home", **kw):
    return PageInfo(kw.pop("title", "A title"), kw.pop("description", "A description."), route, **kw)


class FormatsTest(unittest.TestCase):
    def test_a_timestamp_must_carry_its_timezone(self):
        for ok in ("2026-11-01T09:00:00+05:30", "2026-11-01T09:00:00Z", "2026-11-01T09:00:00.250-08:00"):
            self.assertTrue(formats.is_datetime(ok), ok)
        for bad in ("2026-11-01", "2026-11-01T09:00:00", "2026-11-01T09:00+05:30", "2026-13-01T09:00:00+05:30",
                    "2026-11-01T25:00:00+05:30", "2026-11-01 09:00:00+05:30", "2026-02-30T09:00:00+05:30", 20261101):
            self.assertFalse(formats.is_datetime(bad), bad)

    def test_event_dates_take_a_day_or_a_local_time(self):
        for ok in ("2026-11-01", "2026-11-01T19:00", "2026-11-01T19:00:00", "2026-11-01T19:00:00+05:30"):
            self.assertTrue(formats.is_datetime_or_date(ok), ok)
        for bad in ("2026-11-01T19", "01/11/2026", "2026-11-31"):
            self.assertFalse(formats.is_datetime_or_date(bad), bad)

    def test_times_are_hh_mm_ss(self):
        self.assertTrue(formats.is_time("07:00:00"))
        for bad in ("07:00", "7:00:00", "24:00:00", "07:60:00"):
            self.assertFalse(formats.is_time(bad), bad)
        self.assertEqual(formats.clock_time("07:00"), "07:00:00")
        self.assertEqual(formats.clock_time("18:30:15"), "18:30:15")
        with self.assertRaises(BuildError):
            formats.clock_time("7am")

    def test_durations_urls_phones_countries_days_and_text(self):
        self.assertTrue(formats.is_duration("PT00H30M5S") and formats.is_duration("P1DT2H"))
        self.assertFalse(formats.is_duration("P") or formats.is_duration("30 minutes") or formats.is_duration("PT"))
        self.assertTrue(formats.is_url("https://iitjeekota.com/en/"))
        for bad in ("http://iitjeekota.com/", "/en/", "https://iitjeekota.com/a b", "https://"):
            self.assertFalse(formats.is_url(bad), bad)
        self.assertTrue(formats.is_phone("+91 22 6971 9828"))
        for bad in ("022 6971 9828", "+91", "6971 9828"):
            self.assertFalse(formats.is_phone(bad), bad)
        self.assertTrue(formats.is_country("IN"))
        self.assertFalse(formats.is_country("India") or formats.is_country("in"))
        self.assertTrue(formats.is_day_of_week("Monday") and formats.is_day_of_week("https://schema.org/Sunday"))
        self.assertFalse(formats.is_day_of_week("Mon"))
        self.assertTrue(formats.is_email("ghulesir@dsapghuletutorials.com"))
        self.assertFalse(formats.is_email("ghulesir") or formats.is_email("a@b"))
        self.assertTrue(formats.is_text("Plain words"))
        self.assertFalse(formats.is_text("  ") or formats.is_text("a <b>bold</b> claim"))
        self.assertTrue(formats.is_partial_date("1994") and formats.is_partial_date("1994-06"))
        self.assertFalse(formats.is_partial_date("94"))

    def test_unknown_format_is_an_error(self):
        with self.assertRaises(BuildError):
            formats.check_format("hex", "x")

    def test_stored_days_become_timestamps_in_the_site_timezone(self):
        self.assertEqual(formats.timestamp("2026-11-01", DATES), "2026-11-01T09:00:00+05:30")
        self.assertEqual(formats.timestamp("2026-11-01T09:30", DATES), "2026-11-01T09:30:00+05:30")
        for bad in ("01-11-2026", "2026-11-01T09", "tomorrow"):
            with self.assertRaises(BuildError):
                formats.timestamp(bad, DATES)

    def test_every_rule_names_a_known_format(self):
        for name, rule in RULES["types"].items():
            for prop, fmt in rule.get("fields", {}).items():
                self.assertIn(fmt, formats.CHECKS, f"{name}.{prop}")
        self.assertEqual(set(RULES["formats"]), set(formats.CHECKS))


class PageDatesTest(unittest.TestCase):
    def test_days_and_minutes_are_accepted(self):
        self.assertEqual(page_dates({"published": "2026-11-01", "modified": "2026-11-02T10:00"}, "x"), ("2026-11-01", "2026-11-02T10:00"))
        self.assertEqual(page_dates(None, "x"), (None, None))

    def test_bad_dates_fail_when_the_content_loads(self):
        for raw in ({"published": "1 Nov 2026"}, {"published": "2026-11-01T09:00:00+05:30"}, {"modified": "2026-11-01"},
                    {"published": "2026-11-02", "modified": "2026-11-01"}, {"published": "2026-11-01", "updated": "2026-11-01"}):
            with self.assertRaises(BuildError, msg=str(raw)):
                page_dates(raw, "x")

    def test_a_bare_day_is_not_before_a_time_on_that_day(self):
        self.assertEqual(page_dates({"published": "2026-11-01T09:00", "modified": "2026-11-01T09:00"}, "x")[1], "2026-11-01T09:00")


class RulesAgeTest(unittest.TestCase):
    def test_old_rules_must_be_read_again(self):
        self.assertEqual(rules_age({"checked": "2026-11-01", "staleAfterDays": 90}, date(2026, 11, 11)), 10)
        with self.assertRaises(BuildError):
            rules_age({"checked": "2026-11-01", "staleAfterDays": 90}, date(2027, 2, 1))


class BuilderTest(unittest.TestCase):
    def setUp(self):
        self.site = load_site(PATHS)

    def graph(self, route, locale="en", **kw):
        return build_graph(self.site, BRAND, self.site.routes[route], locale, info(**kw))

    def node(self, built, kind):
        return next(n for n in built.graph["@graph"] if kind in (n["@type"] if isinstance(n["@type"], list) else [n["@type"]]))

    def test_home_carries_organization_and_website_with_one_site_name(self):
        built = self.graph("home")
        org, site = self.node(built, "EducationalOrganization"), self.node(built, "WebSite")
        self.assertEqual(org["name"], site["name"])
        self.assertEqual(org["alternateName"], site["alternateName"])
        self.assertEqual(site["url"], "https://iitjeekota.com/")
        self.assertNotIn("potentialAction", site)
        self.assertEqual(org["address"]["addressCountry"], "IN")

    def test_other_languages_of_home_refer_to_the_one_organization(self):
        built = self.graph("home", "hi")
        kinds = [n["@type"] for n in built.graph["@graph"]]
        self.assertEqual(kinds, ["WebPage"])
        self.assertEqual(built.graph["@graph"][0]["isPartOf"], {"@id": "https://iitjeekota.com/#website"})
        self.assertEqual(built.graph["@graph"][0]["inLanguage"], "hi-IN")

    def test_centre_hours_are_written_hh_mm_ss(self):
        centre = self.node(self.graph("centre-sangvi-head-office"), "LocalBusiness")
        for spec in centre["openingHoursSpecification"]:
            self.assertRegex(spec["opens"], r"^\d\d:\d\d:\d\d$")
            self.assertRegex(spec["closes"], r"^\d\d:\d\d:\d\d$")
        self.assertEqual(centre["geo"]["latitude"], 18.581049)
        self.assertEqual(centre["parentOrganization"], {"@id": "https://iitjeekota.com/#organization"})

    def test_a_pending_fact_leaves_the_property_out_and_says_why(self):
        for fact in ("centre.wakad.hours", "centre.wakad.maps"):
            self.site.facts[fact] = Fact(fact, "pending", None, None, None)
        built = self.graph("centre-wakad")
        centre = self.node(built, "LocalBusiness")
        self.assertNotIn("openingHoursSpecification", centre)
        self.assertNotIn("hasMap", centre)
        self.assertIn("openingHoursSpecification", [p for p, _ in built.pending])
        self.assertNotIn("priceRange", centre)  # no price range is confirmed: a scholarship offer is not one

    def test_confirming_a_fact_brings_the_property_back(self):
        self.site.facts["centre.wakad.maps"] = Fact("centre.wakad.maps", "confirmed", "https://maps.app.goo.gl/x", "t", None)
        self.assertEqual(self.node(self.graph("centre-wakad"), "LocalBusiness")["hasMap"], "https://maps.app.goo.gl/x")

    def test_the_organization_carries_the_confirmed_email(self):
        org = self.node(self.graph("home"), "EducationalOrganization")
        self.assertEqual(org["email"], "ghulesir@dsapghuletutorials.com")
        self.assertEqual(org["contactPoint"]["email"], "ghulesir@dsapghuletutorials.com")

    def test_area_pages_are_not_local_businesses_and_point_at_the_nearest_centre(self):
        built = self.graph("area-aundh")
        types = [n["@type"] for n in built.graph["@graph"]]
        self.assertNotIn("LocalBusiness", types)
        page = self.node(built, "WebPage")
        self.assertEqual(page["about"], {"@id": "https://iitjeekota.com/en/centres/sangvi-head-office/#centre"})

    def test_breadcrumb_follows_the_registry_and_leaves_the_last_item_open(self):
        crumbs = self.node(self.graph("area-aundh"), "BreadcrumbList")["itemListElement"]
        self.assertEqual([c["name"] for c in crumbs], ["Home", "IIT JEE Coaching Pune", "Aundh"])
        self.assertNotIn("item", crumbs[-1])
        self.assertEqual([c["position"] for c in crumbs], [1, 2, 3])
        self.assertNotIn("BreadcrumbList", [n["@type"] for n in self.graph("home").graph["@graph"]])

    def test_course_list_only_on_the_programmes_page(self):
        listing = self.node(self.graph("programmes"), "ItemList")
        urls = [i["url"] for i in listing["itemListElement"]]
        self.assertIn("https://iitjeekota.com/en/class-11-jee/", urls)
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(all("ItemList" not in str(n["@type"]) for n in self.graph("class-11-jee").graph["@graph"]))

    def test_a_post_carries_timestamps_with_the_site_offset_and_a_separate_author(self):
        site = self.site
        site.routes["post-kota-or-pune"] = replace(site.routes["post-kota-or-pune"], planned=False)
        built = self.graph("post-kota-or-pune", published="2026-11-01", modified="2026-11-05T10:30", author="org.founder",
                           image="https://iitjeekota.com/media/og.png")
        post = self.node(built, "BlogPosting")
        self.assertEqual(post["datePublished"], "2026-11-01T09:00:00+05:30")
        self.assertEqual(post["dateModified"], "2026-11-05T10:30:00+05:30")
        self.assertEqual(post["author"][0]["@type"], "Person")
        self.assertEqual(post["image"], ["https://iitjeekota.com/media/og.png"])
        self.assertEqual(post["mainEntityOfPage"], {"@id": "https://iitjeekota.com/en/blogs/kota-or-pune/#webpage"})
        graphs = [PageGraph("home", "en", self.graph("home")), PageGraph("post-kota-or-pune", "en", built)]
        self.assertEqual([f for f in check_graphs(site, RULES, graphs) if f.severity == "error"], [])


class ValidatorTest(unittest.TestCase):
    """One test per kind of mistake Search Console reports, each caught before the page is built."""

    def setUp(self):
        self.site = load_site(PATHS)

    def errors(self, nodes, route="home", locale="en", context="https://schema.org"):
        graph = {"@context": context, "@graph": nodes}
        found = check_graphs(self.site, RULES, [PageGraph(route, locale, Built(graph))])
        return [f.message for f in found if f.severity == "error" and "breadcrumb" not in f.message and "reference to" not in f.message]

    def post(self, **props):
        return {"@type": "BlogPosting", "headline": "h", **props}

    def test_a_date_without_its_timezone(self):
        self.assertTrue(any("datePublished" in m for m in self.errors([self.post(datePublished="2026-11-01T09:00:00")])))
        self.assertTrue(any("datePublished" in m for m in self.errors([self.post(datePublished="2026-11-01")])))
        self.assertEqual(self.errors([self.post(datePublished="2026-11-01T09:00:00+05:30")]), [])

    def test_modified_before_published(self):
        errors = self.errors([self.post(datePublished="2026-11-02T00:00:00+05:30", dateModified="2026-11-01T00:00:00+05:30")])
        self.assertTrue(any("before datePublished" in m for m in errors))

    def test_opening_hours_not_in_hh_mm_ss(self):
        hours = {"@type": "OpeningHoursSpecification", "dayOfWeek": "Monday", "opens": "07:00", "closes": "20:00:00"}
        self.assertTrue(any("opens" in m for m in self.errors([hours])))
        bad_day = {**hours, "opens": "07:00:00", "dayOfWeek": "Mon"}
        self.assertTrue(any("dayOfWeek" in m for m in self.errors([bad_day])))

    def test_country_phone_and_urls(self):
        self.assertTrue(any("addressCountry" in m for m in self.errors([{"@type": "PostalAddress", "addressCountry": "India"}])))
        self.assertTrue(any("telephone" in m for m in self.errors([{"@type": "ContactPoint", "telephone": "022 6971 9828"}])))
        self.assertTrue(any("must be an absolute https URL" in m for m in self.errors([{"@type": "WebSite", "name": "n", "url": "/en/"}])))
        self.assertTrue(any("sameAs" in m or "absolute" in m for m in self.errors([{"@type": "WebSite", "name": "n", "url": "https://x.in/", "sameAs": ["http://x.in/"]}])))

    def test_event_start_must_be_a_day_or_local_time(self):
        event = {"@type": "Event", "name": "Test", "location": {"@type": "Place", "name": "p", "address": "a"}}
        self.assertTrue(any("startDate" in m for m in self.errors([{**event, "startDate": "1 Nov 2026"}])))
        self.assertEqual(self.errors([{**event, "startDate": "2026-11-01T19:00"}]), [])

    def test_geo_needs_five_decimals(self):
        self.assertTrue(any("decimals" in m for m in self.errors([{"@type": "GeoCoordinates", "latitude": 18.58, "longitude": 73.81712}])))

    def test_structure_mistakes(self):
        self.assertTrue(any("@context" in m for m in self.errors([{"@type": "WebSite", "name": "n", "url": "https://x.in/"}], context="http://schema.org")))
        self.assertTrue(any("empty string" in m for m in self.errors([{"@type": "WebSite", "name": " ", "url": "https://x.in/"}])))
        dup = {"@type": "WebSite", "@id": "https://x.in/#w", "name": "n", "url": "https://x.in/"}
        self.assertTrue(any("more than once" in m for m in self.errors([dup, dup])))
        self.assertTrue(any("FAQPage is not used" in m for m in self.errors([{"@type": "FAQPage"}])))
        self.assertTrue(any("must not carry" in m for m in self.errors([{"@type": "LocalBusiness", "name": "n", "address": "a", "aggregateRating": {}}])))
        self.assertTrue(any("potentialAction" in m for m in self.errors([{"@type": "WebSite", "name": "n", "url": "https://x.in/", "potentialAction": {}}])))

    def test_organization_logo_size_and_html_text(self):
        logo = {"@type": "EducationalOrganization", "name": "n", "logo": {"@type": "ImageObject", "url": "https://x.in/l.png", "width": 64, "height": 64}}
        self.assertTrue(any("at least 112" in m for m in self.errors([logo])))
        self.assertTrue(any("name" in m for m in self.errors([{"@type": "WebSite", "name": "<b>n</b>", "url": "https://x.in/"}])))

    def test_item_lists_need_unique_urls_and_positions(self):
        item = lambda p, u: {"@type": "ListItem", "position": p, "url": u}
        same = {"@type": "ItemList", "itemListElement": [item(1, "https://x.in/a/"), item(2, "https://x.in/a/"), item(3, "https://x.in/c/")]}
        self.assertTrue(any("unique url" in m for m in self.errors([same])))

    def test_a_breadcrumb_that_differs_from_the_trail_is_an_error(self):
        graph = {"@context": "https://schema.org", "@graph": [{"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://iitjeekota.com/en/"},
            {"@type": "ListItem", "position": 2, "name": "Aundh"}]}]}
        found = check_graphs(self.site, RULES, [PageGraph("area-aundh", "en", Built(graph))])
        self.assertTrue(any("does not match" in f.message for f in found))
        missing = check_graphs(self.site, RULES, [PageGraph("area-aundh", "en", Built({"@context": "https://schema.org", "@graph": []}))])
        self.assertTrue(any("no BreadcrumbList" in f.message for f in missing))


if __name__ == "__main__":
    unittest.main()
