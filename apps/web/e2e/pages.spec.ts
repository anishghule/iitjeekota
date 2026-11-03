import { expect, test, type Page } from "@playwright/test";

// The built pages that search and "near me" visits land on (make web), read as a visitor reads them.

async function open(page: Page, path: string): Promise<string[]> {
  const errors: string[] = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(path);
  return errors;
}

async function jsonld(page: Page): Promise<{ "@graph": { "@type": string | string[]; [key: string]: unknown }[] }> {
  const text = await page.locator('script[type="application/ld+json"]').first().textContent();
  return JSON.parse(text ?? "{}");
}

const types = (graph: { "@type": string | string[] }[]) => graph.flatMap((n) => (Array.isArray(n["@type"]) ? n["@type"] : [n["@type"]]));

test("an address that does not exist gets the 404 page with status 404, in every language, and is never indexable", async ({ page }) => {
  for (const path of ["/nothing-here/", "/en/nothing-here/", "/hi/nothing-here/", "/mr/nothing-here/"]) {
    const response = await page.goto(path);
    expect(response?.status(), path).toBe(404);
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.locator(".not-found__block")).toHaveCount(3);
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
    await expect(page.locator('link[rel="canonical"]')).toHaveCount(0);
    // The same language menu as every page; with no version of this page, each language leads to its home page.
    const menu = page.locator("[data-lang-menu]").first();
    for (const lang of ["en", "hi", "mr"]) await expect(menu.locator(`a[hreflang][lang="${lang}"][href="/${lang}/"]`)).toHaveCount(1);
    await expect(menu.locator('a[aria-current="page"]')).toHaveCount(0);
    for (const lang of ["en", "hi", "mr"]) {
      const block = page.locator(`.not-found__block[lang="${lang}"]`);
      await expect(block.locator(`a.button[href="/${lang}/"]`)).toHaveCount(1);
      await expect(block.locator(`nav a[href="/${lang}/programmes/"], nav a[href="/${lang}/fees-and-batches/"], nav a[href="/${lang}/contact/"]`)).toHaveCount(3);
    }
  }
});

test("/programmes/ links every programme by its own heading and compares them in a table", async ({ page }) => {
  const errors = await open(page, "/en/programmes/");
  await expect(page.locator("h1")).toHaveCount(1);
  for (const path of ["/en/class-11-jee/", "/en/class-12-jee/", "/en/foundation-class-9-10/", "/en/fees-and-batches/", "/en/test-series/"]) {
    await expect(page.locator(`#spokes a[href="${path}"]`)).toHaveCount(1);
  }
  await expect(page.locator("#compare table tbody tr")).toHaveCount(3);
  const graph = (await jsonld(page))["@graph"];
  expect(types(graph)).toEqual(expect.arrayContaining(["CollectionPage", "ItemList", "BreadcrumbList"]));
  const list = graph.find((n) => n["@type"] === "ItemList") as { itemListElement: unknown[] };
  expect(list.itemListElement).toHaveLength(3);
  expect(errors).toEqual([]);
});

test("a centre page has the address, phone, hours and directions the structured data states", async ({ page }) => {
  const errors = await open(page, "/en/centres/sangvi-head-office/");
  const card = page.locator(".centre-card");
  await expect(card).toContainText("Krishna Nagar Rd Number 2");
  await expect(card).toContainText("+91 22 6971 9828");
  await expect(card).toContainText("Monday to Friday");
  await expect(card).toContainText("Closed Sunday");
  await expect(card.locator('a[href^="https://www.google.com/maps/dir/"]')).toHaveCount(1);
  const business = (await jsonld(page))["@graph"].find((n) => types([n]).includes("LocalBusiness")) as { telephone: string; openingHoursSpecification: { opens: string }[] };
  expect(business.telephone).toBe("+91 22 6971 9828");
  expect(business.openingHoursSpecification[0]?.opens).toBe("07:00:00");
  await expect(page.locator("#inside video")).toHaveCount(1); // the film from this centre
  expect(errors).toEqual([]);
});

test("the fees page states the scholarship, the batch table and asks for an enquiry, with no amount made up", async ({ page }) => {
  const errors = await open(page, "/en/fees-and-batches/");
  await expect(page.locator("#fees")).toContainText("Up to 30% scholarship");
  await expect(page.locator('#fees a[href="#enquiry"]')).toHaveCount(1);
  await expect(page.locator("#batches table")).toContainText("JEE 2029");
  await expect(page.locator("#batches table")).toContainText("April 2027");
  await expect(page.locator("#batches table")).toContainText("Open");
  await expect(page.locator("#questions")).toContainText("foundation period from April");
  expect(errors).toEqual([]);
});

test("the syllabus page is the full table, with its own heading and every chapter", async ({ page }) => {
  const errors = await open(page, "/en/jee-syllabus/");
  await expect(page.locator("h1")).toContainText("JEE Main syllabus");
  await expect(page.locator("#table [data-syllabus], #table[data-syllabus]").first()).toBeVisible();
  expect(await page.locator("#table details").count()).toBeGreaterThan(70);
  expect(errors).toEqual([]);
});

test("an area page tells how to get to each centre and links the pages around it", async ({ page }) => {
  const errors = await open(page, "/en/iit-jee-coaching-aundh/");
  const trips = page.locator(".commute__trip");
  await expect(trips).toHaveCount(2);
  await expect(trips.first()).toContainText("Nearest centre");
  await expect(trips.first()).toContainText("New Sangvi");
  await expect(trips.first()).toContainText("on empty roads");
  await expect(trips.nth(1)).toContainText("12 to 16 minutes");
  await expect(page.locator('.related a[href="/en/iit-jee-coaching-pune/"]')).toHaveCount(1);
  const graph = (await jsonld(page))["@graph"];
  expect(types(graph)).not.toContain("LocalBusiness"); // no centre in Aundh
  expect(graph.find((n) => types([n]).includes("WebPage"))?.about).toEqual({ "@id": "https://iitjeekota.com/en/centres/sangvi-head-office/#centre" });
  expect(errors).toEqual([]);
});

test("the contact page draws the map itself and embeds nothing from another site", async ({ page }) => {
  const errors = await open(page, "/en/contact/");
  await expect(page.locator("iframe")).toHaveCount(0);
  await expect(page.locator(".area-map__figure svg")).toHaveCount(1);
  await expect(page.locator('a[href^="mailto:"]')).toHaveCount(1);
  await expect(page.locator(".centre-card")).toHaveCount(2);
  await expect(page.locator("#enquiry form")).toHaveCount(1);
  expect(await page.evaluate(() => performance.getEntriesByType("resource").map((e) => new URL(e.name).origin).filter((o) => o !== location.origin))).toEqual([]);
  expect(errors).toEqual([]);
});

test("a guide has its body, its author and its dates in the page and in its structured data", async ({ page }) => {
  const errors = await open(page, "/en/blogs/kota-or-pune/");
  await expect(page.locator("h1")).toHaveCount(1);
  await expect(page.locator("article.guide h2").first()).toBeVisible();
  await expect(page.locator(".page-head__meta")).toContainText("By Prof. Ghule");
  await expect(page.locator(".page-head__meta")).toContainText("Last updated 2 November 2026");
  const post = (await jsonld(page))["@graph"].find((n) => n["@type"] === "BlogPosting") as { datePublished: string; author: { name: string }[] };
  expect(post.datePublished).toMatch(/^2026-11-02T\d\d:\d\d:\d\d\+05:30$/);
  expect(post.author[0]?.name).toBe("Prof. Ghule");
  await expect(page.locator("article.guide")).not.toContainText("**");
  expect(errors).toEqual([]);
});

test("the blogs page lists every written guide", async ({ page }) => {
  await open(page, "/en/blogs/");
  expect(await page.locator("#guides .spokes__list li").count()).toBeGreaterThanOrEqual(5);
});

test("the navbar leaves out Pimpri-Chinchwad and the footer lists each area hub with its areas", async ({ page }) => {
  await open(page, "/en/");
  await expect(page.locator('header a[href="/en/iit-jee-coaching-pimpri-chinchwad/"]')).toHaveCount(0);
  const hubs = page.locator("footer .footer-hub a");
  await expect(hubs).toHaveText(["IIT JEE Coaching Pune", "IIT JEE Coaching Pimpri-Chinchwad"]);
  await expect(page.locator('footer a[href="/en/iit-jee-coaching-pimpri-chinchwad/"]')).toHaveCount(1);
  await expect(page.locator('footer .footer-areas a[href="/en/iit-jee-coaching-aundh/"]')).toHaveCount(1);
});
