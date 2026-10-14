import { defineConfig, devices } from "@playwright/test";

// Starts a throwaway backend (SQLite, demo provider) and the built frontend.
// Set E2E_EXTERNAL=1 to run against servers you started yourself.
const external = process.env.E2E_EXTERNAL === "1";
const python = process.env.E2E_PYTHON ?? "python";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:4173",
    trace: "retain-on-failure",
    ...devices["Desktop Chrome"],
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH } : {},
  },
  webServer: external
    ? undefined
    : [
        {
          command:
            `bash -c "rm -f e2e.db && ${python} -m alembic upgrade head && ${python} -m uvicorn app.main:app --port 8000"`,
          cwd: "../backend",
          url: "http://localhost:8000/health/ready",
          reuseExistingServer: !process.env.CI,
          timeout: 60_000,
          env: {
            APP_ENV: "development",
            DATABASE_URL: "sqlite:///./e2e.db",
            SECRET_KEY: "e2e-secret-key-that-is-long-enough-for-tests-only",
            CORS_ORIGINS: "http://localhost:4173",
            ENABLE_DEMO_PROVIDER: "true",
            EMBEDDING_BACKEND: "lsa",
            STORAGE_DIR: "./e2e-storage",
            GREENHOUSE_BOARDS: "",
            LEVER_SITES: "",
          },
        },
        {
          command: "npm run build && npx vite preview --port 4173 --strictPort",
          url: "http://localhost:4173",
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
          env: { VITE_API_BASE_URL: "http://localhost:8000" },
        },
      ],
});
