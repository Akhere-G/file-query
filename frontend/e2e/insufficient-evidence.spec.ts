import { ask, expect, pricingDoc, register, test, uploadFile, waitForProcessing } from "./fixtures";

test.beforeEach(async ({ page }) => {
  await register(page);
  await uploadFile(page, pricingDoc());
  await waitForProcessing(page);
});

test("a question the documents say nothing about gets a refusal without sources", async ({
  page,
}) => {
  await ask(page, "Tell me about zebra migration");

  await expect(
    page.getByText("Sorry, I could not answer your question with the context provided."),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Pricing" })).toHaveCount(0);
});

test("related but unsupported questions are declined rather than guessed", async ({ page }) => {
  await ask(page, "Who founded the pricing department?");

  await expect(
    page.getByText("I don't have enough information in the provided documents to answer that."),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Pricing" })).toHaveCount(0);
});
