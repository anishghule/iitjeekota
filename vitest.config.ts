import { defineConfig } from "vitest/config";

// One run for every browser package. DOM tests opt in per file with
// `// @vitest-environment happy-dom`; everything else runs in plain Node.
export default defineConfig({
  test: {
    include: ["packages/*/test/**/*.test.ts", "apps/web/test/**/*.test.ts"],
    environment: "node",
  },
});
