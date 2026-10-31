import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

// The scene preview: pnpm preview. Fonts come from packages/tokens/fonts at /fonts, as on the site.
const here = (path: string) => fileURLToPath(new URL(path, import.meta.url));

export default defineConfig({
  root: here("."),
  publicDir: here("../../tokens"),
  server: { port: 5178, strictPort: true, fs: { allow: [here("../../..")] } },
  preview: { port: 5178, strictPort: true },
});
