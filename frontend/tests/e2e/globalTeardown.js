import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

export default function teardown() {
  execFileSync('python', ['-m', 'tests.e2e_server', '--stop'], {
    cwd: fileURLToPath(new URL('../../../backend/', import.meta.url)),
    windowsHide: true,
    stdio: 'inherit',
  })
}
