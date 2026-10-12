import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config.js'

export default defineConfig((environment) => mergeConfig(viteConfig(environment), {
  test: {
    environment: 'jsdom',
    include: ['src/features/**/__tests__/**/*.test.jsx', 'src/shared/**/__tests__/**/*.test.jsx'],
    setupFiles: ['./tests/component/setup.js'],
    clearMocks: true,
    restoreMocks: true,
  },
}))
