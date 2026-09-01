import test from 'node:test';
import assert from 'node:assert/strict';

import { applyTelemetryFrame, normalizeAsset, toUiStatus } from '../src/api/normalize.js';

test('status normalization preserves operational states', () => {
  assert.equal(toUiStatus('ACTIVE'), 'ACTIVE');
  assert.equal(toUiStatus('UNASSIGNED'), 'UNASSIGNED');
  assert.equal(toUiStatus('OVERDUE'), 'OVERDUE');
  assert.equal(toUiStatus('IDLE'), 'IDLE_WARNING');
  assert.equal(toUiStatus('SAFETY_LOCKOUT'), 'CRITICAL_ALERT');
});

test('anomaly state takes precedence over an active backend status', () => {
  assert.equal(toUiStatus('ACTIVE', { isAnomaly: true }), 'CRITICAL_ALERT');
});

test('asset normalization retains zero telemetry and uses site coordinates', () => {
  const result = normalizeAsset({
    asset_id: 'EXC-101',
    type: 'Excavator',
    status: 'ACTIVE',
    current_site_id: 'S001',
    fuel_level_pct: 0,
    speed_kmh: 0,
  }, { S001: { site_name: 'North Yard', center_lat: 12.3, center_lng: 77.6 } });

  assert.equal(result.fuelLevel, 0);
  assert.equal(result.speedKmH, 0);
  assert.deepEqual(result.coords, [12.3, 77.6]);
  assert.equal(result.siteName, 'North Yard');
});

test('telemetry merges coordinates and caps the visible trail', () => {
  const trail = Array.from({ length: 12 }, (_, index) => [index, index]);
  const result = applyTelemetryFrame({ trail }, { lat: 20, lng: 30, fuel_level_pct: 0 });

  assert.deepEqual(result.coords, [20, 30]);
  assert.equal(result.trail.length, 12);
  assert.deepEqual(result.trail.at(-1), [20, 30]);
  assert.equal(result.fuelLevel, 0);
});
