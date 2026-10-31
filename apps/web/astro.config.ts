import { defineConfig } from "astro/config";
import site from "./src/generated/data/site.json" with { type: "json" };

// docs/adr/0007-web-app.md. Everything the site renders comes from src/generated (make web-data).
export default defineConfig({
  site: site.origin,
  output: "static",
  trailingSlash: "always",
  publicDir: "./src/generated/public",
  // The fixed root redirect from packages/site/site.json; never by browser language.
  redirects: { "/": site.root.redirectTo },
  build: {
    format: "directory",
    // No inline styles or scripts, so the Content Security Policy can stay strict.
    inlineStylesheets: "never",
  },
  vite: { build: { assetsInlineLimit: 0 } },
  devToolbar: { enabled: false },
});
