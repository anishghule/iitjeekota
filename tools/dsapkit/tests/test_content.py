import unittest
from dataclasses import replace
from pathlib import Path

from dsapkit.content.check import check_content, similarity
from dsapkit.content.model import Page, Paragraph, Post, Question, Section, load_content
from dsapkit.content.syllabus import check_syllabus, load_syllabus
from dsapkit.content.text import resolve
from dsapkit.paths import Paths
from dsapkit.site.model import Fact, load_site

PATHS = Paths.discover()


def project():
    site = load_site(PATHS)
    return load_content(PATHS, site.locales), site


def prose(sid: str, *texts: str, heading: str = "A heading") -> Section:
    return Section(sid, None, heading, tuple(Paragraph(t) for t in texts), (), ())


def area_page(route: str, words: str) -> Page:
    """An area page in the right shape: words in the local section, and filler that names the area elsewhere."""
    name = route.removeprefix("area-").replace("-", " ")
    faq = Section("questions", None, "Questions", (), (),
                  tuple(Question(f"{name} question {i}?", Paragraph(f"{name} answer {i}.")) for i in range(3)))
    sections = (prose("getting-there", f"From {name}, take the road."), prose("local", words, words),
                Section("kota-system", None, None, (), (), (), block="kota-system"), prose("programmes", f"{name} evenings."),
                faq, Section("enquiry", None, None, (), (), (), block="enquiry"))
    return Page(route, "en", "draft", f"IIT JEE coaching in {name}", "x" * 100, f"IIT JEE coaching in {name}",
                (Paragraph(f"About {name}."),), sections, Path(f"{route}.json"))


def messages(findings, severity=None):
    return [f.message for f in findings if severity is None or f.severity == severity]


class TextTest(unittest.TestCase):
    def test_confirmed_fact_is_filled_and_structured_field_read(self):
        _, site = project()
        r = resolve("Classes start at {{fact:batch.timings#start}}.", site)
        self.assertEqual(r.text, "Classes start at 3:00 PM.")

    def test_pending_fact_holds_the_text(self):
        _, site = project()
        site.facts["batch.size"] = Fact("batch.size", "pending", None, None, None)
        r = resolve("At most {{fact:batch.size}} students.", site)
        self.assertIsNone(r.text)
        self.assertEqual(r.pending, ("batch.size",))
        self.assertEqual(resolve("Plain words.", site, requires=("batch.size",)).pending, ("batch.size",))

    def test_words_in_a_fact_need_the_page_language(self):
        _, site = project()
        site.facts["batch.days"] = Fact("batch.days", "confirmed", "Monday to Saturday", "test", None, {"hi": "सोमवार से शनिवार"})
        self.assertEqual(resolve("{{fact:batch.days}}", site, locale="hi").text, "सोमवार से शनिवार")
        self.assertEqual(resolve("{{fact:batch.days}}", site, locale="mr").pending, ("batch.days in mr",))
        self.assertEqual(resolve("{{fact:batch.days}}", site).text, "Monday to Saturday")
        self.assertEqual(resolve("{{fact:contact.phone}}", site, locale="mr").text, site.facts["contact.phone"].value)

    def test_unknown_and_malformed_references(self):
        _, site = project()
        self.assertTrue(resolve("{{fact:no.such}}", site).unknown)
        self.assertTrue(resolve("{{fact:batch.timings}}", site).unknown)  # structured: needs a field
        self.assertTrue(resolve("[see](page:no-such-page)", site).unknown)
        self.assertTrue(resolve("[see](/en/about/)", site).unknown)  # URLs are not written in copy
        self.assertTrue(resolve("{{origin}}", site).unknown)

    def test_commute_distance_comes_from_the_area_data(self):
        _, site = project()
        km = next(r["km"] for r in site.areas["aundh"]["commute"]["routes"] if r["centre"] == site.areas["aundh"]["nearestCentre"])
        self.assertEqual(resolve("About {{commute:aundh#km}} km.", site).text, f"About {km} km.")
        self.assertTrue(resolve("{{commute:wakad#km}}", site).unknown)  # the centre is in Wakad
        self.assertTrue(resolve("{{commute:aundh#minutes}}", site).unknown)
        site.areas["aundh"]["commute"] = {**site.areas["aundh"]["commute"], "status": "placeholder"}
        self.assertEqual(resolve("{{commute:aundh#km}} km", site).pending, ("commute.aundh",))

    def test_syllabus_values(self):
        content, site = project()
        year = content.syllabus.sources["main"]["year"]
        self.assertEqual(resolve("JEE Main {{syllabus:main#year}}", site, syllabus=content.syllabus).text, f"JEE Main {year}")
        self.assertEqual(resolve("{{syllabus:all#chapters}}", site, syllabus=content.syllabus).text, str(len(content.syllabus.chapters)))
        self.assertTrue(resolve("{{syllabus:biology#chapters}}", site, syllabus=content.syllabus).unknown)
        self.assertTrue(resolve("{{syllabus:main#year}}", site).unknown)

    def test_link_to_a_page_not_live_keeps_its_anchor(self):
        _, site = project()
        r = resolve("Read [about Kota](page:powered-by-kota).", site)
        self.assertEqual(r.text, "Read about Kota.")
        self.assertEqual(r.unlinked, ("powered-by-kota",))
        self.assertEqual(resolve("[us](page:about)", site).links, ("about",))


class StructureTest(unittest.TestCase):
    def test_project_content_has_no_errors(self):
        content, site = project()
        self.assertEqual(messages(check_content(content, site), "error"), [])

    def test_missing_section_and_wrong_counts_are_caught(self):
        content, site = project()
        page = area_page("area-aundh", "Aundh words.")
        page = replace(page, status="ready", sections=page.sections[:1] + (prose("local", "Only one."),) + page.sections[2:-1])
        content.pages = {("area-aundh", "en"): page}
        found = messages(check_content(content, site), "error")
        self.assertTrue(any("should be" in m and "enquiry" in m for m in found))
        self.assertTrue(any("section local: 1 paragraphs" in m for m in found))

    def test_draft_problems_are_warnings_not_errors(self):
        content, site = project()
        page = area_page("area-aundh", "Aundh words.")
        content.pages = {("area-aundh", "en"): replace(page, sections=page.sections[:-1])}
        found = check_content(content, site)
        self.assertEqual(messages(found, "error"), [])
        self.assertTrue(messages(found, "warning"))

    def test_meta_lengths_and_keyword(self):
        content, site = project()
        page = area_page("area-aundh", "Aundh words.")
        content.pages = {("area-aundh", "en"): replace(page, status="ready", title="A" * 70, h1="Classes near you")}
        found = messages(check_content(content, site), "error")
        self.assertTrue(any("meta.title is 70 characters" in m for m in found))
        self.assertTrue(any("primary keyword" in m for m in found))

    def test_a_navbar_page_title_starts_with_the_navbar_word_in_its_language(self):
        content, site = project()
        for locale, label in (("en", "Fees and Batches"), ("hi", "फीस और बैच"), ("mr", "फी आणि बॅच")):
            page = content.pages[("fees-and-batches", locale)]
            self.assertTrue(page.title.startswith(label), page.title)
            content.pages[("fees-and-batches", locale)] = replace(page, title="Fees in Pune | D-SAP")
        found = messages(check_content(content, site), "error")
        self.assertTrue(any("navbar word 'Fees and Batches'" in m for m in found))
        self.assertTrue(any("navbar word 'फीस और बैच'" in m for m in found))

    def test_page_for_a_later_phase_is_refused(self):
        content, site = project()
        content.pages = {("privacy-policy", "en"): replace(area_page("area-aundh", "x"), route="privacy-policy")}
        self.assertTrue(any("Phase 1" in m for m in messages(check_content(content, site), "error")))

    def test_gated_section_and_fully_held_section_are_hidden(self):
        content, site = project()
        site.facts["faculty.profiles"] = Fact("faculty.profiles", "pending", None, None, None)
        for fact_id in ("method.test-analytics", "method.ptm"):
            site.facts[fact_id] = Fact(fact_id, "pending", None, None, None)
        held = messages(check_content(content, site), "held")
        self.assertIn("section faculty is hidden until faculty.profiles", held)
        self.assertIn("section report is hidden until method.ptm, method.test-analytics", held)
        site.facts["method.ptm"] = Fact("method.ptm", "confirmed", "yes", "test", None)
        held = messages(check_content(content, site), "held")
        self.assertFalse(any("section report is hidden" in m for m in held))
        self.assertIn("report.body[0]: waits for method.test-analytics", held)


class SimilarityTest(unittest.TestCase):
    def test_copied_area_pages_are_flagged(self):
        content, site = project()
        text = "Students here study in schools on the main road and travel by bus after school every evening."
        content.pages = {("area-aundh", "en"): area_page("area-aundh", text),
                         ("area-baner", "en"): area_page("area-baner", text)}
        score, _, _ = similarity(content, site)[0]
        self.assertGreater(score, content.similarity["max"])
        self.assertTrue(any("of their wording is shared" in m for m in messages(check_content(content, site), "warning")))

    def test_shared_blocks_do_not_count(self):
        content, site = project()
        content.pages = {("area-aundh", "en"): area_page("area-aundh", "Aundh has its own schools and roads to describe here."),
                         ("area-baner", "en"): area_page("area-baner", "Baner sits along the highway with a different set of lanes.")}
        score, _, _ = similarity(content, site)[0]
        self.assertLess(score, content.similarity["max"])


class PostTest(unittest.TestCase):
    def post(self, content, body: str, **changes) -> Post:
        base = content.posts[("post-kota-or-pune", "en")]
        return replace(base, body=body, **changes)

    def test_project_posts_load_with_front_matter(self):
        content, _ = project()
        post = content.posts[("post-kota-or-pune", "en")]
        self.assertEqual(post.author, "org.founder")
        self.assertFalse(post.body.startswith("---"))

    def test_post_rules(self):
        content, site = project()
        long_intro = " ".join(["word"] * 80)
        content.posts = {("post-kota-or-pune", "en"): self.post(content, f"# A second title\n\n{long_intro}\n\n## Next", status="ready")}
        found = messages(check_content(content, site), "error")
        self.assertTrue(any("the H1 is the title in blog.json" in m for m in found))
        self.assertTrue(any("opening paragraph is 80 words" in m for m in found))
        self.assertTrue(any("a guide needs at least" in m for m in found))
        self.assertTrue(any("does not link to home" in m for m in found))

    def test_planned_post_with_copy_is_an_error(self):
        content, site = project()
        rid = "post-kota-or-pune"
        site.routes[rid] = replace(site.routes[rid], planned=True)
        self.assertTrue(any("still says planned" in m for m in messages(check_content(content, site), "error")))


class SyllabusTest(unittest.TestCase):
    def test_project_syllabus_covers_every_official_unit(self):
        self.assertEqual(check_syllabus(load_syllabus(PATHS)), [])

    def test_uncovered_unit_and_wrong_references_are_caught(self):
        syllabus = load_syllabus(PATHS)
        trig = next(c for c in syllabus.chapters if c.id == "m-trigonometry")
        others = tuple(c for c in syllabus.chapters if c.id != "m-trigonometry")
        broken = replace(syllabus, chapters=others + (replace(trig, main=99, advanced=("Astronomy",)),))
        problems = check_syllabus(broken)
        self.assertTrue(any("unit 14 (Trigonometry) has no chapter" in p for p in problems))
        self.assertTrue(any("heading 'Trigonometry' has no chapter" in p for p in problems))
        self.assertTrue(any("unit 99 is not one of" in p for p in problems))
        self.assertTrue(any("'Astronomy' is not a JEE Advanced" in p for p in problems))

    def test_chapter_codes_number_each_subject_within_its_first_class(self):
        syllabus = load_syllabus(PATHS)
        codes = [syllabus.code(c) for c in syllabus.chapters]
        self.assertEqual(len(set(codes)), len(codes))
        self.assertEqual(syllabus.code(syllabus.chapters[0]), "11-P-01")
        both = next(c for c in syllabus.chapters if c.classes == (11, 12))
        self.assertTrue(syllabus.code(both).startswith("11-"))
        clash = replace(syllabus, subject_codes={**syllabus.subject_codes, "maths": "P"})
        self.assertTrue(any("single capital letter" in p for p in check_syllabus(clash)))

    def test_translations_name_every_chapter(self):
        syllabus = load_syllabus(PATHS)
        self.assertTrue(all({"en", "hi", "mr"} <= set(c.names) for c in syllabus.chapters))
        hi = dict(syllabus.translations["hi"], chapters={k: v for k, v in syllabus.translations["hi"]["chapters"].items() if k != "m-3d"})
        hi["chapters"]["m-astronomy"] = "खगोल"
        problems = check_syllabus(replace(syllabus, translations={"hi": hi}))
        self.assertIn("syllabus/hi.json: no chapter name for m-3d", problems)
        self.assertIn("syllabus/hi.json: m-astronomy is not a syllabus chapter", problems)

    def test_advanced_only_chapters(self):
        syllabus = load_syllabus(PATHS)
        self.assertIn("c-solid-state", {c.id for c in syllabus.chapters if c.advanced_only})
        self.assertFalse(next(c for c in syllabus.chapters if c.id == "p-semiconductors").advanced)


if __name__ == "__main__":
    unittest.main()
