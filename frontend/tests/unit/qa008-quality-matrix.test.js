import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = new URL('../../../docs/quality/TA-QA-001-matriz-metricas-iso25023.md', import.meta.url)
const rows = async () => (await readFile(source, 'utf8')).split('\n')
  .filter(line => /^\| M[FPUMCST]-\d\d \|/.test(line))
  .map(line => line.split('|').map(value => value.trim()))

test('percentage quality measures multiply by 100', async () => {
  const percentages = (await rows()).filter(columns => columns[6] === '%')
  assert.equal(percentages.length, 19)
  for (const columns of percentages) {
    assert.match(columns[5], /\s\/\s.+\s\*\s100$/, columns[1])
  }
})

test('percentile measures preserve their multiplier and sample condition', async () => {
  const measures = new Map((await rows()).map(columns => [columns[1], columns[5]]))
  assert.match(measures.get('MP-02'), /ceil\(0,50 \* n\)/)
  assert.match(measures.get('MP-03'), /ceil\(0,95 \* n\), n >= 100/)
})
