import { defineConfig } from "@playwright/test";

// Browser checks (plan D6). WebGL runs on SwiftShader, the software renderer, so screenshots work
// without a GPU. Two projects: the scene preview (Phase 5) and the built site (make web first).
const SCENES = "http://localhost:5178";
const WEB = "http://localhost:5180";
const launchOptions = { args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] };

// The software renderer uses every core it can get: a scene test takes 13 to 23 s on an 8-core laptop
// (about 3.7 cores busy). On a CI runner with 2 to 4 slower cores, two of them side by side starve each
// other and the page stops answering. So CI runs one test at a time, and a scene test may take three
// times the usual limit.
const SCENE_TIMEOUT = 180_000;

export default defineConfig({
  timeout: 60_000,
  workers: process.env.CI ? 1 : undefined,
  use: { viewport: { width: 1280, height: 800 }, launchOptions },
  projects: [
    { name: "scenes", testDir: "packages", testMatch: "*/e2e/**/*.spec.ts", timeout: SCENE_TIMEOUT, use: { baseURL: SCENES } },
    { name: "web", testDir: "apps/web/e2e", testMatch: "**/*.spec.ts", use: { baseURL: WEB } },
  ],
  webServer: [
    { command: "pnpm exec vite --config packages/scenes/preview/vite.config.ts", url: SCENES, reuseExistingServer: true },
    { command: "pnpm --filter @dsap/web serve", url: `${WEB}/en/`, reuseExistingServer: true },
  ],
});
