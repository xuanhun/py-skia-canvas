"""Compare real installed wheel scalar f64 math against independently captured Node bits."""
import argparse,json,struct,math,sys,os,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    """Read numeric audit inputs and write fresh evidence; fail on any bit difference.

    Development only, no units beyond radian inputs; stateless _dom_math any thread.
    Requires installed extension, outside-workspace cwd and empty PATH.
    """
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--node',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    from py_skia_canvas import _native
    if os.environ.get('PATH') or Path.cwd().is_relative_to(ROOT) or not Path(_native.__file__).is_relative_to(Path(sys.prefix)):p.error('Use actual installed wheel outside workspace with empty PATH')
    out=a.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'test-runs'):p.error('Use fresh test-runs directory')
    xs=json.loads(a.inputs.read_text());expected=json.loads(a.node.read_text())
    rows=[]
    for x in xs:
        x*=math.pi/180
        rows.append([struct.pack('<d',_native._dom_math(n,x)).hex() for n in ('sin','cos','tan')]+[struct.pack('<d',_native._dom_math('atan2',x,.37)).hex()])
    differences=[{'input':xs[i],'operation':name,'node':expected[i][j],'python':row[j]} for i,row in enumerate(rows) for j,name in enumerate(('sin','cos','tan','atan2')) if expected[i][j]!=row[j]]
    out.mkdir();(out/'bits.json').write_text(json.dumps(rows)+'\n')
    report={'status':'MATCHED_SCALAR_BITS' if not differences else 'DIFFERENT_OR_INCOMPLETE','samples':len(xs),'comparisons':len(xs)*4,'differences':differences,'nativeSha256':hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest(),'inputsSha256':hashlib.sha256(a.inputs.read_bytes()).hexdigest(),'nodeSha256':hashlib.sha256(a.node.read_bytes()).hexdigest(),'limitations':['Finite audit set, not proof over all IEEE values','Scalar compatibility evidence, separate from exact matrix/pixel/trace checks']}
    (out/'run.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'samples':len(xs),'differences':len(differences)}));raise SystemExit(bool(differences))

if __name__=='__main__':main()
