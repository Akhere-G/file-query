import { defineConfig, devices } from "@playwright/test";

const BACKEND_URL = "http://localhost:8000";
const FRONTEND_URL = "http://localhost:3000";
const INTERNAL_API_SECRET = "e2e-internal-secret";
const python = process.env.E2E_PYTHON ?? "../backend/venv/bin/python";

/**
 * Runs the real Next.js app against the real FastAPI app, with a throwaway database and
 * fake AWS/Bedrock services (backend/e2e_server.py). Start the test database first:
 * `make test-db-up`.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: FRONTEND_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `${python} ../backend/e2e_server.py`,
      url: `${BACKEND_URL}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        FRONTEND_URL,
        INTERNAL_API_SECRET,
        E2E_PUBLIC_URL: BACKEND_URL,
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      command: "npm run build && npm run start",
      url: FRONTEND_URL,
      reuseExistingServer: false,
      timeout: 300_000,
      env: { BASE_URL: BACKEND_URL, INTERNAL_API_SECRET },
    },
  ],
});
