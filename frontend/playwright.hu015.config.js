import process from 'node:process';
import config from './playwright.config.js';

// Real historical start/rasterize flow, with an isolated repository test backend.
export default {
  ...config,
  testMatch: 'hu015-rasterization.spec.js',
  outputDir: './test-results/hu015',
  reporter: [['list']],
  use: {
    ...config.use,
    channel: process.env.PLAYWRIGHT_EXECUTABLE_PATH ? undefined : config.use.channel,
    launchOptions: process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {},
  },
};
