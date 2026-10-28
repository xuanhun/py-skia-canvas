"""Create a locked Python source archive, preserving every runtime dependency pin."""
import argparse,hashlib,json,subprocess,sys,tarfile,tempfile,tomllib
from pathlib import Path


def build(out):
    """Produce sdist and provenance; raise if packaging changes any retained pin.

    Paths have no units; fresh output required. Maturin 1.9.6 rewrites workspace
    members but retains Node development lock entries. Reconcile only that temp
    archive's lock offline, then prove both supported Python dependency trees equal
    the workspace's trees. No source mutation, native loading or GPU transfer.
    """
    root=Path(__file__).resolve().parents[1];out.mkdir(parents=True,exist_ok=False)
    def run(args,cwd):
        p=subprocess.run(args,cwd=cwd,capture_output=True)
        if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
        return p.stdout
    def lock(path):return {(x['name'],x['version']):x for x in tomllib.loads(path.read_text(encoding='utf-8'))['package']}
    with tempfile.TemporaryDirectory(prefix='canvas-sdist-') as tmp:
        tmp=Path(tmp);raw=tmp/'raw';run([sys.executable,'-m','maturin','sdist','--out',str(raw)],root);archive=next(raw.glob('*.tar.gz'))
        with tarfile.open(archive) as t:t.extractall(tmp/'source',filter='data')
        source=next((tmp/'source').iterdir());materialized=[]
        # Materialize source bytes explicitly. Some WSL/DrvFS cargo-package copies
        # of small untracked headers contain NULs despite the source reading correctly.
        # Keep only Maturin's workspace projection/PKG-INFO, never accept altered code.
        for path in sorted(source.rglob('*')):
            relative=path.relative_to(source);original=root/relative
            if path.is_file() and original.is_file() and relative.as_posix() not in ('Cargo.toml','Cargo.lock','PKG-INFO'):
                raw_bytes=original.read_bytes()
                if path.read_bytes()!=raw_bytes:materialized.append(relative.as_posix())
                path.write_bytes(raw_bytes)
        before=lock(root/'Cargo.lock');run(['cargo','metadata','--offline','--format-version','1'],source);after=lock(source/'Cargo.lock')
        pin=lambda value:{k:value.get(k) for k in ('name','version','source','checksum')}
        changed=[key for key,value in after.items() if key not in before or pin(before[key])!=pin(value)]
        if changed:raise ValueError('Packaging changed retained dependency pins: '+repr(changed))
        trees={}
        for target in ('x86_64-unknown-linux-gnu','x86_64-pc-windows-msvc'):
            for edges in ('normal,build','features'):
                args=['cargo','tree','--offline','--locked','-p','py-skia-canvas-native','--target',target,'--edges',edges,'--prefix','none']
                original=run(args,root).replace(str(root).encode(),b'<source>');projected=run(args,source).replace(str(source).encode(),b'<source>')
                if original!=projected:raise ValueError('Python dependency tree changed for '+target+' '+edges)
                trees[target+' '+edges]=hashlib.sha256(original).hexdigest()
        provenance=dict(schema='py-skia-canvas-sdist-projection/v1',sourceLockSha256=hashlib.sha256((root/'Cargo.lock').read_bytes()).hexdigest(),projectedLockSha256=hashlib.sha256((source/'Cargo.lock').read_bytes()).hexdigest(),removedDevelopmentPackages=[list(k) for k in before if k not in after],retainedPackages=len(after),exactPythonDependencyTrees=trees,materializedOriginalSourceBytes=materialized)
        (source/'SDIST-SOURCE.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8');result=out/archive.name
        with tarfile.open(result,'w:gz',format=tarfile.PAX_FORMAT) as t:t.add(source,arcname=source.name)
        provenance.update(status='LOCKED_SDIST_CHECKED',archive=result.name,sha256=hashlib.sha256(result.read_bytes()).hexdigest(),bytes=result.stat().st_size);(out/'run.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8');print(json.dumps(provenance))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.out.resolve())
