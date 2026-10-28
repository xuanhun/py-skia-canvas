"""Verify a reviewed release manifest and exactly the wheel bytes it names."""
import argparse,hashlib,json,zipfile
from pathlib import Path


def verify(directory, manifest_sha256):
    """Return reviewed manifest or raise on any missing/replaced/unaccepted artifact.

    Paths are bundle-relative, sizes are bytes; no network or native code loading.
    Caller must supply the reviewed manifest SHA independently. GPU evidence must
    already be accepted, never inferred from GitHub Actions build success.
    """
    raw=(directory/'release-manifest.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest_sha256:raise ValueError('Manifest SHA mismatch')
    d=json.loads(raw)
    if d['status']!='LOCAL_GPU_ACCEPTED':raise ValueError('Bundle not locally GPU accepted')
    for platform in ('windows','linux'):
        if d['platforms'][platform]['status']!='ACCEPTED':raise ValueError('Missing platform acceptance')
    expected=set()
    for row in d['wheels']:
        path=(directory/row['file']).resolve()
        if path.parent!=directory.resolve() or path.suffix!='.whl':raise ValueError('Invalid wheel path')
        allowed={f"py_skia_canvas-{d['version']}-cp313-cp313-{tag}.whl" for tag in ('win_amd64','manylinux_2_28_x86_64')}
        if path.name not in allowed:raise ValueError('Unsupported wheel version/ABI/platform')
        data=path.read_bytes();expected.add(path.name)
        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Wheel SHA mismatch')
        with zipfile.ZipFile(path) as z:
            metadata=z.read(f"py_skia_canvas-{d['version']}.dist-info/METADATA").decode()
            if '\nName: py-skia-canvas\n' not in metadata or f"\nVersion: {d['version']}\n" not in metadata:raise ValueError('Wheel metadata version/name mismatch')
            if any(n.lower().endswith(('.node','.ttf','.otf','.ttc','.js','.mjs')) or 'node_modules/' in n or '/references/' in n for n in z.namelist()):raise ValueError('Development/font payload in wheel')
    if {p.name for p in directory.glob('*.whl')}!=expected:raise ValueError('Unexpected wheel in bundle')
    if d.get('sourceDistribution'):
        row=d['sourceDistribution'];path=directory/row['file']
        if path.name!=f"py_skia_canvas-{d['version']}.tar.gz":raise ValueError('Unexpected source archive')
        data=path.read_bytes()
        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Source archive SHA mismatch')
    return d


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--manifest-sha256',required=True);a=p.parse_args();d=verify(a.directory,a.manifest_sha256);print(json.dumps(dict(status='EXACT_REVIEWED_WHEELS',version=d['version'],wheels=len(d['wheels']))))
