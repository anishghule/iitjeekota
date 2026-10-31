// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from "vitest";
import { bindAutoscroll } from "../src/dom.ts";
import { pinnedProgress } from "../src/progress.ts";

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

describe("pinned progress", () => {
  it("runs from 0 at the top to 1 when the section bottom meets the viewport bottom", () => {
    expect(pinnedProgress(0, 3000, 1000)).toBe(0);
    expect(pinnedProgress(-1000, 3000, 1000)).toBe(0.5);
    expect(pinnedProgress(-2000, 3000, 1000)).toBe(1);
    expect(pinnedProgress(400, 3000, 1000)).toBe(0);
    expect(pinnedProgress(-5000, 3000, 1000)).toBe(1);
  });

  it("treats a section no taller than the viewport as a step", () => {
    expect(pinnedProgress(10, 800, 1000)).toBe(0);
    expect(pinnedProgress(-10, 800, 1000)).toBe(1);
  });
});
