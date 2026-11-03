import { describe, expect, it } from "vitest";
import { compare } from "../src/islands/cost-calc.ts";
import { normalisePhone, validate, whatsappLink } from "../src/islands/enquiry.ts";
import { edges, stepTarget } from "../src/islands/gallery.ts";
import { outcome, paletteState, score } from "../src/islands/live-test.ts";
import { progressForStep, scrollForStep, stepAt } from "../src/islands/steps.ts";
import { matches, type RowFacts } from "../src/islands/syllabus.ts";
import { currentStep, railFill } from "../src/islands/timeline.ts";
import { fill, minutesAndSeconds, templateParts } from "../src/lib/format.ts";
import { axisTop, barBox, chapterAccuracy, difficultyMatrix, tally, type MapQuestion } from "../src/lib/test-map.ts";

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

  it("tells a right answer, a wrong one and a question left", () => {
    expect(outcome(2, 2)).toBe("right");
    expect(outcome(1, 2)).toBe("wrong");
    expect(outcome(null, 2)).toBe("left");
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

describe("jumping to a step", () => {
  it("is the inverse of stepAt, with and without a held-back start", () => {
    for (const from of [0, 0.3]) {
      for (let i = 0; i < 5; i++) expect(stepAt((progressForStep(i, 5, from) - from) / (1 - from), 5)).toBe(i);
    }
    expect(progressForStep(0, 5, 0.3)).toBeCloseTo(0.3);
    expect(progressForStep(4, 5, 0.3)).toBe(1);
  });

  it("scrolls to the point in the section where the step holds", () => {
    expect(scrollForStep(0, 5, 0.3, 1000, 3000, 800, 0)).toBeCloseTo(1000 + 0.3 * 2200);
    expect(scrollForStep(4, 5, 0.3, 1000, 3000, 800, 0)).toBe(1000 + 2200);
    expect(scrollForStep(4, 5, 0.3, 1000, 3000, 800, 200)).toBe(1000 + 200 + 2000);
  });
});

describe("the syllabus filters", () => {
  const mainOnly: RowFacts = { subject: "physics", classes: [12], inMain: true, inAdvanced: false };
  const both: RowFacts = { subject: "physics", classes: [11, 12], inMain: true, inAdvanced: true };
  const advancedOnly: RowFacts = { subject: "chemistry", classes: [12], inMain: false, inAdvanced: true };
  const all = { class: "all", exam: "all" };

  it("shows one subject, and narrows it by class and by exam", () => {
    expect(matches(mainOnly, { subject: "physics", ...all })).toBe(true);
    expect(matches(mainOnly, { subject: "chemistry", ...all })).toBe(false);
    expect(matches(mainOnly, { subject: "physics", class: "all", exam: "advanced" })).toBe(false);
    expect(matches(advancedOnly, { subject: "chemistry", class: "all", exam: "main" })).toBe(false);
    expect(matches(advancedOnly, { subject: "chemistry", class: "all", exam: "advanced" })).toBe(true);
  });

  it("shows every subject on All", () => {
    expect(matches(mainOnly, { subject: "all", ...all })).toBe(true);
    expect(matches(advancedOnly, { subject: "all", ...all })).toBe(true);
  });

  it("lists a chapter taught across both classes under each class", () => {
    expect(matches(both, { subject: "physics", class: "11", exam: "all" })).toBe(true);
    expect(matches(both, { subject: "physics", class: "12", exam: "all" })).toBe(true);
    expect(matches(mainOnly, { subject: "physics", class: "11", exam: "all" })).toBe(false);
  });
});

describe("the photo strip", () => {
  it("moves most of a screen at a time and stays inside the strip", () => {
    expect(stepTarget(0, 1000, 2000, 1)).toBe(800);
    expect(stepTarget(800, 1000, 2000, 1)).toBe(1600);
    expect(stepTarget(1600, 1000, 2000, 1)).toBe(2000);
    expect(stepTarget(300, 1000, 2000, -1)).toBe(0);
    expect(stepTarget(0, 1000, 0, 1)).toBe(0); // everything fits: nowhere to go
  });

  it("knows when it is at either end", () => {
    expect(edges(0, 1000, 3000)).toEqual({ atStart: true, atEnd: false });
    expect(edges(1000, 1000, 3000)).toEqual({ atStart: false, atEnd: false });
    expect(edges(1999.6, 1000, 3000)).toEqual({ atStart: false, atEnd: true }); // rounding on a fractional scale
    expect(edges(0, 1000, 900)).toEqual({ atStart: true, atEnd: true });
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

describe("the journey timeline", () => {
  it("fills as the list passes the reading line at mid-screen", () => {
    expect(railFill(800, 1000, 800)).toBe(0);
    expect(railFill(400, 1000, 800)).toBe(0);
    expect(railFill(-100, 1000, 800)).toBe(0.5);
    expect(railFill(-900, 1000, 800)).toBe(1);
  });

  it("makes the last step above the reading line current", () => {
    expect(currentStep([300, 700, 1300], 800)).toBe(0);
    expect(currentStep([100, 350, 1300], 800)).toBe(1);
    expect(currentStep([-200, -50, 390], 800)).toBe(2);
    expect(currentStep([450, 900], 800)).toBe(-1);
  });
});

describe("the test map", () => {
  const q = (chapter: string, difficulty: MapQuestion["difficulty"], status: MapQuestion["status"], seconds = 60): MapQuestion =>
    ({ subject: "physics", chapter, difficulty, status, seconds, average: 90, visits: 1 });
  const questions = [q("a", "easy", "right"), q("a", "hard", "wrong"), q("b", "hard", "left", 12), q("b", "medium", "slow", 150)];

  it("counts how the questions ended", () => {
    expect(tally(questions)).toEqual({ right: 1, slow: 1, wrong: 1, left: 1 });
  });

  it("scores a chapter on what was tried, and counts a slow right answer as right", () => {
    expect(chapterAccuracy(questions)).toEqual([
      { chapter: "a", total: 2, attempted: 2, correct: 1 },
      { chapter: "b", total: 2, attempted: 1, correct: 1 },
    ]);
  });

  it("sets difficulty against result", () => {
    const matrix = difficultyMatrix(questions);
    expect(matrix.hard).toEqual({ right: 0, slow: 0, wrong: 1, left: 1 });
    expect(matrix.easy.right).toBe(1);
    expect(matrix.medium.slow).toBe(1);
  });

  it("sizes bars against an axis rounded up to a whole step", () => {
    expect(axisTop(questions)).toBe(150);
    const chart = { slot: 10, bar: 6, height: 100, dots: 8 };
    expect(barBox(2, 75, 150, chart)).toEqual({ x: 22, y: 58, width: 6, height: 50 });
    expect(barBox(0, 999, 150, chart).height).toBe(100);
  });
});
