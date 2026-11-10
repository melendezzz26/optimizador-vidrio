import { defineConfig } from '@playwright/test'

const sizes = [
  ['desktop', 1920, 1080], ['laptop', 1366, 768],
  ['tablet', 768, 1024], ['mobile', 390, 844],
]
export default defineConfig({
  testDir: './tests/compatibility', workers: 1, retries: 0, timeout: 120000,
  reporter: [['list'], ['json', { outputFile: 'test-results/ta-qa-008.json' }]],
  use: { baseURL: 'http://127.0.0.1:5173', trace: 'off', screenshot: 'only-on-failure' },
  projects: ['chrome', 'msedge'].flatMap(channel => sizes.map(([name, width, height]) => ({
    name: `${channel}-${name}`, use: { browserName: 'chromium', channel, viewport: { width, height } },
  }))),
})
