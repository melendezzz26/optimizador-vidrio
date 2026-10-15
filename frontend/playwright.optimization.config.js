import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/e2e', testMatch: 's1-optimization-ui.spec.js', fullyParallel: false,
  workers: 1, retries: 0, reporter: [['list']],
  use: { baseURL: 'http://127.0.0.1:5186', browserName: 'chromium', channel: 'chrome', serviceWorkers: 'block' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
  webServer: { command: 'npm run dev -- --host 127.0.0.1 --port 5186 --strictPort',
    url: 'http://127.0.0.1:5186', reuseExistingServer: false,
    env: { VITE_API_URL: 'http://127.0.0.1:5186' }, timeout: 60000 },
});
