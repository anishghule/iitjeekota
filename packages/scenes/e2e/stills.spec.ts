import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "@playwright/test";
import config from "../scenes.json" with { type: "json" };

// make stills: the still-tier fallback of every scene, rendered on the full tier at the progress
// set in scenes.json (still.at), with a transparent background so it sits on any surface.
// Only runs when STILLS is set, so the regular browser checks stay quick.
const out = fileURLToPath(new URL("../dist/stills/", import.meta.url));

test.skip(!process.env.STILLS, "set STILLS=1 (make stills) to render the stills");
test.use({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });

test("render the still of every scene", async ({ page }) => {
  mkdirSync(out, { recursive: true });
  await page.goto("/?tier=full");
  await page.evaluate(() => localStorage.setItem("dsap.autoscroll", "off"));
  await page.reload();
  await page.evaluate(() => document.fonts.ready);
  await page.addStyleTag({ content: "html, body { background: transparent !important; } .stage h2, .stage output, header { visibility: hidden; }" });
  for (const [name, scene] of Object.entries(config.scenes)) {
    await page.evaluate(([n, p]) => {
      const section = document.querySelector<HTMLElement>(`[data-scene="${n}"]`)!;
      const top = section.getBoundingClientRect().top + window.scrollY;
      window.scrollTo(0, top + (p as number) * (section.offsetHeight - window.innerHeight));
    }, [name, scene.still.at] as const);
    await page.waitForTimeout(800);
    await page.locator(`[data-scene="${name}"] canvas`).screenshot({ path: `${out}${name}.png`, omitBackground: true });
  }
});
