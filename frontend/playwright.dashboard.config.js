import { defineConfig } from '@playwright/test';

// Dashboard T3 runs against the backend and Vite processes started outside Playwright.
// This config deliberately has no webServer: the default config starts a temporary DB.
export default defineConfig({
  testDir: './tests/e2e',
  testMatch: 'ta-dashboard.spec.js',
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    browserName: 'chromium',
    viewport: { width: 1366, height: 900 },
    serviceWorkers: 'block',
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
});
