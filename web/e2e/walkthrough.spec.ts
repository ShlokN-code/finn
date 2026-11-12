// The evaluator's five minutes, scripted (PRODUCT §11), at phone (375 px) and laptop (1280 px) widths, against the
// deployed site. Read-only except "Connect Telegram", which creates a one-time link that expires in 15 minutes.
import { expect, test, type Page } from "@playwright/test";

const ASK_Q = "What revenue growth guidance did management give for FY27?"; // cached: no model call

async function skipTour(page: Page) {
  const skip = page.getByRole("button", { name: "Skip" });
  if (await skip.isVisible().catch(() => false)) await skip.click();
}

async function openBrief(page: Page) {
  await page.goto("/brief");
  await skipTour(page);
  await expect(page.locator("[data-card]").first()).toBeVisible({ timeout: 60_000 });
  await skipTour(page);
}

test("landing: QR + live phone preview on a laptop; straight into the Brief on a phone", async ({ page }, info) => {
  await page.goto("/");
  if (info.project.name === "laptop") {
    await expect(page.getByText("Open on your phone")).toBeVisible();
    await expect(page.getByRole("img", { name: /QR code for/ })).toBeVisible();
    const frame = page.frameLocator('iframe[title="FINN on a phone — live"]');
    await expect(frame.locator("[data-card]").first()).toBeVisible({ timeout: 60_000 });
  } else {
    await expect(page.getByText("Open on your phone")).toBeHidden();
    await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
  }
});

test("Brief loads with ranked cards and a freshness stamp", async ({ page }) => {
  await openBrief(page);
  await expect(page.getByText(/Data as of|Saved day · data as of|Freshness unknown/).first()).toBeVisible();
  expect(await page.locator("[data-card]").count()).toBeGreaterThan(0);
});

test("swipe a card past 40% → toast → UNDO restores it", async ({ page }) => {
  await openBrief(page);
  const card = page.locator("[data-card]").first();
  const id = await card.getAttribute("data-card");
  const box = (await card.boundingBox())!;
  const y = box.y + Math.min(box.height / 2, 40);
  await page.mouse.move(box.x + 20, y);
  await page.mouse.down();
  for (let i = 1; i <= 12; i++) await page.mouse.move(box.x + 20 + (box.width * 0.6 * i) / 12, y, { steps: 2 });
  await page.mouse.up();
  const undo = page.getByRole("button", { name: "UNDO" });
  await expect(undo).toBeVisible({ timeout: 5_000 });
  await expect(page.getByText(/marked reviewed/i)).toBeVisible();
  await undo.click();
  await expect(page.locator(`[data-card="${id}"]`)).toBeVisible();
});

test("open a card's source: a readable exchange document", async ({ page }) => {
  await openBrief(page);
  await page.locator("[data-card]").first().click();
  const link = page.locator('[data-card] a[href^="http"]').first();
  await expect(link).toBeVisible();
  const href = (await link.getAttribute("href")) ?? "";
  expect(href).toMatch(/^https:\/\/(nsearchives\.nseindia\.com|www\.nseindia\.com|www\.bseindia\.com|www\.screener\.in|finance\.yahoo\.com)/);
  expect(href).not.toMatch(/\.xml($|#)/); // readable-first: never raw XBRL as the Open target
});

test("Promise Ledger → a figure's provenance sheet names the document and page", async ({ page }) => {
  await page.goto("/research/INFY");
  await skipTour(page);
  await expect(page.getByRole("navigation", { name: "Sections" })).toBeVisible({ timeout: 60_000 });
  await page.getByRole("navigation", { name: "Sections" }).getByText("Ledger").click();
  const fig = page.locator("#ledger button[data-figure]").first();
  await expect(fig).toBeVisible();
  await fig.click();
  await expect(page.getByRole("dialog").getByText(/p\.\s?\d+/).first()).toBeVisible();
});

test("Ask about a company: a cited answer (or an honest 'Not found')", async ({ page }) => {
  await page.goto("/research/INFY");
  await skipTour(page);
  await expect(page.getByRole("navigation", { name: "Sections" })).toBeVisible({ timeout: 60_000 });
  await page.getByRole("button", { name: /Ask about INFY/ }).click();
  await page.getByPlaceholder(/What did management say about margins/).fill(ASK_Q);
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  const ans = page.locator("[data-ask-state]");
  await expect(ans).toBeVisible({ timeout: 60_000 });
  expect(await ans.getAttribute("data-ask-state")).toBe("answered");
  await expect(ans.getByText("Sources")).toBeVisible();
});

test("Rules: alert rules and the Telegram entry are on screen", async ({ page }) => {
  await page.goto("/rules");
  await skipTour(page);
  await expect(page.getByRole("heading", { name: "Rules", exact: true })).toBeVisible();
  await expect(page.getByText("Price move", { exact: true })).toBeVisible();
  await expect(page.getByText("Quiet hours", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Connect Telegram/ })).toBeVisible();
});

test("Connect Telegram gives a t.me deep link", async ({ page }, info) => {
  test.skip(info.project.name !== "phone", "one link per run is enough");
  await page.goto("/connect");
  await skipTour(page);
  await page.getByRole("button", { name: /Connect Telegram/ }).click();
  const open = page.getByRole("link", { name: /Open Telegram/ });
  await expect(open).toBeVisible({ timeout: 60_000 });
  expect(await open.getAttribute("href")).toMatch(/^https:\/\/t\.me\/\w+\?start=/);
});

test("research a ticker never built before (manual: FINN_BUILD_TICKER)", async ({ page }, info) => {
  const sym = process.env.FINN_BUILD_TICKER;
  test.skip(!sym || info.project.name !== "phone", "spends model quota; run by hand with FINN_BUILD_TICKER=<SYM>");
  test.setTimeout(15 * 60_000);
  await page.goto(`/research/${sym}`);
  await skipTour(page);
  await page.getByRole("button", { name: `Research ${sym}` }).click();
  // The build shows its progress, sections fill in while it runs, and the panel goes away when the job ends.
  await expect(page.locator("[data-build-progress]")).toBeVisible({ timeout: 60_000 });
  await expect(page.locator("#snapshot")).toBeVisible({ timeout: 5 * 60_000 });
  await expect(page.locator("[data-build-progress]")).toBeHidden({ timeout: 14 * 60_000 });
  await expect(page.locator('[data-build-progress="failed"]')).toHaveCount(0);
  await expect(page.locator("#ledger")).toBeVisible();
  await expect(page.locator("#snapshot").getByText(/Coming soon|Something went wrong/)).toHaveCount(0);
});
