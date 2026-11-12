import { ask, expect, pricingDoc, register, test, uploadFile } from "./fixtures";

test("upload a document, wait for processing, ask a question and open its source", async ({
  page,
}) => {
  await register(page);

  await uploadFile(page, pricingDoc());

  // The backend processes the file asynchronously: the UI says so, then catches up by polling.
  await expect(page.getByText("Some files are still processing.")).toBeVisible();
  await expect(page.getByText("pricing.md")).toBeVisible();
  await expect(page.getByText("Some files are still processing.")).toBeHidden({ timeout: 30_000 });

  await ask(page, "How much does the starter plan cost?");

  const answer = page.getByText("The starter plan costs nine euros per month.").first();
  await expect(answer).toBeVisible();

  // The answer is backed by a citation pointing at the uploaded file.
  const citation = page.getByRole("button", { name: "Pricing" });
  await expect(citation).toBeVisible();
  await citation.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Source citation");
  await expect(dialog).toContainText("pricing.md");
  await expect(dialog).toContainText("The starter plan costs nine euros per month.");
  await page.keyboard.press("Escape");

  // The conversation, with its citation, survives a reload.
  await page.reload();
  await page.getByRole("tab", { name: "Chat" }).click();
  await expect(page.getByText("How much does the starter plan cost?")).toBeVisible();
  await expect(page.getByRole("button", { name: "Pricing" })).toBeVisible();
});

test("chat is blocked until the uploaded file has been processed", async ({ page }) => {
  await register(page);
  await uploadFile(page, pricingDoc());

  await page.getByRole("tab", { name: "Chat" }).click();
  await expect(page.getByText("All files are still processing")).toBeVisible();
  await expect(page.getByPlaceholder("Ask a question...")).toBeDisabled();

  await expect(page.getByPlaceholder("Ask a question...")).toBeEnabled({ timeout: 30_000 });
});
