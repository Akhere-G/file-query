import { expect, test as base, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";

export const PASSWORD = "Passw0rdTest";

export const test = base.extend({
  // Analytics must never leave the machine during tests.
  page: async ({ page }, provide) => {
    await page.route(/posthog\.com/, (route) => route.abort());
    await provide(page);
  },
});

export { expect };

let counter = 0;
export const uniqueEmail = () => `e2e-${Date.now()}-${counter++}@example.com`;

export async function register(page: Page, email = uniqueEmail()) {
  await page.goto("/register");
  await page.locator("#username").fill("E2E User");
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(PASSWORD);
  await page.locator("#repeatPassword").fill(PASSWORD);
  await page.getByRole("checkbox").click();
  await page.locator("form").getByRole("button", { name: "Register" }).click();
  await page.waitForURL("**/dashboard");
  return email;
}

export async function logout(page: Page) {
  await page.getByRole("navigation").getByRole("button", { name: "Log out" }).click();
  // Navigating away before the logout request finishes would abort it and keep the session.
  await expect(page.getByRole("navigation").getByRole("link", { name: "Login" })).toBeVisible();
}

export const pricingDoc = () => ({
  name: "pricing.md",
  mimeType: "text/markdown",
  buffer: readFileSync(path.join(__dirname, "fixtures", "pricing.md")),
});

/** Uploads one file from the Files tab and returns the id of the project it created. */
export async function uploadFile(
  page: Page,
  file: { name: string; mimeType: string; buffer: Buffer },
) {
  await page.getByRole("tab", { name: "Files" }).click();
  await page.locator("input[type=file]").setInputFiles(file);
  await page.getByRole("button", { name: "Upload 1 file" }).click();
  await page.waitForURL(/projectId=\d+/);
  return Number(new URL(page.url()).searchParams.get("projectId"));
}

export async function waitForProcessing(page: Page) {
  await expect(page.getByText("Some files are still processing.")).toBeHidden();
}

export async function ask(page: Page, question: string) {
  await page.getByRole("tab", { name: "Chat" }).click();
  const box = page.getByPlaceholder("Ask a question...");
  await box.fill(question);
  await box.press("Enter");
}
