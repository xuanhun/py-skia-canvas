"""Guard byte-identical pinned V8 dtoa and original decimal formatting, no rendering."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def validate(root=ROOT):
    """Check pinned source hashes and standalone adapter's original format block.
    Returns owned errors, no units/GPU/threads/network; file errors propagate.
    Source Node22.23.2 aa4c775 V8 base/numbers and conversions.cc.
    """
    ref=root/'references/math/node-v22.23.2/numbers';dest=root/'crates/python/vendor/v8-numbers';errors=[]
    data=json.loads((ref/'source.json').read_text(encoding='utf-8'))
    for entry in data['files']:
        source=ref/entry['path']
        if hashlib.sha256(source.read_bytes()).hexdigest()!=entry['sha256']:errors.append('Pinned V8 number source changed: '+entry['path'])
        if entry['path'].startswith('src/base/numbers/') and source.read_bytes()!=(dest/entry['path']).read_bytes():errors.append('Working V8 dtoa source changed: '+entry['path'])
    source=(ref/'src/numbers/conversions.cc').read_text(encoding='utf-8');start=source.index('const char* DoubleToCString(');end=source.index('char* DoubleToFixedCString(',start)
    if source[start:end] not in (dest/'format.cpp').read_text(encoding='utf-8'):errors.append('Original V8 decimal format block changed')
    if (dest/'LICENSE').read_bytes()!=(root/'crates/python/vendor/v8/LICENSE').read_bytes():errors.append('V8 number license changed')
    return errors
if __name__=='__main__':
    errors=validate();print(json.dumps(dict(status='NUMBER_SOURCE_CHECKED',errors=errors)));raise SystemExit(bool(errors))
