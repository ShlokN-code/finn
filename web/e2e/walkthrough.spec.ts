// The evaluator's five minutes, scripted (PRODUCT §11), at phone (375 px) and laptop (1280 px) widths, against the
// deployed site. Read-only except "Connect Telegram", which creates a one-time link that expires in 15 minutes.
import { expect, test, type Locator, type Page } from "@playwright/test";

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
  await page.locator("[data-ask-bar] button").click();
  await page.getByPlaceholder(/What did management say about margins/).fill(ASK_Q);
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  const ans = page.locator("[data-ask-state]");
  await expect(ans).toBeVisible({ timeout: 60_000 });
  expect(await ans.getAttribute("data-ask-state")).toBe("answered");
  await expect(ans.getByText("Sources")).toBeVisible();
});

test("Ask on the Brief: names a company → its answer, with a way into its research", async ({ page }) => {
  await openBrief(page);
  await page.locator("[data-ask-bar] button").click();
  const field = page.locator("#ask-q");
  await field.fill("What did Infosys say about deal wins?");
  await expect(page.locator('[data-ask-target="INFY"]')).toHaveText(/About Infosys \(INFY\)/);
  // No company named → the holdings with research are offered as picks; picking one asks it (a cached question).
  await field.fill(ASK_Q);
  const pick = page.locator("[data-ask-picks]").getByRole("button", { name: "INFY", exact: true });
  await expect(pick).toBeVisible();
  expect(await page.locator("[data-ask-picks] button[aria-pressed]").count()).toBeLessThanOrEqual(5); // never every holding
  await pick.click();
  const ans = page.locator("[data-ask-state]");
  await expect(ans).toBeVisible({ timeout: 60_000 });
  expect(await ans.getAttribute("data-ask-state")).toBe("answered");
  await page.getByRole("link", { name: /Open INFY research/ }).click();
  await expect(page).toHaveURL(/\/research\/INFY$/);
});

test("Ask on Portfolio: a company without research says so and opens it in Research", async ({ page }) => {
  await page.goto("/portfolio");
  await skipTour(page);
  await page.locator("[data-ask-bar] button").click();
  await page.locator("#ask-q").fill("How is Asian Paints doing on margins?");
  await expect(page.locator('[data-ask-target="ASIANPAINT"]')).toBeVisible();
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  const none = page.locator('[data-ask-state="no_research"]');
  await expect(none).toBeVisible({ timeout: 60_000 });
  await expect(none.getByText("No research for Asian Paints yet")).toBeVisible();
  expect(await none.getByRole("link", { name: "Open ASIANPAINT in Research" }).getAttribute("href")).toBe("/research/ASIANPAINT");
});

test("Ask on Research home: search any company; a holding without a dossier answers from its transcripts", async ({ page }) => {
  await page.goto("/research");
  await skipTour(page);
  await page.locator("[data-ask-bar] button").click();
  await expect(page.locator("[data-ask-picks] button[aria-pressed]").first()).toBeVisible();
  // Search any company → one Ask can't answer says so, without asking.
  await page.locator("#ask-company").fill("ITC");
  await page.locator("#ask-company-results").getByRole("button", { name: /^ITC\b/ }).first().click();
  const none = page.locator('[data-ask-state="no_research"]');
  await expect(none.getByText("No research for ITC yet")).toBeVisible();
  expect(await none.getByRole("link", { name: "Open ITC in Research" }).getAttribute("href")).toBe("/research/ITC");
  // A holding with no dossier whose calls were read (drivers build): answered from those transcripts, labelled so.
  await page.locator("#ask-q").fill("What did Hindustan Aeronautics say about order inflows?");
  await expect(page.locator('[data-ask-target="HAL"]')).toBeVisible();
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  const ans = page.locator("[data-ask-state]");
  await expect(ans).toBeVisible({ timeout: 60_000 });
  expect(["answered", "not_found"]).toContain(await ans.getAttribute("data-ask-state"));
  expect(await ans.getAttribute("data-ask-basis")).toBe("transcripts");
  await expect(ans.getByText(/call transcripts only/)).toBeVisible();
});

// Android Chrome closed the keyboard after every key (the sheet re-took focus on each re-render). Type one key at a
// time, as a phone keyboard does, and check the field still has focus after each one.
async function typeKeepingFocus(page: Page, field: Locator, text: string) {
  await field.tap();
  await expect(field).toBeFocused();
  for (const ch of text) {
    await page.keyboard.type(ch);
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => setTimeout(r, 30)))); // let effects run
    await expect(field, `focus after typing ${JSON.stringify(ch)}`).toBeFocused();
  }
}

const TYPING: { name: string; open: (page: Page) => Promise<Locator>; text: string; value: string | RegExp }[] = [
  {
    name: "Ask bar on a company",
    open: async (page) => {
      await page.goto("/research/INFY");
      await skipTour(page);
      await expect(page.getByRole("navigation", { name: "Sections" })).toBeVisible({ timeout: 60_000 });
      await page.locator("[data-ask-bar] button").click();
      return page.locator("#ask-q");
    },
    text: "margin guidance",
    value: "margin guidance",
  },
  {
    name: "Ask bar on the Brief",
    open: async (page) => {
      await openBrief(page);
      await page.locator("[data-ask-bar] button").click();
      return page.locator("#ask-q");
    },
    text: "Infosys margins",
    value: "Infosys margins",
  },
  {
    name: "Ask bar on Portfolio",
    open: async (page) => {
      await page.goto("/portfolio");
      await skipTour(page);
      await page.locator("[data-ask-bar] button").click();
      return page.locator("#ask-q");
    },
    text: "HDFC Bank NIM",
    value: "HDFC Bank NIM",
  },
  {
    name: "Ask bar on Research home",
    open: async (page) => {
      await page.goto("/research");
      await skipTour(page);
      await page.locator("[data-ask-bar] button").click();
      return page.locator("#ask-q");
    },
    text: "Persistent deal wins",
    value: "Persistent deal wins",
  },
  {
    name: "Ask: search any company",
    open: async (page) => {
      await openBrief(page);
      await page.locator("[data-ask-bar] button").click();
      return page.locator("#ask-company");
    },
    text: "asian paints",
    value: "asian paints",
  },
  {
    name: "Research ticker search",
    open: async (page) => {
      await page.goto("/research");
      await skipTour(page);
      return page.getByRole("combobox");
    },
    text: "hdfc bank",
    value: "hdfc bank",
  },
  {
    name: "Portfolio paste/CSV import",
    open: async (page) => {
      await page.goto("/portfolio");
      await skipTour(page);
      await page.getByRole("button", { name: /Use my holdings|Edit holdings/ }).click();
      return page.getByRole("dialog").locator("textarea");
    },
    text: "INFY 7%\nITC 5%",
    value: "INFY 7%\nITC 5%",
  },
  {
    name: "Rules quiet hours (time field)",
    open: async (page) => {
      await page.goto("/rules");
      await skipTour(page);
      return page.getByLabel("Quiet from");
    },
    text: "2130",
    value: /^\d\d:\d\d$/,
  },
];

for (const t of TYPING) {
  test(`typing keeps focus on a phone: ${t.name}`, async ({ page }, info) => {
    test.skip(info.project.name !== "phone", "phone keyboards only");
    const field = await t.open(page);
    await typeKeepingFocus(page, field, t.text);
    await expect(field).toHaveValue(t.value);
  });
}

test("Rules: alert rules and the Telegram entry are on screen", async ({ page }) => {
  await page.goto("/rules");
  await skipTour(page);
  await expect(page.getByRole("heading", { name: "Rules", exact: true })).toBeVisible();
  await expect(page.locator("[data-ask-bar]")).toHaveCount(0); // no Ask bar on Rules
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
