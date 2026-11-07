import { test } from 'node:test';
import assert from 'node:assert/strict';
import { beamFallbackSummary } from '../../src/features/optimization/beamFallbackModel.js';

const diagnostic = statistics => ({ origin: 'ENGINE', termination_reason: 'COMPLETED', statistics });

test('M6 completed with First Fit reports the units each part decided', () => {
  assert.equal(beamFallbackSummary(diagnostic({ fallback_used: 1, fallback_beam_units: 3, fallback_units: 43 })),
    'Búsqueda continuada con respaldo First Fit: M6 decidió 3 unidades y el respaldo 43 unidades.');
  assert.equal(beamFallbackSummary(diagnostic({ fallback_used: 1, fallback_beam_units: 0, fallback_units: 1 })),
    'Búsqueda continuada con respaldo First Fit: M6 decidió 0 unidades y el respaldo 1 unidad.');
});

test('without the fallback counter there is no fallback label', () => {
  assert.equal(beamFallbackSummary(diagnostic({ expansions: 120 })), null);
  assert.equal(beamFallbackSummary(diagnostic({})), null);
  assert.equal(beamFallbackSummary(null), null);
  assert.equal(beamFallbackSummary(diagnostic({ fallback_used: 0, fallback_units: 2 })), null);
});
