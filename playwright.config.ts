import { defineConfig } from "@playwright/test";

// Browser checks (plan D6). WebGL runs on SwiftShader, the software renderer, so screenshots work
// without a GPU. Two projects: the scene preview (Phase 5) and the built site (make web first).
const SCENES = "http://localhost:5178";
const WEB = "http://localhost:5180";
const launchOptions = { args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] };

export default defineConfig({
  timeout: 60_000,
  use: { viewport: { width: 1280, height: 800 }, launchOptions },
  projects: [
    { name: "scenes", testDir: "packages", testMatch: "*/e2e/**/*.spec.ts", use: { baseURL: SCENES } },
    { name: "web", testDir: "apps/web/e2e", testMatch: "**/*.spec.ts", use: { baseURL: WEB } },
  ],
  webServer: [
    { command: "pnpm exec vite --config packages/scenes/preview/vite.config.ts", url: SCENES, reuseExistingServer: true },
    { command: "pnpm --filter @dsap/web serve", url: `${WEB}/en/`, reuseExistingServer: true },
  ],
});
