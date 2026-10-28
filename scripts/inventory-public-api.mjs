/** Development-only source inventory; never loads the native module or changes upstream. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from '../tools/api-ledger/node_modules/typescript/lib/typescript.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const upstream = 'references/upstream/skia-canvas-3.0.8';
const native = JSON.parse(fs.readFileSync(path.join(root, 'references/native-api-index.json'), 'utf8'));

/** Parse UTF-8 source into an owned AST, failing on syntax errors (no execution/threads). */
function parse(relative) {
  const source = ts.createSourceFile(relative, fs.readFileSync(path.join(root, relative), 'utf8'),
    ts.ScriptTarget.Latest, true, relative.endsWith('.ts') ? ts.ScriptKind.TS : ts.ScriptKind.JS);
  if (source.parseDiagnostics.length) throw Error(`Cannot parse ${relative}: ${source.parseDiagnostics[0].messageText}`);
  return source;
}

/** Return a one-based, source-relative location; AST nodes remain owned by the parser. */
function location(node, source) {
  return { path: source.fileName, line: source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1 };
}

/** Visit descendants synchronously; callback must not mutate the AST. */
function visit(node, callback) {
  callback(node);
  ts.forEachChild(node, child => visit(child, callback));
}

/** Extract literal member names; private/symbol binding infrastructure is excluded explicitly. */
function memberName(node, source) {
  if (ts.isConstructorDeclaration(node) || ts.isConstructSignatureDeclaration(node)) return 'constructor';
  if (!node.name || ts.isPrivateIdentifier(node.name) || ts.isComputedPropertyName(node.name)) return null;
  return node.name.text ?? node.name.getText(source);
}

/** Expand mutable declaration properties into separate getter/setter contract records. */
function kinds(node) {
  if (ts.isGetAccessorDeclaration(node)) return ['get'];
  if (ts.isSetAccessorDeclaration(node)) return ['set'];
  if (ts.isConstructorDeclaration(node) || ts.isConstructSignatureDeclaration(node)) return ['construct'];
  if (ts.isMethodDeclaration(node) || ts.isMethodSignature(node)) return ['call'];
  return node.modifiers?.some(m => m.kind === ts.SyntaxKind.ReadonlyKeyword) ? ['get'] : ['get', 'set'];
}

/** Index local declarations, including merged interfaces and constructor-valued variables. */
function declarations(source) {
  const types = new Map(), values = new Map(), functions = new Map();
  for (const node of source.statements) {
    if (ts.isInterfaceDeclaration(node) || ts.isClassDeclaration(node)) {
      const name = node.name.text;
      const current = types.get(name) ?? { members: [], bases: [] };
      current.members.push(...node.members);
      for (const clause of node.heritageClauses ?? []) {
        current.bases.push(...clause.types.map(t => t.expression.getText(source)));
      }
      types.set(name, current);
    } else if (ts.isVariableStatement(node)) {
      for (const declaration of node.declarationList.declarations) {
        if (declaration.type && ts.isTypeLiteralNode(declaration.type)) values.set(declaration.name.text, declaration.type.members);
      }
    } else if (ts.isFunctionDeclaration(node)) {
      const list = functions.get(node.name.text) ?? [];
      list.push(node);
      functions.set(node.name.text, list);
    }
  }
  return { types, values, functions };
}

/** Resolve local inheritance without importing browser or Node ambient declarations. */
function inherited(name, types, ancestors = new Set()) {
  if (ancestors.has(name)) throw Error(`Cyclic declaration inheritance: ${name}`);
  const declaration = types.get(name);
  if (!declaration) return [];
  const own = new Set(declaration.members.map(node => memberName(node)));
  const next = new Set(ancestors).add(name);
  return [...declaration.bases.flatMap(base => inherited(base, types, next)).filter(node => !own.has(memberName(node))),
    ...declaration.members];
}

/** Collect exact JS defaults, explicit throws, and direct Neon routes, without inferring algorithms. */
function jsContract(node, source, owner, kind) {
  const routes = new Set(), throws = [];
  visit(node, child => {
    if (ts.isThrowStatement(child)) throws.push({ ...location(child, source), expression: child.expression.getText(source) });
    if (!ts.isCallExpression(child) || !ts.isPropertyAccessExpression(child.expression)) return;
    const name = child.expression.name.text, first = child.arguments[0];
    if (name === 'alloc') routes.add(`${owner}_new`);
    if (!first || !ts.isStringLiteral(first)) return;
    if (name === 'ƒ' || name === 'init') routes.add(`${owner}_${first.text}`);
    if (name === 'prop') routes.add(`${owner}_${child.arguments.length > 1 ? 'set' : 'get'}_${first.text}`);
  });
  return {
    parameters: (node.parameters ?? []).map(p => ({ name: p.name.getText(source),
      defaultExpression: p.initializer?.getText(source) ?? null, rest: !!p.dotDotDotToken })),
    explicitThrows: throws,
    nativeSources: native.nativeExports.filter(entry => routes.has(entry.name)),
  };
}

/** Build an overload/accessor inventory. Unreviewed semantic fields stay pending, never pass. */
export function buildLedger() {
  const declarationSource = parse(`${upstream}/lib/index.d.ts`);
  const { types, values, functions } = declarations(declarationSource);
  const jsClasses = new Map(), jsFunctions = new Map();
  const files = fs.readdirSync(path.join(root, upstream, 'lib/classes')).filter(name => name.endsWith('.js')).sort();
  for (const file of files) {
    const source = parse(`${upstream}/lib/classes/${file}`);
    for (const node of source.statements) {
      if (ts.isClassDeclaration(node)) jsClasses.set(node.name.text, { node, source });
      if (ts.isFunctionDeclaration(node)) jsFunctions.set(node.name.text, { node, source });
      if (ts.isVariableStatement(node)) for (const declaration of node.declarationList.declarations) {
        if (declaration.initializer && (ts.isArrowFunction(declaration.initializer) || ts.isFunctionExpression(declaration.initializer))) {
          jsFunctions.set(declaration.name.text, { node: declaration.initializer, source });
        }
      }
    }
  }
  const entries = [];
  for (const owner of native.publicExports) {
    const records = new Map();
    function add(name, kind, scope, node, source, origin) {
      if (!name || name === 'prototype') return;
      const key = `${scope}:${name}:${kind}`;
      const record = records.get(key) ?? { owner, name, kind, scope, declarations: [], javascript: [] };
      record[origin].push({ ...location(node, source), signature: node.getText(source).split(/\s*\{/)[0].trim(),
        ...(origin === 'javascript' ? jsContract(node, source, owner, kind) : { signature: node.getText(source).trim() }) });
      records.set(key, record);
    }
    for (const node of inherited(owner, types)) {
      const scope = node.modifiers?.some(m => m.kind === ts.SyntaxKind.StaticKeyword) ? 'static' : 'instance';
      for (const kind of kinds(node)) add(memberName(node, declarationSource), kind, scope, node, declarationSource, 'declarations');
    }
    for (const node of values.get(owner) ?? []) {
      for (const kind of kinds(node)) add(memberName(node, declarationSource), kind, kind === 'construct' ? 'instance' : 'static', node, declarationSource, 'declarations');
    }
    for (const node of functions.get(owner) ?? []) add(owner, 'call', 'module', node, declarationSource, 'declarations');
    const implementation = jsClasses.get(owner);
    if (implementation) for (const node of implementation.node.members) {
      const scope = node.modifiers?.some(m => m.kind === ts.SyntaxKind.StaticKeyword) ? 'static' : 'instance';
      for (const kind of kinds(node)) add(memberName(node, implementation.source), kind, scope, node, implementation.source, 'javascript');
    }
    const fn = jsFunctions.get(owner);
    if (fn) add(owner, 'call', 'module', fn.node, fn.source, 'javascript');
    if (!records.size) throw Error(`Unaccounted public export: ${owner}`);
    for (const record of records.values()) {
      const overloads = record.declarations.length || 1;
      for (let i = 0; i < overloads; i++) {
        const declaration = record.declarations[i] ?? null;
        entries.push({ id: `${owner}.${record.scope}.${record.name}.${record.kind}.${i + 1}`,
          owner, name: record.name, kind: record.kind, scope: record.scope, overload: i + 1,
          declaration, javascript: record.javascript,
          availability: !declaration ? 'javascript-only' : record.javascript.length ? 'both' : 'declaration-only-or-instance-data',
          feature: ['App', 'Window'].includes(owner) ? 'window' : 'headless',
          languageBoundary: /Sharp/.test(record.name) ? 'node-sharp-review-required' : /^(App|Window|Image)$/.test(owner) ? 'events-and-ownership-review-required' : 'adapter-required',
          coreMethod: null, pythonEntry: null, scenarioIds: [], status: 'inventoried',
          contractAudit: 'pending', units: null, returnSemantics: null, ownershipAndThreads: null, evidence: [] });
      }
    }
  }
  // Code-point ordering is independent of the host's ICU/locale version.
  entries.sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
  return { schema: 'py-skia-canvas-public-api-ledger/v1', commit: native.commit, parser: `typescript@${ts.version}`,
    scope: 'Source inventory, not semantic review or a supported Python API.',
    limitations: ['Declaration-only members can be instance data or absent at runtime; review required.',
      'Inherited Node EventEmitter methods and dynamic instance fields require a separate host-contract audit.',
      'Direct native routes only; delegated routes, defaults inside function bodies, units and ownership remain pending.'],
    exports: native.publicExports.map(name => ({ name, entries: entries.filter(e => e.owner === name).length,
      kind: ['App', 'FontLibrary'].includes(name) ? 'singleton' : functions.has(name) ? 'function' : 'class' })), entries };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  if (args.length > 1 || args.length && args[0] !== '--check') throw Error('Usage: node scripts/inventory-public-api.mjs [--check]');
  const ledger = buildLedger();
  const text = JSON.stringify(ledger, null, 2) + '\n';
  const destination = path.join(root, 'docs/public-api-ledger.json');
  if (args[0] === '--check') {
    if (fs.readFileSync(destination, 'utf8') !== text) throw Error('Public API ledger is stale; review before regeneration');
  } else fs.writeFileSync(destination, text);
  console.log(JSON.stringify({ status: 'API_INVENTORIED', exports: ledger.exports.length, entries: ledger.entries.length,
    semanticAudit: 'pending', path: 'docs/public-api-ledger.json' }));
}
