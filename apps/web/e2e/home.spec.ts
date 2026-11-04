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

test("the classroom film plays only from its Play button, and scrolling never moves it", async ({ page }) => {
  const errors = await noErrors(page);
  await page.goto("/en/");
  const section = page.locator("#classroom");
  await expect(section).not.toHaveClass(/pinned/);
  await section.scrollIntoViewIfNeeded();
  const film = page.locator("#classroom video");
  const button = page.locator("#classroom [data-film-toggle]");
  await expect(button).toBeVisible();
  await expect(film).toHaveJSProperty("controls", false);
  await expect(button).toHaveAttribute("aria-pressed", "false");
  await expect(button).toContainText("Play the film");

  const seconds = () => film.evaluate((v: HTMLVideoElement) => v.currentTime);
  await page.mouse.wheel(0, 200);
  await page.mouse.wheel(0, -200);
  expect(await seconds()).toBe(0); // scrolling does nothing to the film

  await button.click();
  await expect.poll(() => film.evaluate((v: HTMLVideoElement) => !v.paused)).toBe(true);
  await expect(button).toHaveAttribute("aria-pressed", "true");
  await expect(button).toContainText("Pause the film");
  await button.click();
  await expect.poll(() => film.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true);
  await expect(button).toHaveAttribute("aria-pressed", "false");
  const stopped = await seconds();
  await page.mouse.wheel(0, 300);
  await page.waitForTimeout(400);
  expect(await seconds()).toBe(stopped); // still where Pause left it

  await button.click(); // play, then leave the section: it stops
  await expect.poll(() => film.evaluate((v: HTMLVideoElement) => !v.paused)).toBe(true);
  await page.evaluate(() => scrollTo(0, 0));
  await expect.poll(() => film.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true);
  expect(errors).toEqual([]);
});

test("the cost sum starts with typical Kota amounts that the parent can change", async ({ page }) => {
  const errors = await noErrors(page);
  await page.goto("/en/");
  const calc = page.locator("[data-cost-calc]");
  const coaching = calc.locator('input[name="kota-0"]');
  const hostel = calc.locator('input[name="kota-1"]');
  await expect(coaching).toHaveValue("163000");
  await expect(hostel).toHaveValue("132000");
  await expect(calc.locator('[data-total="kota"]')).toHaveText("₹2,95,000");
  await expect(calc.locator("[data-result]")).toContainText("Fill in both sides");
  await calc.locator('input[name="pune-0"]').fill("150000");
  await expect(calc.locator("[data-result]")).toContainText("Kota costs ₹1,45,000 more a year.");
  await coaching.fill("200000");
  await expect(calc.locator('[data-total="kota"]')).toHaveText("₹3,32,000");
  expect(errors).toEqual([]);
});

test("the photo strip scrolls sideways by touchpad and button, and a vertical scroll over it moves the page", async ({ page }) => {
  const errors = await noErrors(page);
  await page.goto("/en/");
  const gallery = page.locator("#gallery");
  const track = gallery.locator("[data-gallery-track]");
  await gallery.scrollIntoViewIfNeeded();
  const left = () => track.evaluate((el) => el.scrollLeft);
  expect(await track.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(true);
  await expect(gallery.locator("figure")).toHaveCount(8);
  await expect(gallery.locator("figure.gallery__photo--arch")).not.toHaveCount(0);
  await expect(gallery.locator("figure.gallery__photo--circle")).toHaveCount(1);

  const previous = gallery.locator('[data-gallery-step="-1"]');
  const next = gallery.locator('[data-gallery-step="1"]');
  await expect(previous).toBeDisabled();
  await next.click();
  await expect.poll(left).toBeGreaterThan(0);
  await expect(previous).toBeEnabled();

  const box = await track.boundingBox();
  await page.mouse.move((box?.x ?? 0) + 40, (box?.y ?? 0) + 40);
  const sideways = await left();
  await page.mouse.wheel(300, 0);
  await expect.poll(left).toBeGreaterThan(sideways);

  // Scroll snap keeps settling for a moment after a wheel: wait until the strip stops before measuring.
  await expect.poll(async () => {
    const before = await left();
    await page.waitForTimeout(200);
    return before === (await left());
  }).toBe(true);
  const held = await left();
  const pageTop = await page.evaluate(() => scrollY);
  await page.mouse.wheel(0, 200);
  await expect.poll(() => page.evaluate(() => scrollY)).not.toBe(pageTop); // the page moved, not the strip
  expect(await left()).toBe(held);
  expect(errors).toEqual([]);
});

test("the root redirects to English", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/en\/$/);
});

test("home renders every approved section without errors, and may be indexed", async ({ page }) => {
  const errors = await noErrors(page);
  await page.goto("/en/");
  await expect(page.locator("h1")).toHaveCount(1);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "max-image-preview:large");
  for (const id of ["kota-system", "kota-to-pune", "classroom", "portal", "live-test", "report", "syllabus", "journey", "area-map", "programmes", "questions", "enquiry"]) {
    await expect(page.locator(`section#${id}`)).toHaveCount(1);
  }
  // Sections waiting for facts or media stay out.
  for (const id of ["faculty", "results"]) await expect(page.locator(`section#${id}`)).toHaveCount(0);
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

test("the sample test timer waits for the reader, then starts on the first touch or the Start button", async ({ page }) => {
  await page.goto("/en/#live-test");
  const cbt = page.locator("[data-live-test]");
  await page.waitForTimeout(1500);
  await expect(cbt.locator("[data-timer]")).toHaveText("06:00");
  await expect(cbt).not.toHaveAttribute("data-running", "");
  await cbt.locator("[data-palette='1']").click();
  await expect(cbt).toHaveAttribute("data-running", "");
  await cbt.getByRole("button", { name: "Submit test" }).click();
  await cbt.getByRole("button", { name: "Try again" }).click();
  await expect(cbt).not.toHaveAttribute("data-running", "");
  await cbt.getByRole("button", { name: "Start timer" }).click();
  await expect(cbt).toHaveAttribute("data-running", "");
});

test("on a wide screen the syllabus is a table of tiles, and a tile opens its topics in the side panel", async ({ page }) => {
  await page.goto("/en/");
  const syllabus = page.locator("[data-syllabus]");
  await expect(syllabus.locator(".syllabus__table")).toBeVisible();
  await expect(syllabus.locator(".syllabus__index")).toBeHidden();
  await syllabus.locator("[data-filter='subject:chemistry']").click();
  expect(await syllabus.locator("[data-tile]:not([data-dim])").count()).toBeGreaterThan(0);
  await expect(syllabus.locator("[data-tile][data-subject='physics']").first()).toHaveAttribute("data-dim", "");
  await page.locator("[data-tile='p-kinematics']").click();
  await expect(page.locator("[data-panel-title]")).toHaveText("Kinematics");
  await expect(page.locator("[data-panel-body]")).toContainText("Relative velocity");
  await page.keyboard.press("Escape");
  await expect(page.locator("[data-panel]")).toBeHidden();
});

test("the syllabus filters stay on screen while the reader scrolls the table", async ({ page }) => {
  await page.goto("/en/#syllabus");
  await page.evaluate(() => window.scrollBy(0, 900));
  const bar = await page.locator(".syllabus__bar").boundingBox();
  expect(bar!.y).toBeGreaterThanOrEqual(0);
  expect(bar!.y).toBeLessThan(120);
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("the syllabus is a list of rows, one subject at a time, and a link opens its chapter", async ({ page }) => {
    await page.goto("/en/");
    const syllabus = page.locator("[data-syllabus]");
    await expect(syllabus.locator(".syllabus__index")).toBeVisible();
    await expect(syllabus.locator(".syllabus__table")).toBeHidden();
    await expect(syllabus.locator("[data-subject-block]:visible")).toHaveCount(1);
    await syllabus.locator("[data-filter='subject:chemistry']").click();
    await syllabus.getByRole("button", { name: "Class 12" }).click();
    const classes = await syllabus.locator("[data-chapter]:visible").evaluateAll((rows) => rows.map((r) => (r as HTMLElement).dataset.classes ?? ""));
    expect(classes.length).toBeGreaterThan(0);
    expect(classes.every((c) => c.split(" ").includes("12"))).toBe(true);
    await page.goto("/en/#11-p-03");
    await expect(page.locator("details[id='11-p-03']")).toHaveAttribute("open", "");
  });

  test("the Kota route section has no figure and does not pin", async ({ page }) => {
    await page.goto("/en/");
    const route = page.locator("section#kota-to-pune");
    await expect(route).toHaveAttribute("data-pin", "off");
    await expect(route.locator(".route__figure")).toBeHidden();
    expect((await route.boundingBox())?.height).toBeLessThan(844 * 1.5);
  });

  test("the portal window sits below the board, not over it", async ({ page }) => {
    await page.goto("/en/");
    const board = await page.locator(".portal .board").boundingBox();
    const mac = await page.locator(".portal .mac").boundingBox();
    expect(mac!.y).toBeGreaterThanOrEqual(board!.y + board!.height);
  });

  test("the report card is tall enough for its text", async ({ page }) => {
    await page.goto("/en/");
    const card = page.locator(".report__card");
    const box = await card.boundingBox();
    const week = await card.locator("[data-week]:visible").boundingBox();
    expect(box!.height).toBeGreaterThanOrEqual(week!.height);
    expect(box!.height).toBeLessThanOrEqual(844);
  });
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

test("clicking a Kota point scrolls to it and makes it the current one", async ({ page }) => {
  await page.goto("/en/");
  const points = page.locator("#kota-system .kota__points li");
  await points.nth(3).click();
  await expect(points.nth(3)).toHaveAttribute("aria-current", "", { timeout: 5000 });
  await points.nth(1).click();
  await expect(points.nth(1)).toHaveAttribute("aria-current", "", { timeout: 5000 });
});

test.describe("on a tablet", () => {
  test.use({ viewport: { width: 900, height: 800 } });
  test("the Kota route is left out where its figure would be too small to read", async ({ page }) => {
    await page.goto("/en/");
    await expect(page.locator("#kota-to-pune")).toHaveAttribute("data-pin", "off");
    await expect(page.locator("#kota-to-pune .route__figure")).toBeHidden();
  });
});

test("the world canvas mounts behind the page", async ({ page }) => {
  await page.goto("/en/");
  await expect(page.locator("html")).toHaveAttribute("data-world", "");
  await expect(page.locator("canvas[data-world]")).toHaveCount(1);
});

test.describe("a syllabus row, on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 } });
test("a syllabus row opens to its topics, and Expand all opens every visible row", async ({ page }) => {
  await page.goto("/en/#syllabus");
  const row = page.locator("[data-chapter='p-kinematics']");
  await expect(row).toContainText("11-P-02");
  await expect(row.locator("details")).not.toHaveAttribute("open", "");
  await row.locator("summary").click();
  await expect(row.locator("details")).toHaveAttribute("open", "");
  await expect(row).toContainText("Relative velocity");
  await page.locator("[data-expand]").click();
  expect(await page.locator("[data-chapter]:visible details:not([open])").count()).toBe(0);
});
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

  test("animated sections pin with their visual held, and only the listed ones autoscroll", async ({ page }) => {
    await page.goto("/en/");
    await expect(page.locator("#kota-system")).toHaveAttribute("data-pin", "narrow");
    await expect(page.locator("#kota-system")).toHaveAttribute("data-autoscroll", "intro");
    await expect(page.locator("#hero")).toHaveAttribute("data-autoscroll", "intro");
    await expect(page.locator("#report")).toHaveAttribute("data-autoscroll", "report");
    await expect(page.locator("#journey")).toHaveAttribute("data-autoscroll", "journey");
    await expect(page.locator("#kota-to-pune")).toHaveAttribute("data-autoscroll", "intro");
    await expect(page.locator("#classroom")).toHaveAttribute("data-autoscroll", "intro");
    await expect(page.locator("#portal")).not.toHaveAttribute("data-autoscroll", /.*/); // the opening ends with the classroom
    await expect(page.locator("html")).not.toHaveAttribute("data-autoscroll", /.*/);
    await expect(page.locator("[data-autoscroll-toggle]")).toBeVisible();
  });

  test("half way through the Kota section, the prism holds still on screen with the current point", async ({ page }) => {
    const errors = await noErrors(page);
    await page.goto("/en/");
    const box = await page.locator("#kota-system").evaluate((el) => {
      const top = el.getBoundingClientRect().top + window.scrollY;
      window.scrollTo(0, top + ((el as HTMLElement).offsetHeight - window.innerHeight) * 0.6);
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
