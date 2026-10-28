"""Check original skia-bindings0.88 crate and Linux-only original static-link build patch."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def validate(root=ROOT):
    """Return source/patch errors; no build/runtime/GPU claim or external input execution.
    Source original crate SHA and upstream skia-canvas static-fontconfig patch.
    """
    ref=root/'references/rust-skia-static';d=json.loads((ref/'source.json').read_text(encoding='utf-8'));dest=root/'crates/skia-bindings';errors=[];changed={'build_support/binaries_config.rs','build_support/platform/linux.rs'}
    for row in d['files']:
        if row['path'] not in changed and hashlib.sha256((dest/row['path']).read_bytes()).hexdigest()!=row['sha256']:errors.append('Original vendored Skia binding source changed: '+row['path'])
    source=(ref/'build_support/binaries_config.rs').read_text(encoding='utf-8');working=(dest/'build_support/binaries_config.rs').read_text(encoding='utf-8');a=working.index('        // Original skia-canvas static-fontconfig');b=working.index('\n        cargo::add_static_link_libs(&target, self.built_libraries',a)
    if working[:a]+working[b:]!=source:errors.append('Static library ordering patch exceeds original upstream scope')
    source=(ref/'build_support/platform/linux.rs').read_text(encoding='utf-8');working=(dest/'build_support/platform/linux.rs').read_text(encoding='utf-8');a=source.index('    // Use pkg-config for system libraries');b=source.index('\n    if features[feature::GL]',a);block=source[a:b]
    expected=source[:a]+'''    // Original static patch omits these shared links; embedded Skia FreeType
    // resolves Fontconfig references. Keep ordinary developer builds unchanged.
    if std::env::var_os("SKIA_STATIC_FONTCONFIG_DIR").is_none() {
'''+''.join('    '+line+'\n' for line in block.splitlines())+'    }\n'+source[b:]
    if working!=expected:errors.append('Static system library patch exceeds original upstream scope')
    return errors
if __name__=='__main__':
    errors=validate();print(json.dumps(dict(status='STATIC_SKIA_SOURCE_CHECKED',errors=errors)));raise SystemExit(bool(errors))
