import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { PAGES_BASE } from '../config/staging.js'

function files(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const file = path.join(directory, entry.name)
    return entry.isDirectory() ? files(file) : [file]
  })
}

const html = fs.readFileSync('dist/index.html', 'utf8')
const references = [...html.matchAll(/(?:src|href)="([^"]+)"/g)].map((match) => match[1])
assert(references.length > 0, 'El build debe tener assets')
for (const reference of references) {
  assert(reference.startsWith(PAGES_BASE), 'Asset HTML fuera de la base Pages')
  assert(fs.existsSync(path.join('dist', reference.slice(PAGES_BASE.length))), 'Asset HTML ausente')
}
const forbidden = /localhost|127\.0\.0\.1|SECRET_KEY|DATABASE_URL|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:ghp_|github_pat_|sb_secret_)[A-Za-z0-9_-]{12,}|\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|postgres(?:ql)?(?:\+\w+)?:\/\//i
for (const file of files('dist').filter((file) => /\.(?:html|js|css|json|svg|map)$/.test(file))) {
  assert(!forbidden.test(fs.readFileSync(file, 'utf8')), `Contenido no permitido en ${file}; valor omitido`)
}
console.log('PASS: base Pages, assets presentes y bundle sin localhost, DSN, nombres de secretos o patrones de tokens privados.')
