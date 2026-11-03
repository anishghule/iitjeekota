import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

// The built site (make web) under exactly the headers it is served with (apps/web/dist/_headers,
// from packages/site/security.json): any script, style, font, image, film or request the policy
// would block shows up here as a violation. Pages are scrolled end to end so the 3D world, the
// pinned sections and the film all start.
const headers = readFileSync(new URL("../dist/_headers", import.meta.url), "utf8");

/** The headers of the "/*" block: what every response carries. */
function everyResponse(file: string): Record<string, string> {
  const out: Record<string, string> = {};
  let inBlock = false;
  for (const line of file.split("\n")) {
    if (line && !/^\s/.test(line) && !line.startsWith("#")) inBlock = line.trim() === "/*";
    else if (inBlock && /^\s+\S/.test(line)) {
      const at = line.indexOf(":");
      out[line.slice(0, at).trim()] = line.slice(at + 1).trim();
    }
  }
  return out;
}

const policy = everyResponse(headers);

async function watchViolations(page: Page): Promise<string[]> {
  const found: string[] = [];
  page.on("console", (m) => /content security policy|refused to/i.test(m.text()) && found.push(m.text()));
  page.on("pageerror", (e) => found.push(`error: ${e.message}`));
  await page.addInitScript(() => {
    const seen: string[] = ((window as unknown as { __csp: string[] }).__csp = []);
    document.addEventListener("securitypolicyviolation", (e) => seen.push(`${e.violatedDirective} blocked ${e.blockedURI}`));
  });
  return found;
}

async function scrollThrough(page: Page): Promise<void> {
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < height; y += 700) {
    await page.evaluate((to) => window.scrollTo(0, to), y);
    await page.waitForTimeout(60);
  }
  await page.waitForTimeout(500);
}

test.beforeEach(async ({ context }) => {
  await context.route("**/*", async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, headers: { ...response.headers(), ...policy } });
  });
});

test("the headers file carries the whole policy", () => {
  expect(Object.keys(policy)).toEqual(expect.arrayContaining([
    "Content-Security-Policy", "Referrer-Policy", "X-Content-Type-Options", "Permissions-Policy", "Cross-Origin-Opener-Policy",
  ]));
  expect(policy["Content-Security-Policy"]).toMatch(/script-src 'self'(;|$)/);
  expect(policy["Content-Security-Policy"]).not.toMatch(/unsafe-|\*/);
});

for (const path of ["/en/", "/hi/", "/mr/", "/en/programmes/", "/en/centres/", "/en/jee-syllabus/", "/en/contact/", "/en/iit-jee-coaching-aundh/", "/en/centres/sangvi-head-office/", "/en/fees-and-batches/", "/en/blogs/kota-or-pune/", "/en/class-11-jee/", "/hi/contact/", "/mr/centres/wakad/"]) {
  test(`${path} runs under the policy with no violation`, async ({ page }) => {
    const problems = await watchViolations(page);
    const response = await page.goto(path);
    expect(response?.headers()["content-security-policy"]).toContain("default-src 'none'");
    await scrollThrough(page);
    const blocked = await page.evaluate(() => (window as unknown as { __csp: string[] }).__csp);
    expect([...blocked, ...problems]).toEqual([]);
  });
}

test("the home page keeps working under the policy: world, film and enquiry", async ({ page }) => {
  const problems = await watchViolations(page);
  await page.goto("/en/");
  await scrollThrough(page);
  await expect(page.locator("canvas.world")).toHaveCount(1);
  await expect(page.locator("#classroom video")).toHaveCount(1);
  const blocked = await page.evaluate(() => (window as unknown as { __csp: string[] }).__csp);
  expect([...blocked, ...problems]).toEqual([]);
});

test("the policy really blocks what it should", async ({ page }) => {
  await page.goto("/en/");
  const outcome = await page.evaluate(async () => {
    const result: Record<string, string> = {};
    const seen: string[] = [];
    document.addEventListener("securitypolicyviolation", (e) => seen.push(e.violatedDirective));
    const script = document.createElement("script");
    script.textContent = "window.__ran = true";
    document.head.append(script);
    result.inline = (window as unknown as { __ran?: boolean }).__ran ? "ran" : "blocked";
    try {
      await fetch("https://example.com/", { mode: "no-cors" });
      result.fetch = "ran";
    } catch {
      result.fetch = "blocked";
    }
    result.framed = window.top === window ? "top" : "framed";
    await new Promise((resolve) => setTimeout(resolve, 100));
    result.directives = [...new Set(seen)].sort().join(",");
    return result;
  });
  // eval is not tried here: Playwright's own evaluate runs outside the page's policy, so it would prove nothing.
  expect(outcome).toMatchObject({ inline: "blocked", fetch: "blocked", framed: "top" });
});
