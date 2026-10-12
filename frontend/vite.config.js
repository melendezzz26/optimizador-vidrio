import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import process from 'node:process'
import { PAGES_BASE, stagingApiUrl } from './config/staging.js'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const staging = mode === 'staging'
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  return {
    plugins: [react()],
    base: staging ? PAGES_BASE : '/',
    ...(staging && {
      define: { 'import.meta.env.VITE_API_URL': JSON.stringify(stagingApiUrl(env.VITE_API_URL)) },
    }),
  }
})
