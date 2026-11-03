import unittest
import xml.etree.ElementTree as ET

from dsapkit.errors import BuildError
from dsapkit.jsonio import read_json
from dsapkit.paths import Paths
from dsapkit.site.crawl import robots_txt, sitemap_files
from dsapkit.site.drift import Drift, check_drift, live_date, require_no_drift, watched_pages
from dsapkit.site.model import load_site

PATHS = Paths.discover()
CRAWL = read_json(PATHS.site / "crawl.json")
RULES = read_json(PATHS.site / "jsonld-rules.json")
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}


class RobotsTest(unittest.TestCase):
    def setUp(self):
        self.site = load_site(PATHS)

    def test_before_launch_nothing_is_crawled_and_no_sitemap_is_named(self):
        text = robots_txt(self.site, CRAWL, indexing=False)
        self.assertIn("Disallow: /\n", text)
        self.assertNotIn("Sitemap:", text)
        self.assertNotIn("Allow: /", text.replace("Disallow: /", ""))

    def test_after_launch_it_follows_the_policy_in_crawl_json(self):
        text = robots_txt(self.site, CRAWL, indexing=True)
        self.assertIn("User-agent: *\nContent-Signal: search=yes, ai-input=yes, ai-train=no\nAllow: /\nDisallow: /api/", text)
        for agent in CRAWL["blockedAgents"]:
            self.assertIn(f"User-agent: {agent}\nDisallow: /\n", text)
        self.assertTrue(text.rstrip().endswith("Sitemap: https://iitjeekota.com/sitemap.xml"))

    def test_search_and_answer_agents_are_not_blocked(self):
        for agent in ("Googlebot", "OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot", "Claude-User", "PerplexityBot"):
            self.assertNotIn(agent, CRAWL["blockedAgents"])


class SitemapTest(unittest.TestCase):
    def setUp(self):
        self.site = load_site(PATHS)

    def files(self, pages, modified=None):
        return sitemap_files(self.site, pages, modified or {})

    def test_only_built_pages_are_listed_with_alternates_that_exist(self):
        files = self.files({("home", "en"), ("home", "hi"), ("faq", "en")})
        urls = {u.find("s:loc", NS).text: u for u in ET.fromstring(files["sitemap-en.xml"]).findall("s:url", NS)}
        self.assertEqual(set(urls), {"https://iitjeekota.com/en/", "https://iitjeekota.com/en/faq/"})
        home = {a.get("hreflang"): a.get("href") for a in urls["https://iitjeekota.com/en/"].findall("x:link", NS)}
        self.assertEqual(home, {"en-IN": "https://iitjeekota.com/en/", "hi-IN": "https://iitjeekota.com/hi/", "x-default": "https://iitjeekota.com/en/"})
        faq = {a.get("hreflang") for a in urls["https://iitjeekota.com/en/faq/"].findall("x:link", NS)}
        self.assertEqual(faq, {"en-IN", "x-default"})  # no Hindi FAQ is built, so none is claimed
        self.assertNotIn("sitemap-mr.xml", files)

    def test_the_index_lists_only_the_sitemaps_that_exist(self):
        files = self.files({("home", "en"), ("home", "hi")})
        locs = [e.find("s:loc", NS).text for e in ET.fromstring(files["sitemap.xml"]).findall("s:sitemap", NS)]
        self.assertEqual(locs, ["https://iitjeekota.com/sitemap-en.xml", "https://iitjeekota.com/sitemap-hi.xml"])

    def test_lastmod_only_where_the_page_says_when_it_changed(self):
        files = self.files({("home", "en"), ("faq", "en")}, {("home", "en"): "2026-11-05", ("faq", "en"): None})
        rows = {u.find("s:loc", NS).text: u.find("s:lastmod", NS) for u in ET.fromstring(files["sitemap-en.xml"]).findall("s:url", NS)}
        self.assertEqual(rows["https://iitjeekota.com/en/"].text, "2026-11-05")
        self.assertIsNone(rows["https://iitjeekota.com/en/faq/"])

    def test_a_time_on_the_day_becomes_a_full_timestamp_and_nothing_else_is_written(self):
        files = self.files({("home", "en")}, {("home", "en"): "2026-11-05T10:30"})
        self.assertIn("<lastmod>2026-11-05T10:30:00+05:30</lastmod>", files["sitemap-en.xml"])
        self.assertNotIn("priority", files["sitemap-en.xml"])
        self.assertNotIn("changefreq", files["sitemap-en.xml"])


class DriftTest(unittest.TestCase):
    def test_every_page_the_rules_cite_is_watched_once(self):
        urls = [w.url for w in watched_pages(RULES)]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(all(u.startswith("https://developers.google.com/") for u in urls))
        self.assertIn("https://developers.google.com/search/docs/appearance/structured-data/article", urls)

    def test_the_date_is_read_from_the_page(self):
        self.assertEqual(live_date("<p>Last updated 2026-09-08 UTC.</p>"), "2026-09-08")
        self.assertIsNone(live_date("<p>nothing</p>"))

    def test_a_newer_page_is_reported_with_where_to_look(self):
        def fetch(url):
            return "Last updated 2027-01-01 UTC." if url.endswith("/article") else next(
                f"Last updated {w.recorded} UTC." for w in watched_pages(RULES) if w.url == url)
        drifts = check_drift(RULES, fetch)
        self.assertEqual([d.page.url for d in drifts if d.changed], ["https://developers.google.com/search/docs/appearance/structured-data/article"])
        with self.assertRaises(BuildError) as raised:
            require_no_drift(drifts)
        self.assertIn("BlogPosting", str(raised.exception))
        self.assertIn("2027-01-01", str(raised.exception))

    def test_a_page_that_stops_showing_a_date_counts_as_changed(self):
        page = watched_pages(RULES)[0]
        self.assertTrue(Drift(page, None).changed)
        self.assertFalse(Drift(page, page.recorded).changed)


if __name__ == "__main__":
    unittest.main()
