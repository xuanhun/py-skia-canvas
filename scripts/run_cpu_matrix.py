"""Run the declared exact CPU/no-driver matrix on installed release wheels and official A."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path

def main():
    """Read explicit development paths, capture fresh evidence and fail on any mismatch.

    Supports a native target or Windows-to-WSL transport. Sizes in pixels/bytes;
    no native objects in the controller. Child Vulkan driver discovery is isolated
    with official loader environment variables, never system/registry modification.
    Production package/default GPU policy is not changed. Parameters: config JSON,
    fresh output directory. Returns process success or raises on failed capture.
    """
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[1];out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);cfg=json.loads(a.config.read_text(encoding='utf-8'));checks=[];differences=[];journal=(out/'commands.ndjson').open('x',encoding='utf-8')
    wheel_path=root/cfg['wheel'][len(cfg['root'])+1:];wheel_sha=hashlib.sha256(wheel_path.read_bytes()).hexdigest()
    def remote(path):return cfg['root']+'/'+path.resolve().relative_to(root).as_posix()
    def run(name,args,role=None,strict=False,required=True):
        args=list(map(str,args));env=os.environ.copy();cwd=root
        if role:
            values={'VK_DRIVER_FILES':cfg['blockedDriver'],'VK_ICD_FILENAMES':cfg['blockedDriver'],'VK_LOADER_DRIVERS_DISABLE':'*'}
            if role=='python':values['PATH']=''
            if strict:values['SKIA_CANVAS_STRICT']='1'
            if cfg['transport']=='wsl':args=['wsl','--cd',cfg['cwd'] if role=='python' else cfg['root'],'-e','env','-u','SKIA_CANVAS_STRICT',*[k+'='+v for k,v in values.items()],*args]
            else:env.pop('SKIA_CANVAS_STRICT',None);env.update(values);cwd=cfg['cwd'] if role=='python' else root
        with (out/(name+'.log')).open('xb') as f:result=subprocess.run(args,env=env,cwd=cwd,stdout=f,stderr=subprocess.STDOUT)
        entry=dict(name=name,argv=args,exitCode=result.returncode);checks.append(entry);journal.write(json.dumps(entry)+'\n');journal.flush();print(name,result.returncode,flush=True)
        if required and result.returncode:raise RuntimeError(name)
        return result.returncode
    try:
        for strict,names in ((False,cfg['ordinary']),(True,cfg['strict'])):
            for name in names:
                tag=name+('-strict' if strict else '');fixture=root/'tests/fixtures'/(name+'.json')
                if cfg.get('mappedFixtures') and (root/cfg['mappedFixtures']/(name+'.json')).exists():fixture=root/cfg['mappedFixtures']/(name+'.json')
                original=out/(tag+'-original');candidate=out/(tag+'-python');common=['--fixtures',remote(fixture),'--environment',cfg['environment']]
                run(tag+'-original',[cfg['node'],cfg['root']+'/tests/oracle/capture-node.mjs','--module',cfg['module'],*common,'--out',remote(original),'--require-cpu'],'original',strict)
                run(tag+'-python',[cfg['python'],'-I',cfg['root']+'/scripts/capture_python.py',*common,'--wheel',cfg['wheel'],'--backend','cpu','--out',remote(candidate)],'python',strict)
                if run(tag+'-compare',[sys.executable,root/'scripts/compare_runs.py',original,candidate,'--out',out/(tag+'-comparison.json')],required=False):differences.append(tag)
        for strict in (False,True):
            tag='exports'+('-strict' if strict else '');original=out/(tag+'-original');candidate=out/(tag+'-python')
            run(tag+'-original',[cfg['node'],cfg['root']+'/tests/oracle/capture-exports.mjs',cfg['module'],cfg['root']+'/tests/fixtures/exports.json',remote(original),'cpu'],'original',strict)
            run(tag+'-python',[cfg['python'],'-I',cfg['root']+'/scripts/capture_exports.py',cfg['root']+'/tests/fixtures/exports.json',remote(candidate),'cpu'],'python',strict)
            if run(tag+'-compare',[sys.executable,root/'scripts/compare_exports.py',original,candidate,'--out',out/(tag+'-comparison'),'--pdf-tools',root/'.local/export-tools','--audit-modules',root/'.local/export-audit-python'],required=False):differences.append(tag)
        for name in ('font-fallback','draw-fonts'):
            fixture=root/'tests/fixtures'/(name+'.json')
            if cfg.get('mappedFixtures'):fixture=root/cfg['mappedFixtures']/(name+'.json')
            run('actual-draw-'+name,[cfg['python'],'-I',cfg['root']+'/scripts/audit_draw_sources.py','--fixtures',remote(fixture),'--environment',cfg['environment'],'--backend','cpu','--out',remote(out/('actual-draw-'+name))],'python',required=False)
        status='CPU_MATRIX_EXACT' if not differences and not any(c['exitCode'] for c in checks) else 'DIFFERENT_RECORDS'
    except Exception as e:status='INCOMPLETE';raise
    finally:
        journal.close();(out/'run.json').write_text(json.dumps(dict(status=status,checks=checks,differences=differences,config=cfg,wheelSha256=wheel_sha,scope='No-driver automatic CPU fallback; exact official A comparison. Default GPU acceptance retained separately.'),indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
