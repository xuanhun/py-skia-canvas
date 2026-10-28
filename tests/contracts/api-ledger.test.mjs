/** Contract-inventory guards: these are not renderer or Python parity tests. */
import assert from 'node:assert/strict';
import test from 'node:test';
import { buildLedger } from '../../scripts/inventory-public-api.mjs';

const ledger = buildLedger();
const find = (owner, name, kind) => ledger.entries.filter(e => e.owner === owner && e.name === name && e.kind === kind);

test('all 17 runtime exports have a home, including GUI and JS-only loaders', () => {
  assert.equal(ledger.exports.length, 17);
  for (const name of ['App', 'Window', 'loadImage', 'loadImageData', 'DOMRect', 'CanvasTexture']) {
    assert(ledger.exports.find(e => e.name === name)?.entries > 0, name);
  }
});

test('image and transform overloads remain separate contracts', () => {
  assert.equal(find('CanvasRenderingContext2D', 'drawImage', 'call').length, 3);
  assert.equal(find('CanvasRenderingContext2D', 'setTransform', 'call').length, 2);
  assert.equal(find('ImageData', 'constructor', 'construct').length, 4);
  assert.equal(find('FontLibrary', 'use', 'call').length, 3);
});

test('mutable accessors and inherited readonly geometry are distinguished', () => {
  assert.equal(find('Canvas', 'gpu', 'get').length, 1);
  assert.equal(find('Canvas', 'gpu', 'set').length, 1);
  assert.equal(find('DOMRect', 'top', 'get').length, 1);
  assert.equal(find('DOMRect', 'top', 'set').length, 0);
  assert.equal(find('DOMPoint', 'matrixTransform', 'call').length, 1);
});

test('runtime/declaration disagreements and Sharp boundaries cannot disappear', () => {
  assert.equal(find('Canvas', 'toFileSync', 'call')[0].availability, 'javascript-only');
  assert.equal(find('Canvas', 'toSharpSync', 'call')[0].availability, 'declaration-only-or-instance-data');
  assert.equal(find('Canvas', 'toSharp', 'call')[0].languageBoundary, 'node-sharp-review-required');
});

test('JS defaults and native routes retain source locations', () => {
  const constructor = find('Canvas', 'constructor', 'construct')[0].javascript[0];
  assert(constructor.parameters.some(p => p.name.includes('textGamma=1.4') && p.defaultExpression === '{}'));
  const getter = find('Canvas', 'gpu', 'get')[0].javascript[0];
  assert(getter.nativeSources.some(e => e.name === 'Canvas_get_engine'));
  assert(getter.path.endsWith('lib/classes/canvas.js'));
});

test('inventory never masquerades as implemented bindings or semantic acceptance', () => {
  assert.equal(new Set(ledger.entries.map(e => e.id)).size, ledger.entries.length);
  assert(ledger.entries.every(e => e.status === 'inventoried' && e.contractAudit === 'pending' && !e.pythonEntry));
});
