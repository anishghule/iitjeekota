// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from "vitest";
import { bindAutoscroll, mergeUnits } from "../src/dom.ts";
import { holdLead, pinnedProgress } from "../src/progress.ts";

function setReducedMotion(reduced: boolean) {
  window.matchMedia = ((query: string) => ({
    matches: reduced && query.includes("reduce"),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia;
}

afterEach(() => {
  window.localStorage.clear();
  document.body.innerHTML = "";
});

describe("the reader's choice", () => {
  it("is on by default and remembered when switched off", () => {
    setReducedMotion(false);
    const first = bindAutoscroll(window);
    expect(first.isOn()).toBe(true);
    first.setOn(false);
    first.destroy();
    const second = bindAutoscroll(window);
    expect(second.isOn()).toBe(false);
    second.destroy();
  });

  it("stays off under reduced motion, whatever was chosen", () => {
    setReducedMotion(true);
    const binding = bindAutoscroll(window);
    binding.setOn(true);
    expect(binding.isAvailable()).toBe(false);
    expect(binding.isOn()).toBe(false);
    binding.destroy();
  });
});

describe("autoscroll units", () => {
  it("makes elements that share a name one section, from the first top to the last bottom", () => {
    const merged = mergeUnits([
      { name: "intro", start: 0, end: 900 },
      { name: "intro", start: 900, end: 4000 },
      { name: "report", start: 6000, end: 9000 },
    ]);
    expect(merged).toEqual([{ start: 0, end: 4000 }, { start: 6000, end: 9000 }]);
  });

  it("keeps unnamed elements as sections of their own, and does not merge across different names", () => {
    expect(mergeUnits([{ name: "", start: 0, end: 10 }, { name: "", start: 10, end: 20 }, { name: "a", start: 30, end: 40 }, { name: "b", start: 40, end: 50 }]))
      .toHaveLength(4);
  });

  it("takes the widest span when the elements are listed out of page order", () => {
    expect(mergeUnits([{ name: "u", start: 500, end: 800 }, { name: "u", start: 0, end: 300 }])).toEqual([{ start: 0, end: 800 }]);
  });
});

describe("pinned progress", () => {
  it("runs from 0 at the top to 1 when the section bottom meets the viewport bottom", () => {
    expect(pinnedProgress(0, 3000, 1000)).toBe(0);
    expect(pinnedProgress(-1000, 3000, 1000)).toBe(0.5);
    expect(pinnedProgress(-2000, 3000, 1000)).toBe(1);
    expect(pinnedProgress(400, 3000, 1000)).toBe(0);
    expect(pinnedProgress(-5000, 3000, 1000)).toBe(1);
  });

  it("starts only after the lead, when the held part sticks below the text", () => {
    expect(pinnedProgress(-300, 3000, 1000, 600)).toBe(0);
    expect(pinnedProgress(-600, 3000, 1000, 600)).toBe(0);
    expect(pinnedProgress(-1300, 3000, 1000, 600)).toBe(0.5);
    expect(pinnedProgress(-2000, 3000, 1000, 600)).toBe(1);
  });

  it("treats a section no taller than the viewport as a step", () => {
    expect(pinnedProgress(10, 800, 1000)).toBe(0);
    expect(pinnedProgress(-10, 800, 1000)).toBe(1);
  });
});

describe("where a held part starts to stick", () => {
  const section = (pin: string) => {
    document.body.innerHTML = `<section data-pin="${pin}"><div><p id="text"></p><div data-pin-visual></div></div></section>`;
    const el = document.querySelector("section") as HTMLElement;
    const text = document.getElementById("text") as HTMLElement;
    Object.defineProperties(text, { offsetTop: { value: 40 }, offsetHeight: { value: 560 } });
    const held = el.querySelector("[data-pin-visual]") as HTMLElement;
    held.style.top = "72px";
    el.querySelector("div")!.style.rowGap = "24px";
    return el;
  };

  it("is the text above it plus the gap, less the offset it sticks at", () => {
    expect(holdLead(section("narrow"), window)).toBe(40 + 560 + 24 - 72);
  });

  it("is zero when the whole stage pins or nothing does", () => {
    expect(holdLead(section("wide"), window)).toBe(0);
    expect(holdLead(section("off"), window)).toBe(0);
  });
});
