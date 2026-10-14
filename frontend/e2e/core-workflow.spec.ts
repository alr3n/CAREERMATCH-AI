import { expect, test } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const resumeFile = path.join(here, "fixtures", "synthetic-resume.pdf"); // synthetic, no real personal data

test("upload, review, search, match, open, save, then delete everything", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;

  // Create an account
  await page.goto("/");
  await page.getByRole("link", { name: "Create account" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("e2e-pass-123");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/app\/resume$/);

  // 1. Upload a test resume
  await page.getByLabel("Resume file").setInputFiles(resumeFile);
  await expect(page.getByRole("heading", { name: "My resume" })).toBeVisible();

  // 2. Review extracted skills and correct one
  const skills = page.getByRole("region", { name: "Skills" });
  await expect(skills.getByRole("button", { name: "Remove Python", exact: true })).toBeVisible();
  await expect(skills.getByRole("button", { name: "Remove SQL", exact: true })).toBeVisible();
  await page.getByLabel("Add a skill").fill("Power BI");
  await page.getByLabel("Add a skill").press("Enter");
  await page.getByRole("button", { name: "Save corrections" }).click();
  await expect(page.getByText("Your corrections are saved.")).toBeVisible();

  // 3. Search available jobs
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Find jobs" }).click();
  await expect(page.getByText(/^\d+ listings?$/)).toBeVisible();
  await page.getByLabel("Keywords").fill("analyst");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page.getByRole("heading", { name: "Data Analyst Intern" })).toBeVisible();

  // 4. Generate matches
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Recommended jobs" }).click();
  await page.getByRole("button", { name: "Find my matches" }).click();
  await expect(page.getByText(/not a probability of being hired/)).toBeVisible();

  // 5. Open the top recommendation
  await page.getByRole("article").first().getByRole("link", { name: "View details" }).click();
  await expect(page.getByRole("heading", { name: "Why this job was recommended" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Found in your resume" })).toBeVisible();

  // 6. Save the job
  await page.getByRole("button", { name: "Save job" }).click();
  await expect(page.getByRole("button", { name: "Saved" })).toBeVisible();
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Saved jobs" }).click();
  await expect(page.getByRole("article")).toHaveCount(1);

  // 7. Delete the test resume, then the whole profile
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "My resume" }).click();
  await page.getByRole("button", { name: "Delete resume" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Delete resume" }).click();
  await expect(page.getByRole("heading", { name: "Upload your resume" })).toBeVisible();

  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Settings & privacy" }).click();
  await page.getByRole("button", { name: "Delete my account" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Delete account" }).click();
  await expect(page).toHaveURL("/");

  // The deleted account can no longer sign in.
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("e2e-pass-123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toHaveText("Incorrect email or password");
});
