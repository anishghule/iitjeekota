import { tokens } from "@dsap/tokens";
import { expect, test, type Page } from "@playwright/test";

// Autoscroll in a real browser (plan C5), on the scene preview's pinned sections.
const { pauseMs } = tokens.motion.autoscroll;

async function intoFirstSection(page: Page) {
  await page.goto("/?tier=lite");
  await page.evaluate(() => localStorage.removeItem("dsap.autoscroll"));
  await page.reload();
  const top = await page.evaluate(() => document.querySelector<HTMLElement>("[data-autoscroll]")!.getBoundingClientRect().top + window.scrollY);
  await page.evaluate((y) => window.scrollTo(0, y + 50), top);
  await page.mouse.move(640, 400);
  for (let i = 0; i < 4; i++) {
    await page.mouse.wheel(0, 120);
    await page.waitForTimeout(40);
  }
  return page.evaluate(() => window.scrollY);
}

test("keeps scrolling in the reader's direction after the pause", async ({ page }) => {
  const afterWheel = await intoFirstSection(page);
  await page.waitForTimeout(pauseMs / 2);
  const beforePause = await page.evaluate(() => window.scrollY);
  expect(beforePause - afterWheel).toBeLessThan(5);
  await page.waitForTimeout(pauseMs + 600);
  expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(beforePause + 20);
});

test("stops when the reader scrolls again", async ({ page }) => {
  await intoFirstSection(page);
  await page.waitForTimeout(pauseMs + 600);
  await page.mouse.wheel(0, -40);
  // The browser animates the wheel's own scroll for a short while; measure once it has landed,
  // and before a new pause could start autoscroll again.
  await page.waitForTimeout(pauseMs / 2);
  const stopped = await page.evaluate(() => window.scrollY);
  await page.waitForTimeout(pauseMs / 4);
  expect(Math.abs((await page.evaluate(() => window.scrollY)) - stopped)).toBeLessThan(2);
});

test("stays off when the reader switches it off", async ({ page }) => {
  await page.goto("/?tier=lite");
  await page.getByRole("button", { name: /Autoscroll/ }).click();
  const afterWheel = await intoFirstSectionKeepingChoice(page);
  await page.waitForTimeout(pauseMs + 600);
  expect(Math.abs((await page.evaluate(() => window.scrollY)) - afterWheel)).toBeLessThan(5);
});

async function intoFirstSectionKeepingChoice(page: Page) {
  const top = await page.evaluate(() => document.querySelector<HTMLElement>("[data-autoscroll]")!.getBoundingClientRect().top + window.scrollY);
  await page.evaluate((y) => window.scrollTo(0, y + 50), top);
  await page.mouse.move(640, 400);
  for (let i = 0; i < 4; i++) {
    await page.mouse.wheel(0, 120);
    await page.waitForTimeout(40);
  }
  return page.evaluate(() => window.scrollY);
}
