export const PAGES_BASE = '/optimizador-vidrio/'

export function stagingApiUrl(value) {
  const message = 'Staging requiere VITE_API_URL HTTPS, sin localhost, credenciales, query ni fragmento.'
  let url
  try {
    url = new URL(value)
  } catch {
    throw new Error(message)
  }
  const host = url.hostname.toLowerCase()
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash
    || host === 'localhost' || host.endsWith('.localhost') || host.endsWith('.local')
    || host.startsWith('127.') || host === '0.0.0.0' || host === '[::1]' || host === '[::]') {
    throw new Error(message)
  }
  return url.href.replace(/\/$/, '')
}
