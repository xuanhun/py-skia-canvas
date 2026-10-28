"""Exact installed native original V8 number formatting versus official Node outputs."""
import argparse,hashlib,json,os,struct,sys
from pathlib import Path
def main():
    """Compare every IEEE bit pattern without tolerance, save owned metadata only.
    No units/native objects or graphics; requires installed wheel, empty PATH/outside repo.
    """
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--node',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
    root=Path(__file__).resolve().parents[1]
    if os.environ.get('PATH') or Path.cwd().is_relative_to(root):raise RuntimeError('Require empty PATH and outside workspace')
    from py_skia_canvas import _native
    native=Path(_native.__file__).resolve();assert native.is_relative_to(Path(sys.prefix).resolve())
    inputs=json.loads(a.inputs.read_text(encoding='utf-8'));node=json.loads(a.node.read_text(encoding='utf-8'));differences=[]
    for bits,expected in zip(inputs,node['strings'],strict=True):
        actual=_native._number_string(struct.unpack('>d',bytes.fromhex(bits))[0])
        if actual!=expected:differences.append(dict(bits=bits,node=expected,python=actual))
    d=dict(status='EXACT_NUMBER_STRINGS' if not differences else 'INCOMPLETE',cases=len(inputs),differences=differences,nodeVersion=node['node'],nativeSha256=hashlib.sha256(native.read_bytes()).hexdigest(),inputSha256=hashlib.sha256(a.inputs.read_bytes()).hexdigest())
    (a.out/'run.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(status=d['status'],cases=len(inputs),differences=len(differences))));raise SystemExit(bool(differences))
if __name__=='__main__':main()
