import assert from 'node:assert/strict'
import test from 'node:test'
import { PAGES_BASE, stagingApiUrl } from '../../config/staging.js'

test('Pages usa el subpath aprobado y una API HTTPS explícita', () => {
  assert.equal(PAGES_BASE, '/optimizador-vidrio/')
  assert.equal(stagingApiUrl('https://api.example.test/'), 'https://api.example.test')
})

for (const value of [undefined, '', 'invalid', 'http://api.example.test',
  'https://localhost', 'https://app.localhost', 'https://127.0.0.1',
  'https://127.1', 'https://2130706433', 'https://0.0.0.0', 'https://[::1]',
  'https://[::]', 'https://host.local', 'https://user:password@api.example.test',
  'https://api.example.test?token=synthetic', 'https://api.example.test#fragment']) {
  test(`build staging rechaza entrada no apta: ${String(value)}`, () => {
    assert.throws(() => stagingApiUrl(value), /Staging requiere VITE_API_URL HTTPS/)
  })
}
