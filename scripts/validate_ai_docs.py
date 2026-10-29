"""Check AI documentation links, Python syntax, versions and demo fixture structure.

This is a source/documentation check, not rendering or release acceptance. It
loads no native module, creates no Canvas and changes no source/evidence files.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import struct
import tomllib
from urllib.parse import unquote, urlsplit

from validate_bootstrap import validate_fixtures

ROOT = Path(__file__).resolve().parents[1]


def check(root: Path = ROOT) -> dict:
    """Return structural status/errors; all paths are local, no GPU/thread ownership."""
    errors = []
    base = root / 'docs/ai'
    facts = json.loads((base / 'facts.json').read_text(encoding='utf-8'))
    project = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))
    tree = ast.parse((root / 'python/py_skia_canvas/__init__.py').read_text(encoding='utf-8'))
    exports = []
    version = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == '__version__':
                    version = ast.literal_eval(node.value)
                if isinstance(target, ast.Name) and target.id == '__all__':
                    exports = ast.literal_eval(node.value)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == '__all__':
            exports += ast.literal_eval(node.value)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == '__all__' and call.func.attr == 'append':
                exports.append(ast.literal_eval(call.args[0]))
    if facts.get('schema') != 'py-skia-canvas-ai-docs/v1':
        errors.append('Unsupported AI facts schema')
    if not (facts.get('version') == project['project']['version'] == version):
        errors.append('AI facts, pyproject and Python versions differ')
    if set(facts.get('publicExports', [])) != set(exports) or len(facts['publicExports']) != len(exports):
        errors.append('AI facts public exports differ from package __all__')

    paths = [*facts['routes'].values(), facts['acceptedWheels']['releaseStatus'], facts['host']['profile'],
             facts['examples']['script'], facts['examples']['developmentFixture'], facts['examples']['assetsManifest'],
             facts['development']['instructions'], *facts['development']['requiredFirstReads'],
             facts['development']['uniqueCore'], facts['development']['sourceMap'], facts['development']['readOnlyUpstream']]
    for target in paths:
        if not (base / target).exists():
            errors.append(f'AI facts missing path: {target}')

    files = [*sorted(base.rglob('*.md')), root / 'examples/README.md', root / 'README.md']
    fences = links = 0
    for path in files:
        source = path.read_text(encoding='utf-8')
        inside = False
        language = ''
        block = []
        first_line = 0
        for number, line in enumerate(source.splitlines(), 1):
            match = re.match(r'^```(\w*)\s*$', line)
            if match:
                if not inside:
                    inside = True
                    language = match[1]
                    block = []
                    first_line = number + 1
                else:
                    if language == 'python':
                        fences += 1
                        try:
                            compile('\n'.join(block), str(path), 'exec')
                        except SyntaxError as error:
                            errors.append(f'{path.relative_to(root)}:{first_line}: invalid Python: {error}')
                    inside = False
                continue
            if inside:
                block.append(line)
                continue
            for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)', line):
                target = match[1].strip().strip('<>')
                if urlsplit(target).scheme or target.startswith('#'):
                    continue
                filename = unquote(target.split('#', 1)[0])
                if not filename:
                    continue
                links += 1
                if not (path.parent / filename).exists():
                    errors.append(f'{path.relative_to(root)}:{number}: missing link: {target}')
        if inside:
            errors.append(f'{path.relative_to(root)}: unclosed code fence')
    demo = root / 'examples/ai_demos.py'
    compile(demo.read_text(encoding='utf-8'), str(demo), 'exec')
    fixture = root / 'examples/development/parity-smoke.json'
    document = json.loads(fixture.read_text(encoding='utf-8'))
    errors += [f'{fixture.relative_to(root)}: {error}' for error in validate_fixtures(document, root)]
    manifest_path = base / facts['examples']['assetsManifest']
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema') != 'py-skia-canvas-demo-assets/v1' or manifest.get('version') != version:
        errors.append('Demo image manifest schema/version differs')
    if manifest.get('demoSourceSha256') != hashlib.sha256(demo.read_bytes()).hexdigest():
        errors.append('Demo script changed since embedded images were generated; review/recreate affected images and provenance')
    images = manifest['images']
    if {item['demo'] for item in images} != set(facts['examples']['offscreen']) | {facts['examples']['window']}:
        errors.append('Embedded images do not cover the documented demo set')
    seen = set()
    for item in images:
        path = (manifest_path.parent / item['path']).resolve()
        if path in seen or not path.is_relative_to(manifest_path.parent.resolve()) or not path.is_file():
            errors.append(f'Invalid/duplicate/missing demo image: {item["path"]}')
            continue
        seen.add(path)
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != item['sha256'] or len(payload) != item['bytes']:
            errors.append(f'Demo image SHA/size differs: {item["path"]}')
        if not payload.startswith(b'\x89PNG\r\n\x1a\n') or list(struct.unpack('>II', payload[16:24])) != item['pixels']:
            errors.append(f'Demo PNG signature/dimensions differ: {item["path"]}')
        gallery = (base / 'usage/DEMOS.md').read_text(encoding='utf-8')
        if f'../assets/{item["path"]}' not in gallery:
            errors.append(f'Demo image not embedded in gallery: {item["path"]}')
    return dict(status='AI_DOCS_STRUCTURALLY_VALIDATED' if not errors else 'INCOMPLETE',
                markdownFiles=len(files), localLinks=links, pythonBlocks=fences,
                publicExports=len(exports), developmentFixtureCases=len(document['cases']),
                demoImages=len(images),
                errors=errors, limitation='No renderer, upstream parity, visual or release acceptance is implied.')


def main():
    """Print check result; optional fresh JSON evidence path, nonzero on failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.out is not None and args.out.exists():
        parser.error('--out exists; choose a fresh evidence path')
    result = check()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open('x', encoding='utf-8') as stream:
            stream.write(payload)
    print(payload, end='')
    raise SystemExit(0 if not result['errors'] else 1)


if __name__ == '__main__':
    main()
