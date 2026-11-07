import { defineConfig } from '@playwright/test'
import process from 'node:process'
import path from 'node:path'
import { phaseSettings } from './tests/e2e/e2ePhases.js'

const phase = phaseSettings()

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: true,
  retries: 0,
  globalTeardown: './tests/e2e/globalTeardown.js',
  // Un servidor compartido admite una comparación exclusiva con tres motores.
  workers: 1,
  // TA-040: el gate convierte en fallo las omisiones no aprobadas y los specs críticos sin ejecutar.
  reporter: [['list'], ['html', { open: 'never', ...(phase && {
    outputFolder: path.join('playwright-report', 'e2e-phases', path.basename(phase.directory), phase.phase),
  }) }], ['./tests/e2e/e2eGateReporter.js']],
  ...(phase && { outputDir: path.join(phase.directory, phase.phase) }),
  use: {
    baseURL: 'http://127.0.0.1:5173',
    browserName: 'chromium',
    // Local default: installed stable Chrome. CI can select managed Chromium.
    channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome',
    trace: 'off',
    screenshot: 'off',
    serviceWorkers: 'block',
  },
  projects: [
    { name: 'chromium-desktop', use: { viewport: { width: 1440, height: 900 } } },
    { name: 'chromium-mobile', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
  webServer: [{
    command: 'python -m tests.e2e_server',
    cwd: '../backend',
    url: 'http://127.0.0.1:8017/',
    reuseExistingServer: false,
    timeout: 120_000,
  }, {
    command: 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
    url: 'http://127.0.0.1:5173/hu007-t01.html',
    reuseExistingServer: false,
    env: { VITE_API_URL: 'http://127.0.0.1:8017' },
    timeout: 60_000,
  }],
})
