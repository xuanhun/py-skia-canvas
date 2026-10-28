"""Verify locked original tokenizer sources and retained derivative notices, no runtime JS."""
import hashlib,json
from pathlib import Path

def validate(root):
    """Return source/license errors; paths unitless, files read only, no threads/native objects.

    Source: references/css/source.json; parser algorithm behavior checked separately against Node.
    """
    errors=[];data=json.loads((root/'references/css/source.json').read_text(encoding='utf-8'))
    for item in data['files']:
        if hashlib.sha256((root/item['path']).read_bytes()).hexdigest()!=item['sha256']:errors.append('Tokenizer source changed: '+item['path'])
    original=(root/'references/css/parenthesis/LICENSE').read_text(encoding='utf-8')
    for name,text in [('parenthesis',original),('string-split-by',original.replace('Copyright © 2016 Dmitry Ivanov','Copyright © 2018 Dmitry Yv'))]:
        if (root/f'crates/python/vendor/css/LICENSE-{name}.txt').read_text(encoding='utf-8')!=text:errors.append('Tokenizer license changed: '+name)
    return {'errors':errors,'scope':'Original sources/notices only; parser/runtime/render evidence separate'}
