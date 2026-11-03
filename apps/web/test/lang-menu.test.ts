// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from "vitest";
import { initLangMenus, isOutside } from "../src/islands/lang-menu.ts";

function page(): { menu: HTMLDetailsElement; summary: HTMLElement; outside: HTMLElement } {
  document.body.innerHTML = `
    <p id="outside">elsewhere</p>
    <details data-lang-menu><summary>English</summary><ul><li><a href="/hi/">हिन्दी</a></li></ul></details>`;
  initLangMenus(window);
  return {
    menu: document.querySelector("details")!,
    summary: document.querySelector("summary")!,
    outside: document.getElementById("outside")!,
  };
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("the language dropdown", () => {
  it("closes on Esc and gives focus back to its button", () => {
    const { menu, summary } = page();
    menu.open = true;
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(menu.open).toBe(false);
    expect(document.activeElement).toBe(summary);
  });

  it("closes on a click outside, not on a click inside", () => {
    const { menu, summary, outside } = page();
    menu.open = true;
    summary.dispatchEvent(new Event("pointerdown", { bubbles: true }));
    expect(menu.open).toBe(true);
    outside.dispatchEvent(new Event("pointerdown", { bubbles: true }));
    expect(menu.open).toBe(false);
  });

  it("tells inside from outside", () => {
    const { menu, outside } = page();
    expect(isOutside(menu, menu.querySelector("a"))).toBe(false);
    expect(isOutside(menu, outside)).toBe(true);
    expect(isOutside(menu, null)).toBe(true);
  });
});
