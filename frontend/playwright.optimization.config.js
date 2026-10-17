import { defineConfig } from '@playwright/test';
import process from 'node:process';
import base from './playwright.config.js';
const port = process.env.OPTIMIZATION_E2E_PORT || '5186';
const baseURL = `http://127.0.0.1:${port}`;
export default defineConfig({
  ...base,
  testDir: './tests/e2e', testMatch: 's1-optimization-ui.spec.js', fullyParallel: false,
  outputDir: './test-results/optimization-ui',
  workers: 1, retries: 0, reporter: [['list']],
  use: { baseURL, browserName: 'chromium', serviceWorkers: 'block',
    channel: process.env.PLAYWRIGHT_EXECUTABLE_PATH ? undefined : (process.env.PLAYWRIGHT_CHANNEL || 'chrome'),
    launchOptions: process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {},
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
  webServer: [base.webServer[0], { command: `npm run dev -- --host 127.0.0.1 --port ${port} --strictPort`,
    url: baseURL, reuseExistingServer: false,
    env: { VITE_API_URL: 'http://127.0.0.1:8017' }, timeout: 60000 }],
});
