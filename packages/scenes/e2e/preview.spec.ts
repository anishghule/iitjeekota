import { expect, test, type Page } from "@playwright/test";

// Renders every scene of the preview at the start, middle and end of its section.
// Screenshots go to SHOTS_DIR when it is set, for a person to look at.
const scenes = ["medal", "kota-prism", "syllabus-slab", "specimens"];
const points = [0, 0.5, 1];

async function scrollTo(page: Page, scene: string, progress: number) {
  await page.evaluate(([name, p]) => {
    const section = document.querySelector<HTMLElement>(`[data-scene="${name}"]`)!;
    const top = section.getBoundingClientRect().top + window.scrollY;
    window.scrollTo(0, top + (p as number) * (section.offsetHeight - window.innerHeight));
  }, [scene, progress] as const);
  await page.waitForTimeout(600);
}

for (const tier of ["full", "lite"] as const) {
  test(`every scene renders on the ${tier} tier without errors`, async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(`/?tier=${tier}`);
    await page.evaluate(() => localStorage.setItem("dsap.autoscroll", "off"));
    await page.reload();
    await page.evaluate(() => document.fonts.ready);
    for (const scene of scenes) {
      for (const p of points) {
        await scrollTo(page, scene, p);
        const canvas = page.locator(`[data-scene="${scene}"] canvas`);
        const shot = await canvas.screenshot({
          ...(process.env.SHOTS_DIR ? { path: `${process.env.SHOTS_DIR}/${tier}-${scene}-${p * 100}.png` } : {}),
        });
        expect(shot.byteLength, `${scene} at ${p} draws something`).toBeGreaterThan(8_000);
      }
    }
    expect(errors).toEqual([]);
  });
}
