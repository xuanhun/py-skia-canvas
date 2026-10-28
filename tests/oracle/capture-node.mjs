/** Development-only oracle. Explicit module path; never a Python runtime dependency. */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const sha = data => crypto.createHash('sha256').update(data).digest('hex');

/** Parse named CLI options, rejecting typos instead of silently reducing test coverage. */
function options(args) {
  const result = {};
  for (let i = 0; i < args.length; i++) {
    const key = args[i];
    if (key === '--require-gpu') result.requireGpu = true;
    else if (key === '--require-cpu') result.requireCpu = true;
    else if (['--module', '--fixtures', '--out', '--case', '--environment', '--role'].includes(key)) {
      if (!args[i + 1] || args[i + 1].startsWith('--')) throw Error(`Missing ${key} value`);
      result[key.slice(2)] = args[++i];
    } else throw Error(`Unknown option: ${key}`);
  }
  if (!result.module || !result.out) throw Error('Required: --module ABSOLUTE_PACKAGE_DIR --out test-runs/NEW_ID');
  if (result.requireCpu && result.requireGpu) throw Error('Choose exactly one backend requirement');
  result.role ??= 'node-oracle';
  if (!['node-oracle', 'node-rebuild'].includes(result.role)) throw Error('Invalid --role (node-oracle or node-rebuild)');
  return result;
}

/** Verify an owned, local font/config manifest; no font bytes enter output or native objects. */
function environmentManifest(filename) {
  if (!filename) return null;
  const bytes = fs.readFileSync(path.resolve(root, filename));
  const document = JSON.parse(bytes);
  if (document.schema !== 'py-skia-canvas-environment/v1' || !document.fontFiles?.length) {
    throw Error('Invalid environment manifest or empty font file list');
  }
  for (const file of [...document.fontFiles, ...document.fontConfiguration]) {
    const data = fs.readFileSync(file.path);
    if (data.length !== file.bytes || sha(data) !== file.sha256) throw Error(`Environment resource changed: ${file.path}`);
  }
  // Match Python's canonical serialization for this metadata-only object.
  const canonical = value => Array.isArray(value) ? value.map(canonical)
    : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])])) : value;
  const resources = canonical({ fonts: document.fontFiles, configuration: document.fontConfiguration });
  // Python ensure_ascii=True escapes non-ASCII names, including surrogate pairs.
  const serialized = JSON.stringify(resources).replace(/[\u007f-\uffff]/g, c => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`);
  if (sha(serialized) !== document.fontResourcesSha256) throw Error('Environment resource manifest fingerprint mismatch');
  return { bytes, document };
}

/** Resolve a child path and reject escapes, including existing directory symlinks. */
function within(base, candidate) {
  const resolved = path.resolve(base, candidate);
  const relative = path.relative(base, resolved);
  if (!relative || relative === '..' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    throw Error(`Path must be strictly below ${base}`);
  }
  let ancestor = resolved;
  while (!fs.existsSync(ancestor)) ancestor = path.dirname(ancestor);
  const actualBase = fs.realpathSync(base);
  const actual = fs.realpathSync(ancestor);
  const check = path.relative(actualBase, actual);
  if (check === '..' || check.startsWith(`..${path.sep}`) || path.isAbsolute(check)) throw Error('Symlink escapes output/asset root');
  return resolved;
}

/** Preserve undefined, non-finite floats, -0, typed arrays and enumerable metrics losslessly. */
function encode(value, ancestors = new Set()) {
  if (value === undefined) return { $undefined: true };
  if (typeof value === 'number') {
    if (Number.isNaN(value)) return { $number: 'NaN' };
    if (!Number.isFinite(value)) return { $number: String(value) };
    if (Object.is(value, -0)) return { $number: '-0' };
    return value;
  }
  if (value === null || ['string', 'boolean'].includes(typeof value)) return value;
  if (typeof value !== 'object') throw Error(`Unsupported observation type: ${typeof value}`);
  if (ancestors.has(value)) throw Error('Cyclic observation; add an explicit serializer before claiming coverage');
  const next = new Set(ancestors).add(value);
  if (Array.isArray(value) || ArrayBuffer.isView(value)) return Array.from(value, item => encode(item, next));
  // DOMPoint/DOMMatrix use prototype accessors rather than enumerable own fields.
  const type = value.constructor?.name;
  if (type === 'DOMPoint') return Object.fromEntries(['x','y','z','w'].map(k => [k, encode(value[k], next)]));
  if (type === 'DOMMatrix') return Object.fromEntries(['a','b','c','d','e','f','is2D','isIdentity'].map(k => [k, encode(value[k], next)]));
  if (type === 'ImageData') return { width: value.width, height: value.height, data: encode(value.data, next) };
  return Object.fromEntries(Object.keys(value).sort().map(k => [k, encode(value[k], next)]));
}

/** Decode only the declared test tags; no eval, product-model conversion or external URLs. */
function decode(value, resources) {
  if (Array.isArray(value)) return value.map(item => decode(item, resources));
  if (value && typeof value === 'object') {
    if ('$ref' in value) {
      if (!resources.has(value.$ref)) throw Error(`Unknown resource: ${value.$ref}`);
      return resources.get(value.$ref);
    }
    if ('$undefined' in value) return undefined;
    if ('$number' in value) {
      if (!['NaN', 'Infinity', '-Infinity', '-0'].includes(value.$number)) throw Error('Invalid numeric tag');
      return Number(value.$number);
    }
    if ('$bytes' in value) return Buffer.from(value.$bytes);
    if ('$clamped' in value) return new Uint8ClampedArray(value.$clamped.map(x=>decode(x,resources)));
    if ('$assetBytes' in value) return fs.readFileSync(within(path.join(root,'tests/assets'),value.$assetBytes));
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, decode(v, resources)]));
  }
  return value;
}

/** Apply one fixture operation. An observed API error is data, not a harness failure. */
async function operation(op, api, resources, observations) {
  if(op.ifRef && !resources.has(op.ifRef))return;
  const target = resources.get(op.target);
  const args = decode(op.args || [], resources);
  let value;
  try {
    if (op.target && !resources.has(op.target)) throw Error(`Unknown target: ${op.target}`);
    switch (op.op) {
      case 'set': target[op.name] = decode(op.value, resources); break;
      case 'get': value = target[op.name]; break;
      case 'delete': value = delete target[op.name]; break;
      case 'call': value = await target[op.name](...args); break;
      case 'construct': {
        if (!['Canvas', 'CanvasRenderingContext2D', 'Path2D', 'DOMMatrix', 'DOMPoint', 'DOMRect', 'ImageData', 'CanvasGradient', 'TextMetrics', 'Image', 'CanvasPattern', 'CanvasTexture'].includes(op.class)) throw Error(`Unapproved constructor: ${op.class}`);
        value = new api[op.class](...args);
        break;
      }
      case 'loadImage': {
        const image = within(root, op.path);
        const assets = path.resolve(root, 'tests/assets');
        within(assets, path.relative(assets, image));
        value = await api.loadImage(image);
        break;
      }
      case 'setPixels': target.data.set(op.values); break;
      case 'sameRef': {
        const left = decode(op.left, resources), right = decode(op.right, resources);
        if ((left !== null && typeof left !== 'object') || (right !== null && typeof right !== 'object')) throw Error('sameRef expects objects or null');
        value = left === right;
        break;
      }
      default: throw Error(`Unknown fixture operation: ${op.op}`);
    }
    if (op.observeError) observations[op.observeError] = { threw: false };
  } catch (error) {
    if (!op.observeError) throw error;
    observations[op.observeError] = { threw: true, type: error.name, message: error.message };
    return;
  }
  if (op.id) {
    if (resources.has(op.id)) throw Error(`Duplicate resource: ${op.id}`);
    resources.set(op.id, value);
  }
  if (op.save) observations[op.save] = encode(value);
}

/** Capture original Node outputs only. No Python parity or visual-review verdict is produced. */
async function main() {
  const opts = options(process.argv.slice(2));
  if (!path.isAbsolute(opts.module)) throw Error('--module must be absolute; no dependency search/fallback');
  const moduleDir = fs.realpathSync(opts.module);
  const packageJson = JSON.parse(fs.readFileSync(path.join(moduleDir, 'package.json'), 'utf8'));
  if (packageJson.name !== 'skia-canvas' || packageJson.version !== '3.0.8') throw Error('Oracle must be original skia-canvas@3.0.8');
  const require = createRequire(import.meta.url);
  const api = require(moduleDir);
  const environment = environmentManifest(opts.environment);
  const fixturePath = path.resolve(root, opts.fixtures || 'tests/fixtures/scenarios.json');
  const fixtureBytes = fs.readFileSync(fixturePath);
  const fixtures = JSON.parse(fixtureBytes);
  if (fixtures.schema !== 'py-skia-canvas-fixtures/v1') throw Error('Unsupported fixture schema');
  const selected = opts.case ? new Set(opts.case.split(',')) : null;
  const cases = fixtures.cases.filter(item => !selected || selected.has(item.id));
  if (!cases.length || (selected && selected.size !== cases.length)) throw Error('Empty selection or unknown/duplicate case IDs');
  const runs = path.join(root, 'test-runs');
  fs.mkdirSync(runs, { recursive: true });
  const out = within(runs, path.relative(runs, path.resolve(root, opts.out)));
  fs.mkdirSync(out, { recursive: false }); // EEXIST intentionally prevents evidence overwrite.
  const nativeFiles = Object.keys(require.cache).filter(p => p.endsWith('.node') && p.startsWith(`${moduleDir}${path.sep}`));
  const nativeFingerprints = nativeFiles.map(p => ({ path: path.relative(moduleDir, p), sha256: sha(fs.readFileSync(p)) }));
  const upstreamLock = JSON.parse(fs.readFileSync(path.join(root, 'docs/upstream-lock.json'), 'utf8'));
  if (opts.role === 'node-oracle') {
    const expected = upstreamLock.originalNativeSha256[`${process.platform}-${process.arch}`];
    if (!expected || nativeFingerprints.length !== 1 || nativeFingerprints[0].sha256 !== expected) {
      throw Error('Original native fingerprint is not pinned for this platform; use --role node-rebuild for source builds');
    }
  }
  const report = {
    schema: 'py-skia-canvas-test-run/v1', role: opts.role, status: 'INCOMPLETE',
    createdUtc: new Date().toISOString(), fixtureSha256: sha(fixtureBytes),
    implementation: { name: packageJson.name, version: packageJson.version,
      nativeFiles: nativeFingerprints },
    inputs: { captureScriptSha256: sha(fs.readFileSync(fileURLToPath(import.meta.url))),
      packageJsonSha256: sha(fs.readFileSync(path.join(moduleDir, 'package.json'))),
      upstreamLockSha256: sha(fs.readFileSync(path.join(root, 'docs/upstream-lock.json'))),
      argv: process.argv.slice(2), requireGpu: !!opts.requireGpu },
    environment: { platform: process.platform, arch: process.arch, release: os.release(), host: os.hostname(), node: process.version,
      fontFamiliesSha256: sha(JSON.stringify([...api.FontLibrary.families].sort())),
      fontFilesVerified: !!environment, fontResourcesSha256: environment?.document.fontResourcesSha256 ?? null,
      strict: process.env.SKIA_CANVAS_STRICT ?? null },
    limitations: [environment ? 'Font file contents verified; per-glyph fallback remains unaudited.' : 'Font files and actual fallback glyphs are not fingerprinted.',
      'Engine getters are recorded, not a native call trace.', 'No Python implementation or parity verdict.'], cases: []
  };
  if (environment) {
    fs.writeFileSync(path.join(out, 'environment.json'), environment.bytes, { flag: 'wx' });
    report.environment.manifest = { path: 'environment.json', bytes: environment.bytes.length, sha256: sha(environment.bytes) };
  }
  for (const item of cases) {
    const result = { id: item.id, group: item.group, mode: item.mode, status: 'INCOMPLETE', observations: {} };
    report.cases.push(result);
    try {
      if (!/^[a-z0-9-]+$/.test(item.id)) throw Error('Unsafe case ID');
      const canvas = new api.Canvas(item.width, item.height, item.mode === 'constructor-false' ? { gpu: false } : {});
      if (item.mode === 'cpu-setter') canvas.gpu = false;
      const ctx = canvas.getContext('2d');
      const resources = new Map([['canvas', canvas], ['ctx', ctx], ['fontLibrary', api.FontLibrary], ...['DOMMatrix','DOMPoint','DOMRect','Path2D'].map(k => [k, api[k]])]);
      for (const op of item.ops) await operation(op, api, resources, result.observations);
      result.width = canvas.width;
      result.height = canvas.height;
      const raw = Buffer.from(ctx.getImageData(0, 0, canvas.width, canvas.height).data);
      const png = await canvas.png;
      if(canvas.width%1 || canvas.height%1)result.artifactDimensions={rgba:[Math.floor(canvas.width),Math.floor(canvas.height)],png:[png.readUInt32BE(16),png.readUInt32BE(20)]};
      result.backend = { gpu: canvas.gpu, engine: encode(canvas.engine), evidence: 'public-getters' };
      result.fontPolicy = item.fontPolicy || 'not-requested';
      if (opts.requireGpu && item.mode === 'default' && (!canvas.gpu || canvas.engine.renderer !== 'GPU')) {
        throw Error('GPU required: original library did not report GPU');
      }
      if (opts.requireCpu && (canvas.gpu || canvas.engine.renderer !== 'CPU')) throw Error('CPU required: original library selected GPU');
      result.artifacts = {};
      for (const [kind, data, extension] of [['rgba', raw, 'rgba'], ['png', png, 'png']]) {
        const name = `${item.id}.${extension}`;
        fs.writeFileSync(path.join(out, name), data, { flag: 'wx' });
        result.artifacts[kind] = { path: name, bytes: data.length, sha256: sha(data) };
      }
      result.pixelFormat = 'RGBA8-unpremultiplied-readback';
      result.status = 'CAPTURED';
    } catch (error) {
      result.error = { type: error.name, message: error.message };
    }
  }
  if (report.cases.every(item => item.status === 'CAPTURED')) {
    report.status = opts.role === 'node-oracle' ? 'ORACLE_CAPTURED' : 'CANDIDATE_CAPTURED';
  }
  fs.writeFileSync(path.join(out, 'run.json'), JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
  console.log(JSON.stringify({ status: report.status, cases: cases.length, captured: report.cases.filter(c => c.status === 'CAPTURED').length, report: path.join(out, 'run.json') }));
  if (report.status === 'INCOMPLETE') process.exitCode = 1;
}

main().catch(error => { console.error(error.stack); process.exitCode = 1; });
