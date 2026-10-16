import { expect, test, type Page } from "@playwright/test";

// The layout must work from small phones to large desktops: no horizontal
// scrolling, navigation reachable, job search and links usable at every size.
const VIEWPORTS = [
  { width: 320, height: 640 },
  { width: 375, height: 667 },
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1024, height: 768 },
  { width: 1366, height: 768 },
  { width: 1920, height: 1080 },
];
const APP_PAGES = ["/app", "/app/resume", "/app/preferences", "/app/matches", "/app/jobs", "/app/skills", "/app/saved", "/app/history", "/app/evaluation", "/app/settings"];

async function horizontalOverflow(page: Page): Promise<number> {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
}

test.describe.configure({ mode: "serial" });

let email = "";
test.beforeAll(async ({ request }) => {
  email = `responsive-${Date.now()}@example.com`;
  const res = await request.post("http://localhost:8000/api/v1/auth/register", { data: { email, password: "e2e-pass-123" } });
  expect(res.ok()).toBeTruthy();
});

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("e2e-pass-123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/app/);
}

for (const vp of VIEWPORTS) {
  test(`no horizontal overflow at ${vp.width}px`, async ({ page }) => {
    await page.setViewportSize(vp);
    for (const path of ["/", "/login"]) {
      await page.goto(path);
      expect(await horizontalOverflow(page), `${path} at ${vp.width}px`).toBeLessThanOrEqual(0);
    }
    await signIn(page);
    for (const path of APP_PAGES) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      expect(await horizontalOverflow(page), `${path} at ${vp.width}px`).toBeLessThanOrEqual(0);
    }
  });
}

test("job search, filters and links work on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await signIn(page);
  // Navigation is behind a menu button and closes after choosing a page.
  await page.getByRole("button", { name: "Menu" }).click();
  await page.locator("#mobile-nav").getByRole("link", { name: "Find jobs" }).click();
  await expect(page).toHaveURL(/\/app\/jobs$/);
  await expect(page.locator("#mobile-nav")).toBeHidden();

  await page.getByLabel("Job title, keyword or company").fill("android");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Junior Android Developer" })).toBeVisible();

  // Filters are collapsed until asked for.
  const toggle = page.getByRole("button", { name: /Show filters/ });
  await expect(page.getByLabel("Company", { exact: true })).toBeHidden();
  await toggle.click();
  await expect(page.getByLabel("Company", { exact: true })).toBeVisible();

  const card = page.getByRole("article").first();
  const posting = card.getByRole("link", { name: /original posting|Apply on/ });
  await expect(posting).toHaveAttribute("href", /^https:\/\//);
  await expect(posting).toHaveAttribute("target", "_blank");
  const box = await card.getByRole("link", { name: "View details" }).boundingBox();
  expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
});

test("layout adapts when the screen is resized or rotated", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page);
  await page.goto("/app/jobs");
  await expect(page.getByRole("button", { name: "Menu" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Show filters/ })).toBeVisible();
  // Rotate to landscape tablet, then grow to desktop.
  await page.setViewportSize({ width: 1024, height: 768 });
  await expect(page.getByRole("button", { name: "Menu" })).toBeHidden();
  await expect(page.getByRole("complementary").getByRole("link", { name: "Find jobs" })).toBeVisible();
  await page.setViewportSize({ width: 1366, height: 768 });
  await expect(page.getByRole("button", { name: /Show filters/ })).toBeHidden();
  await expect(page.getByLabel("Company", { exact: true })).toBeVisible();
  expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0);
});
