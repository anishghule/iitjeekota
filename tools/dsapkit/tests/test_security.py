import copy
import unittest
from dataclasses import replace
from datetime import date

from dsapkit.errors import BuildError
from dsapkit.jsonio import read_json
from dsapkit.paths import Paths
from dsapkit.site.model import load_site
from dsapkit.site.security import (check_security, check_security_txt, content_security_policy, headers_file, permissions_policy,
                                   redirects_file, response_headers, security_age, security_txt)

PATHS = Paths.discover()
SECURITY = read_json(PATHS.site / "security.json")


def weakened(path: str, value):
    """A copy of the policy with one setting changed, e.g. weakened("csp.script-src", ["'unsafe-inline'"])."""
    data = copy.deepcopy(SECURITY)
    *parents, last = path.split(".")
    node = data
    for key in parents:
        node = node[key]
    node[last] = value
    return data


class PolicyTest(unittest.TestCase):
    def test_the_project_policy_is_strict(self):
        self.assertEqual(check_security(SECURITY), [])

    def test_every_source_is_this_site_and_nothing_is_open(self):
        csp = content_security_policy(SECURITY)
        for needed in ("default-src 'none'", "script-src 'self'", "style-src 'self'", "frame-ancestors 'none'", "object-src 'none'",
                       "base-uri 'none'", "form-action 'self'", "media-src 'self'", "upgrade-insecure-requests"):
            self.assertIn(needed, csp)
        for never in ("unsafe-inline", "unsafe-eval", "*", "http:", "data:", "blob:"):
            self.assertNotIn(never, csp)

    def test_the_api_origin_is_the_only_extra_place_the_page_may_talk_to(self):
        csp = content_security_policy(weakened("apiOrigin", "https://api.iitjeekota.com"))
        self.assertIn("connect-src 'self' https://api.iitjeekota.com", csp)
        self.assertIn("script-src 'self';", csp)

    def test_a_weaker_policy_is_refused(self):
        cases = {
            "csp.script-src": [["'self'", "'unsafe-inline'"], ["'self'", "https://cdn.example.com/*"], ["'self'", "https:"], ["'self'", "http://x.in"],
                               ["'self'", "'unsafe-eval'"], ["'self'", "data:"], ["'none'", "'self'"], ["*"]],
            "csp.frame-ancestors": [["'self'"]],
            "csp.object-src": [["'self'"]],
            "csp.default-src": [["*"], ["https://x.in"]],
        }
        for path, values in cases.items():
            for value in values:
                self.assertTrue(check_security(weakened(path, value)), f"{path} = {value} should be refused")

    def test_missing_directives_and_headers_are_refused(self):
        data = copy.deepcopy(SECURITY)
        del data["csp"]["base-uri"]
        self.assertIn("csp needs base-uri", check_security(data))
        self.assertTrue(check_security(weakened("headers.X-Content-Type-Options", "sniff")))
        data = copy.deepcopy(SECURITY)
        del data["headers"]["Cross-Origin-Opener-Policy"]
        self.assertIn("headers need Cross-Origin-Opener-Policy", check_security(data))
        self.assertTrue(check_security(weakened("permissionsPolicy", ["camera", "microphone"])))

    def test_an_api_origin_must_be_exact_https(self):
        self.assertTrue(check_security(weakened("apiOrigin", "http://api.iitjeekota.com")))
        self.assertTrue(check_security(weakened("apiOrigin", "https://*.iitjeekota.com")))


class HeadersFileTest(unittest.TestCase):
    def test_the_file_follows_cloudflare_pages_format_and_limits(self):
        text = headers_file(SECURITY)
        lines = text.splitlines()
        rules = [line for line in lines if line and not line.startswith((" ", "#"))]
        self.assertEqual(rules, ["/*", "/.well-known/security.txt", "https://:project.pages.dev/*", "https://:version.:project.pages.dev/*"])
        self.assertLessEqual(len(rules), 100)
        self.assertTrue(all(len(line) <= 2000 for line in lines))
        self.assertTrue(all(line.startswith("  ") for line in lines if line and not line.startswith("#") and line not in rules))
        self.assertIn("  X-Robots-Tag: noindex", lines)

    def test_every_response_carries_the_set(self):
        headers = response_headers(SECURITY)
        for name in ("Content-Security-Policy", "Referrer-Policy", "X-Content-Type-Options", "Cross-Origin-Opener-Policy",
                     "Cross-Origin-Resource-Policy", "X-Frame-Options", "Permissions-Policy"):
            self.assertIn(name, headers)
        self.assertIn("camera=()", permissions_policy(SECURITY))
        self.assertNotIn("Strict-Transport-Security", headers)  # off until launch

    def test_the_root_redirect_is_a_real_301(self):
        self.assertIn("\n/ /en/ 301\n", redirects_file(load_site(PATHS)))


class HstsTest(unittest.TestCase):
    def test_it_is_off_until_launch_then_ramps_up(self):
        on = weakened("hsts.enabled", True)
        self.assertEqual(response_headers(on)["Strict-Transport-Security"], "max-age=300; includeSubDomains")
        final = copy.deepcopy(on)
        final["hsts"].update({"maxAge": 63072000, "preload": True})
        self.assertEqual(response_headers(final)["Strict-Transport-Security"], "max-age=63072000; includeSubDomains; preload")
        self.assertEqual(check_security(final), [])

    def test_preload_needs_a_year_and_subdomains(self):
        for change in ({"preload": True}, {"enabled": True, "preload": True, "maxAge": 300},
                       {"enabled": True, "preload": True, "maxAge": 63072000, "includeSubDomains": False}):
            data = copy.deepcopy(SECURITY)
            data["hsts"].update(change)
            self.assertTrue(check_security(data), change)


class SecurityTxtTest(unittest.TestCase):
    def test_it_names_the_confirmed_contact_and_when_it_expires(self):
        text = security_txt(load_site(PATHS), SECURITY)
        self.assertIn("Contact: mailto:ghulesir@dsapghuletutorials.com\n", text)
        self.assertIn("Expires: 2027-10-30T00:00:00+05:30\n", text)
        self.assertIn("Canonical: https://iitjeekota.com/.well-known/security.txt\n", text)
        self.assertIn("Preferred-Languages: en, hi, mr\n", text)

    def test_without_a_confirmed_contact_the_file_is_not_written(self):
        site = load_site(PATHS)
        site.facts["contact.email"] = replace(site.facts["contact.email"], status="pending", value=None)
        with self.assertRaises(BuildError):
            security_txt(site, SECURITY)

    def test_the_expiry_must_be_ahead_but_under_a_year(self):
        self.assertEqual(check_security_txt(SECURITY, date(2026, 11, 1)), [])
        self.assertTrue(check_security_txt(SECURITY, date(2027, 10, 30)))            # expired
        self.assertTrue(check_security_txt(SECURITY, date(2026, 10, 1)))             # more than a year away
        for bad in ("2027-10-30", "30 October 2027", "2027-10-30T00:00:00"):
            self.assertTrue(check_security_txt(weakened("securityTxt.expires", bad), date(2026, 11, 1)), bad)

    def test_it_is_served_as_plain_utf8_text(self):
        self.assertIn("/.well-known/security.txt\n  Content-Type: text/plain; charset=utf-8", headers_file(SECURITY))


class AgeTest(unittest.TestCase):
    def test_old_guidance_must_be_read_again(self):
        self.assertEqual(security_age({"checked": "2026-11-01", "staleAfterDays": 90}, date(2026, 12, 1)), 30)
        with self.assertRaises(BuildError):
            security_age({"checked": "2026-11-01", "staleAfterDays": 90}, date(2027, 3, 1))


if __name__ == "__main__":
    unittest.main()
