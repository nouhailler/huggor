import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { estimate } from '../src/estimator.js';

const reference = JSON.parse(await readFile(new URL('./python-reference.json', import.meta.url), 'utf8'));

test('estimator.js reproduit src/resource_calculator.py sur les cas de référence', () => {
  assert.ok(reference.cases.length >= 50);
  for (const expected of reference.cases) {
    const actual = estimate(expected.parametersBillions, expected.ramGib, expected.vramGib);
    const label = `${expected.parametersBillions} Md, RAM ${expected.ramGib}, VRAM ${expected.vramGib}`;
    assert.equal(actual.parameters, expected.parameters, label);
    assert.deepEqual(actual.precisions, expected.precisions, label);
    assert.equal(actual.best, expected.best, label);
    assert.equal(actual.path, expected.path, label);
    // Python arrondit au pair (round), JavaScript à l'entier supérieur : tolérance d'un dixième.
    for (const key of ['tpsLow', 'tpsHigh']) {
      if (expected[key] === null) {
        assert.equal(actual[key], null, label);
      } else {
        assert.ok(Math.abs(actual[key] - expected[key]) <= 0.1 + 1e-9, `${label} ${key}: ${actual[key]} vs ${expected[key]}`);
      }
    }
  }
});

test('un nombre de paramètres inconnu ne produit aucune estimation', () => {
  assert.equal(estimate(0, 16, 0).best, null);
  assert.deepEqual(estimate(0, 16, 0).precisions, []);
});
