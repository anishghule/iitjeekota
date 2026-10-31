import { describe, expect, it } from "vitest";
import { compare } from "../src/islands/cost-calc.ts";
import { normalisePhone, validate, whatsappLink } from "../src/islands/enquiry.ts";
import { paletteState, score } from "../src/islands/live-test.ts";
import { stepAt } from "../src/islands/steps.ts";
import { matches } from "../src/islands/syllabus.ts";
import { fill, minutesAndSeconds, templateParts } from "../src/lib/format.ts";

describe("the sample test", () => {
  const marking = { right: 4, wrong: -1, blank: 0 };

  it("scores like JEE Main", () => {
    expect(score([1, 0, null], [1, 2, 0], marking)).toEqual({ right: 1, wrong: 1, left: 1, marks: 3, max: 12 });
    expect(score([null, null, null], [1, 2, 0], marking).marks).toBe(0);
    expect(score([0, 0, 1], [1, 2, 0], marking).marks).toBe(-3);
  });

  it("colours the palette as the JEE screen does", () => {
    expect(paletteState(false, false, false)).toBe("not-visited");
    expect(paletteState(true, false, false)).toBe("not-answered");
    expect(paletteState(true, true, false)).toBe("answered");
    expect(paletteState(true, false, true)).toBe("marked");
    expect(paletteState(true, true, true)).toBe("marked-answered");
  });

  it("shows the time as minutes and seconds", () => {
    expect(minutesAndSeconds(360)).toBe("06:00");
    expect(minutesAndSeconds(59)).toBe("00:59");
    expect(minutesAndSeconds(-3)).toBe("00:00");
  });
});

describe("scroll steps", () => {
  it("settles on the nearest of n stops, like the Kota prism", () => {
    expect(stepAt(0, 5)).toBe(0);
    expect(stepAt(0.12, 5)).toBe(0);
    expect(stepAt(0.13, 5)).toBe(1);
    expect(stepAt(1, 5)).toBe(4);
    expect(stepAt(1.4, 5)).toBe(4);
  });
});

describe("the syllabus filters", () => {
  type Tile = Parameters<typeof matches>[0];
  const mainOnly: Tile = { subject: "physics", main: 18, advanced: [] };
  const both: Tile = { subject: "physics", main: 5, advanced: ["Mechanics"] };
  const advancedOnly: Tile = { subject: "chemistry", main: null, advanced: ["Solid state"] };

  it("matches by subject and by exam", () => {
    expect(matches(mainOnly, { subject: "all", exam: "all" })).toBe(true);
    expect(matches(mainOnly, { subject: "chemistry", exam: "all" })).toBe(false);
    expect(matches(mainOnly, { subject: "all", exam: "advanced" })).toBe(false);
    expect(matches(both, { subject: "physics", exam: "advanced" })).toBe(true);
    expect(matches(advancedOnly, { subject: "all", exam: "main" })).toBe(false);
  });
});

describe("the cost sum", () => {
  it("compares only when both sides have amounts", () => {
    expect(compare(100, 0, { kota: true, pune: false })).toEqual({ kind: "empty" });
    expect(compare(100, 100, { kota: true, pune: true })).toEqual({ kind: "same" });
    expect(compare(300, 100, { kota: true, pune: true })).toEqual({ kind: "kotaMore", amount: 200 });
    expect(compare(100, 250, { kota: true, pune: true })).toEqual({ kind: "puneMore", amount: 150 });
  });
});

describe("the enquiry form", () => {
  it("accepts Indian mobile numbers in the usual forms", () => {
    expect(normalisePhone("98765 43210")).toBe("9876543210");
    expect(normalisePhone("+91 98765-43210")).toBe("9876543210");
    expect(normalisePhone("098765 43210")).toBe("9876543210");
    expect(normalisePhone("12345 67890")).toBeNull();
    expect(normalisePhone("98765")).toBeNull();
  });

  it("names each missing or wrong field", () => {
    expect(validate({ name: "", class: "", area: "", phone: "", consent: false })).toEqual({
      name: "required", class: "required", area: "required", phone: "required", consent: "needConsent",
    });
    expect(validate({ name: "Asha", class: "Class 10", area: "Aundh", phone: "123", consent: true })).toEqual({ phone: "badPhone" });
    expect(validate({ name: "Asha", class: "Class 10", area: "Aundh", phone: "9876543210", consent: true })).toEqual({});
  });

  it("builds the WhatsApp link from the pattern in site data", () => {
    expect(whatsappLink("https://wa.me/{digits}?text={text}", "912269719828", "Student: Asha\nArea: Aundh"))
      .toBe("https://wa.me/912269719828?text=Student%3A%20Asha%0AArea%3A%20Aundh");
  });
});

describe("UI string templates", () => {
  it("fills placeholders and leaves unknown ones", () => {
    expect(fill("{a} and {b}", { a: 1, b: "two" })).toBe("1 and two");
    expect(fill("{a} and {c}", { a: 1 })).toBe("1 and {c}");
  });

  it("splits at placeholders in the language's own order", () => {
    expect(templateParts("{max} में से {marks}")).toEqual([{ key: "max" }, { text: " में से " }, { key: "marks" }]);
  });
});
