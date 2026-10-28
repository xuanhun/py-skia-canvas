"""Check original standalone V8 math source, provenance and no runtime integration."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]

def validate(root=ROOT):
    """Return source-check errors; filesystem text only, no arithmetic/rendering/native objects.

    Pinned upstream files must remain byte-identical in frozen source and working copy.
    """
    frozen=root/'references/math/node-v22.23.2';vendor=root/'crates/python/vendor/v8'
    manifest=json.loads((frozen/'source.json').read_text(encoding='utf-8'));errors=[]
    if manifest['nodeCommit']!='aa4c77582be995286fc6e00aaf530dc7ade102a9': errors.append('V8 math source commit changed')
    for item in manifest['files']:
        source=frozen/item['path'];target=vendor/('src/base/'+item['path'] if item['path']!='LICENSE' else 'LICENSE')
        data=source.read_bytes()
        if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']: errors.append('Pinned V8 math source changed: '+item['path'])
        if target.read_bytes()!=data: errors.append('Working V8 math source changed: '+item['path'])
    flags=(root/'crates/python/build.rs').read_text(encoding='utf-8')
    if '-ffp-contract=off' not in flags or '-fno-fast-math' not in flags: errors.append('V8 math FP flags missing')
    return {'status':'MATRIX_MATH_SOURCE_CHECKED' if not errors else 'INCOMPLETE','errors':errors}

if __name__=='__main__':
    result=validate();print(json.dumps(result,indent=2));raise SystemExit(bool(result['errors']))
