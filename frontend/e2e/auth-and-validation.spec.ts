import { expect, logout, PASSWORD, pricingDoc, register, test, uniqueEmail, uploadFile } from "./fixtures";

test("signed-out visitors are sent to the login page", async ({ page }) => {
  await page.goto("/dashboard");

  await expect(page).toHaveURL(/\/login\?callbackUrl=%2Fdashboard$/);
  await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
});

test("signed-in users are kept out of the login page and can log out", async ({ page }) => {
  await register(page);

  await page.goto("/login");
  await expect(page).toHaveURL(/\/dashboard$/);

  await logout(page);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
});

test("registration explains invalid input before anything is sent", async ({ page }) => {
  await page.goto("/register");
  await page.locator("#username").fill("E2E User");
  await page.locator("#email").fill(uniqueEmail());
  await page.locator("#password").fill("weakpassword");
  await page.locator("#repeatPassword").fill("different");
  await page.locator("form").getByRole("button", { name: "Register" }).click();

  await expect(page.getByText(/at least 1 number/)).toBeVisible();
  await expect(page.getByText("Passwords must match")).toBeVisible();
  await expect(page).toHaveURL(/\/register$/);
});

test("registration requires accepting the terms", async ({ page }) => {
  await page.goto("/register");
  await page.locator("#username").fill("E2E User");
  await page.locator("#email").fill(uniqueEmail());
  await page.locator("#password").fill(PASSWORD);
  await page.locator("#repeatPassword").fill(PASSWORD);
  await page.locator("form").getByRole("button", { name: "Register" }).click();

  await expect(page.getByText("You must accept the terms and conditions to register")).toBeVisible();
  await expect(page).toHaveURL(/\/register$/);
});

test("logging in with a wrong password shows an error and stays on the page", async ({ page }) => {
  const email = await register(page);
  await logout(page);

  await page.goto("/login");
  await page.getByPlaceholder("Email").fill(email);
  await page.locator("#password").fill(`${PASSWORD}-wrong`);
  await page.locator("form").getByRole("button", { name: "Login" }).click();

  await expect(page.locator("form").getByRole("alert")).toContainText("Incorrect email or password.");
  await expect(page).toHaveURL(/\/login/);
});

test("registering the same email twice is rejected", async ({ page }) => {
  const email = await register(page);
  await logout(page);

  await page.goto("/register");
  await page.locator("#username").fill("Again");
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(PASSWORD);
  await page.locator("#repeatPassword").fill(PASSWORD);
  await page.getByRole("checkbox").click();
  await page.locator("form").getByRole("button", { name: "Register" }).click();

  await expect(page.locator("form").getByRole("alert")).toContainText("already exists");
  await expect(page).toHaveURL(/\/register$/);
});

test("unsupported file types are rejected with a clear message and nothing is created", async ({
  page,
}) => {
  await register(page);
  await page.getByRole("tab", { name: "Files" }).click();
  await page.locator("input[type=file]").setInputFiles({
    name: "setup.exe",
    mimeType: "application/x-msdownload",
    buffer: Buffer.from("MZ"),
  });
  await page.getByRole("button", { name: "Upload 1 file" }).click();

  await expect(page.getByText(/Files must be one of/)).toBeVisible();
  await expect(page).not.toHaveURL(/projectId/);
  await expect(page.getByText("setup.exe")).toBeVisible(); // still staged so it can be removed
});

test("a rejected upload does not break later uploads", async ({ page }) => {
  await register(page);
  await page.getByRole("tab", { name: "Files" }).click();
  await page.locator("input[type=file]").setInputFiles({
    name: "setup.exe",
    mimeType: "application/x-msdownload",
    buffer: Buffer.from("MZ"),
  });
  await page.getByRole("button", { name: "Upload 1 file" }).click();
  await expect(page.getByText(/Files must be one of/)).toBeVisible();
  await page.getByRole("button", { name: "Remove setup.exe" }).click();

  await uploadFile(page, pricingDoc());

  await expect(page).toHaveURL(/projectId=\d+/);
});
