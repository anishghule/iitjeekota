import { expect, test, type Page } from "@playwright/test";

// The built home page (make web), in a real browser. Set SHOTS_DIR to also save a screenshot of
// every section, on a wide screen and a phone, for a visual review.
const shots = process.env.SHOTS_DIR;

async function noErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(e.message));
  return errors;
}

test("the root redirects to English", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/en\/$/);
});

test("home renders every approved section without errors, and is noindex before launch", async ({ page }) => {
  const errors = await noErrors(page);
  await page.goto("/en/");
  await expect(page.locator("h1")).toHaveCount(1);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
  for (const id of ["kota-system", "kota-to-pune", "portal", "live-test", "report", "syllabus", "journey", "area-map", "programmes", "questions", "enquiry"]) {
    await expect(page.locator(`section#${id}`)).toHaveCount(1);
  }
  // Sections waiting for facts or media stay out.
  for (const id of ["faculty", "classroom", "results"]) await expect(page.locator(`section#${id}`)).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("the sample test scores like JEE Main", async ({ page }) => {
  await page.goto("/en/#live-test");
  const cbt = page.locator("[data-live-test]");
  await cbt.locator("[data-question]:visible label").nth(1).click(); // the right answer to question 1
  await cbt.getByRole("button", { name: "Save and next" }).click();
  await cbt.locator("[data-question]:visible label").nth(0).click(); // a wrong answer to question 2
  await cbt.getByRole("button", { name: "Submit test" }).click();
  await expect(cbt.locator('[data-score="right"]')).toHaveText("1");
  await expect(cbt.locator('[data-score="wrong"]')).toHaveText("1");
  await expect(cbt.locator('[data-score="left"]')).toHaveText("1");
  await expect(cbt.locator('[data-score="marks"]')).toHaveText("3");
});

test("the enquiry form checks its fields, then opens WhatsApp with the message", async ({ page }) => {
  await page.goto("/en/#enquiry");
  await page.evaluate(() => {
    (window as unknown as { opened: string[] }).opened = [];
    window.open = (url?: string | URL) => {
      (window as unknown as { opened: string[] }).opened.push(String(url));
      return null;
    };
  });
  const form = page.locator("form[data-enquiry]");
  await form.getByRole("button", { name: "Send on WhatsApp" }).click();
  await expect(form.locator('[data-error="name"]')).not.toBeEmpty();
  await form.getByLabel("Student's name").fill("Asha");
  await form.getByLabel("Class now").selectOption({ label: "Class 10" });
  await form.getByLabel("Area").selectOption({ label: "Aundh" });
  await form.getByLabel("Parent's mobile number").fill("98765 43210");
  await form.getByRole("checkbox").check();
  await form.getByRole("button", { name: "Send on WhatsApp" }).click();
  const opened = await page.evaluate(() => (window as unknown as { opened: string[] }).opened);
  expect(opened).toHaveLength(1);
  expect(opened[0]).toMatch(/^https:\/\/wa\.me\/\d+\?text=/);
  expect(decodeURIComponent(opened[0] ?? "")).toContain("Asha");
  expect(decodeURIComponent(opened[0] ?? "")).toContain("9876543210");
});

test("picking an area shows its card", async ({ page }) => {
  await page.goto("/en/#area-map");
  const map = page.locator("[data-area-map]");
  await map.getByRole("button", { name: "Baner" }).click();
  await expect(map.locator('[data-card="baner"]')).toBeVisible();
  await expect(map.locator('[data-card="aundh"]')).toBeHidden();
});

test("a syllabus chapter opens its panel, and Esc closes it", async ({ page }) => {
  await page.goto("/en/#syllabus");
  await page.getByRole("button", { name: "Kinematics" }).click();
  const panel = page.locator("[data-panel]");
  await expect(panel).toBeVisible();
  await expect(panel.locator("[data-panel-title]")).toHaveText("Kinematics");
  await expect(panel.locator("[data-panel-meta]")).toContainText("Physics");
  await page.keyboard.press("Escape");
  await expect(panel).toBeHidden();
});

test("the footer links every live area page by the area's name", async ({ page }) => {
  await page.goto("/en/");
  const areas = page.locator("footer nav", { hasText: "JEE coaching by area" });
  await expect(areas.getByRole("link", { name: "Aundh" })).toHaveAttribute("href", "/en/iit-jee-coaching-aundh/");
});

test("the digital board plays its demonstrations and the portal opens on the live class", async ({ page }) => {
  await page.goto("/en/#portal");
  await expect(page.locator("[data-board-title]")).toHaveText("Area under a curve");
  await page.getByRole("button", { name: "Quiz" }).click();
  await expect(page.locator("[data-board-title]")).toHaveText("Live quiz");
  await expect(page.getByRole("tab", { name: "Live class" })).toHaveAttribute("aria-selected", "true");
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("animated sections pin with their visual held, so autoscroll works here too", async ({ page }) => {
    await page.goto("/en/");
    await expect(page.locator("#kota-system")).toHaveAttribute("data-pin", "narrow");
    await expect(page.locator("#kota-system")).toHaveAttribute("data-autoscroll", "");
    await expect(page.locator("[data-autoscroll-toggle]")).toBeVisible();
  });

  test("half way through the Kota section, the prism holds still on screen with the current point", async ({ page }) => {
    const errors = await noErrors(page);
    await page.goto("/en/");
    const box = await page.locator("#kota-system").evaluate((el) => {
      const top = el.getBoundingClientRect().top + window.scrollY;
      window.scrollTo(0, top + (el.offsetHeight - window.innerHeight) * 0.6);
      return null;
    });
    expect(box).toBeNull();
    await page.waitForTimeout(600);
    const visual = await page.locator("#kota-system .kota__visual").boundingBox();
    const prism = await page.locator("#kota-system .kota__prism").boundingBox();
    expect(visual, "visual").not.toBeNull();
    expect(visual!.y).toBeGreaterThanOrEqual(0);
    expect(visual!.y + visual!.height).toBeLessThanOrEqual(844 + 1);
    expect(prism!.height, `prism ${JSON.stringify(prism)}`).toBeGreaterThan(150);
    await expect(page.locator("#kota-system .kota__points li[aria-current]")).toBeVisible();
    if (shots) {
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `${shots}/phone-kota-held.png` });
    }
    expect(errors).toEqual([]);
  });

  test("the sample test fits one screen, with the question numbers in a row", async ({ page }) => {
    await page.goto("/en/#live-test");
    const cbt = page.locator("[data-live-test]");
    const height = await cbt.evaluate((el) => el.getBoundingClientRect().height);
    expect(height).toBeLessThanOrEqual(844 - 72);
    const tops = await cbt.locator("[data-palette]").evaluateAll((els) => els.map((el) => Math.round(el.getBoundingClientRect().top)));
    expect(new Set(tops).size).toBe(1);
  });

  test("the menu opens as a dialog, holds focus and closes on Esc", async ({ page }) => {
    await page.goto("/en/");
    const button = page.locator("[data-menu-button]");
    await expect(page.locator(".site-nav")).toBeHidden();
    await button.click();
    await expect(button).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("#site-menu")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.locator("#site-menu")).toBeHidden();
    await expect(button).toBeFocused();
  });
});

test("screenshots of every section", async ({ page }) => {
  test.skip(!shots, "set SHOTS_DIR to save screenshots (and SHOTS_LANGS=en,hi,mr for other languages)");
  const langs = (process.env.SHOTS_LANGS ?? "en").split(",");
  const sizes = [["wide", { width: 1440, height: 900 }], ["phone", { width: 390, height: 844 }]] as const;
  for (const [lang, [size, viewport]] of langs.flatMap((l) => sizes.map((s) => [l, s] as const))) {
    const name = `${lang}-${size}`;
    await page.setViewportSize(viewport);
    await page.goto(`/${lang}/`);
    await page.evaluate(() => localStorage.setItem("dsap.autoscroll", "off"));
    await page.reload();
    const ids = await page.locator("main > section, main > header").evaluateAll((els) => els.map((el, i) => el.id || `s${i}`));
    for (const [i, id] of ids.entries()) {
      await page.evaluate((index) => {
        const el = document.querySelectorAll("main > section, main > header")[index] as HTMLElement;
        const pinned = el.dataset.pin !== undefined;
        window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY + (pinned ? (el.offsetHeight - window.innerHeight) * 0.5 : 0));
      }, i);
      await page.waitForTimeout(1200);
      await page.screenshot({ path: `${shots}/${name}-${String(i).padStart(2, "0")}-${id}.png` });
    }
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(400);
    await page.screenshot({ path: `${shots}/${name}-99-footer.png` });
  }
});
