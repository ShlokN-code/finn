// Evaluator walkthrough against the DEPLOYED site (not a dev server): `npx playwright test` from web/.
// FINN_URL overrides the target; FINN_BUILD_TICKER=<SYM> also runs "research a never-built ticker" (spends model
// quota — manual runs only, counted in backend/evals/COST.md).
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "e2e/report" }]],
  use: {
    baseURL: process.env.FINN_URL ?? "https://finn-tau-red.vercel.app",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "phone",
      use: {
        viewport: { width: 375, height: 812 },
        isMobile: true,
        hasTouch: true,
        deviceScaleFactor: 2,
        userAgent:
          "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Mobile Safari/537.36",
      },
    },
    { name: "laptop", use: { viewport: { width: 1280, height: 800 } } },
  ],
});
