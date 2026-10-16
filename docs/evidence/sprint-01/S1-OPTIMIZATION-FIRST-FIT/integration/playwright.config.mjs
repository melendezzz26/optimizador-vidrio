// Portable equivalent of the Cloud runner used for the full regression.
// PostgreSQL is created/stopped by tests.e2e_server; no shared DATABASE_URL.
import config from '../../../../../frontend/playwright.config.js';
import { fileURLToPath } from 'node:url';
import process from 'node:process';

const at = relative => fileURLToPath(new URL(`../../../../../${relative}`, import.meta.url));
const executablePath = process.env.NEWGLASS_E2E_CHROMIUM_EXECUTABLE;
export default {
  ...config,
  testDir: at('frontend/tests/e2e/'),
  globalTeardown: at('frontend/tests/e2e/globalTeardown.js'),
  outputDir: at('frontend/test-results/integration/'),
  reporter: [['list']],
  use: { ...config.use, ...(executablePath ? { channel: undefined, launchOptions: { executablePath } } : {}) },
  webServer: config.webServer.map((server, index) => ({ ...server, cwd: at(index === 0 ? 'backend/' : 'frontend/') })),
};
