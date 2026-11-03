// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from "vitest";
import config from "../src/config/autoscroll.json";
import { markUnits } from "../src/islands/autoscroll.ts";

afterEach(() => {
  document.body.innerHTML = "";
});

describe("which sections autoscroll", () => {
  it("marks the listed sections with their unit's name and leaves the rest alone", () => {
    document.body.innerHTML = '<section id="hero"></section><section id="kota-system"></section><section id="kota-to-pune"></section><section id="classroom"></section><section id="portal"></section><section id="journey"></section>';
    expect(markUnits(document, config.units)).toBe(5);
    expect(document.getElementById("hero")?.getAttribute("data-autoscroll")).toBe("intro");
    expect(document.getElementById("kota-system")?.getAttribute("data-autoscroll")).toBe("intro");
    expect(document.getElementById("journey")?.getAttribute("data-autoscroll")).toBe("journey");
    expect(document.getElementById("kota-to-pune")?.getAttribute("data-autoscroll")).toBe("intro");
    expect(document.getElementById("classroom")?.getAttribute("data-autoscroll")).toBe("intro");
    expect(document.getElementById("portal")?.hasAttribute("data-autoscroll")).toBe(false); // the unit ends with the classroom
  });

  it("finds nothing on a page without them, so no toggle is needed", () => {
    document.body.innerHTML = '<section id="programmes"></section>';
    expect(markUnits(document, config.units)).toBe(0);
  });

  it("is the opening (hero to the classroom), the report, its test map and the journey", () => {
    expect(config.units).toEqual({ intro: ["hero", "kota-system", "kota-to-pune", "classroom"], report: ["report"], "report-test": ["report-test"], journey: ["journey"] });
  });
});
