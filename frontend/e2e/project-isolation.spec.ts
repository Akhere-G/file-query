import { expect, pricingDoc, register, test, uploadFile, waitForProcessing } from "./fixtures";

test("another user cannot open or see someone else's project", async ({ page, browser }) => {
  await register(page);
  const projectId = await uploadFile(page, pricingDoc());
  await waitForProcessing(page);

  const otherContext = await browser.newContext();
  const other = await otherContext.newPage();
  await other.route(/posthog\.com/, (route) => route.abort());
  await register(other);

  await other.goto(`/dashboard?projectId=${projectId}`);

  await expect(other).toHaveURL(/\/dashboard$/);
  await expect(other.getByText("No projects yet")).toBeVisible();
  await other.getByRole("tab", { name: "Files" }).click();
  await expect(other.getByText("pricing.md")).toHaveCount(0);

  // The original owner still has access.
  await page.goto(`/dashboard?projectId=${projectId}`);
  await page.getByRole("tab", { name: "Files" }).click();
  await expect(page.getByText("pricing.md")).toBeVisible();

  await otherContext.close();
});
