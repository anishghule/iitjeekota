import { describe, expect, it } from "vitest";
import { locales, strings } from "../src/i18n/index.ts";
import { NOT_FOUND_ROUTE, notFoundHead } from "../src/lib/not-found.ts";

describe("notFoundHead", () => {
  const head = notFoundHead(strings("en").notFound, "D-SAP Ghule Tutorials");

  it("names the brand in the title and description", () => {
    expect(head.meta.title).toBe("Page not found | D-SAP Ghule Tutorials");
    expect(head.meta.description).toContain("D-SAP Ghule Tutorials");
  });

  it("has no address of its own, no language versions and no structured data", () => {
    expect(head.meta.canonical).toBeUndefined();
    expect(head.meta.alternates).toBeUndefined();
    expect(head.jsonld).toEqual([]);
  });

  it("is no route of the site, so no menu entry is marked current", () => {
    expect(head.route).toBe(NOT_FOUND_ROUTE);
  });
});

describe("not-found copy", () => {
  it.each(locales)("%s has a heading, text, a way home and a title that fits a result line", (locale) => {
    const t = strings(locale).notFound;
    for (const text of [t.heading, t.body, t.home, t.pages]) expect(text.trim()).not.toBe("");
    expect(t.title).toContain("{brand}");
    expect(notFoundHead(t, "D-SAP").meta.title.length).toBeLessThanOrEqual(60);
  });
});
