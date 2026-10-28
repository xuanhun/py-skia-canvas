"""Independent actual installed-wheel platform window/swapchain trace; no CPU substitutes."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path

def main():
    """Capture GDB renderer/surface/present stacks, assert GPU hits and CPU zero, fresh evidence."""
    from py_skia_canvas import _native
    root=Path(__file__).resolve().parents[1];out=Path(sys.argv[1]);assert not out.exists();out.mkdir();native=Path(_native.__file__);assert native.is_relative_to(Path(sys.prefix))
    shutil.copyfile(root/'tests/native/python_gui_scene.py',out/'scene.py');shutil.copyfile(root/'tests/native/gui.gdb',out/'commands.gdb')
    cmd=['/usr/bin/gdb','-nx','-batch','-x',str(out/'commands.gdb'),'--args',sys.executable,'-I',str(out/'scene.py')]
    with (out/'trace.log').open('xb') as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=60)
    log=(out/'trace.log').read_text();render=log.split('TRACE_GUI_PRESENT_BEGIN',1)[1].split('TRACE_GUI_PRESENT_END',1)[0];control=log.split('TRACE_GUI_CPU_CONTROL_BEGIN',1)[1].split('TRACE_GUI_CPU_CONTROL_END',1)[0]
    markers={'draw':'NATIVE_GUI_RENDERER_DRAW_HIT','surface':'NATIVE_GUI_FRAMEBUFFER_SURFACE_HIT','present':'NATIVE_GUI_PRESENT_HIT'};hits={k:render.count(v) for k,v in markers.items()};cpu={k:control.count(v) for k,v in markers.items()};okay=p.returncode==0 and 'exited normally' in log and all(hits.values()) and not any(cpu.values())
    d=dict(status='NATIVE_GUI_VULKAN_PRESENT_OBSERVED' if okay else 'INCOMPLETE',argv=cmd,exitCode=p.returncode,nativeSha256=hashlib.sha256(native.read_bytes()).hexdigest(),gui=hits,freshCpuControl=cpu,traceSha256=hashlib.sha256((out/'trace.log').read_bytes()).hexdigest(),limits=['Skia/Vulkano present call stacks, not driver vkQueuePresentKHR entry','WSLg software Vulkan, not native Windows/Metal/hardware GPU acceptance'])
    (out/'run.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d));sys.exit(not okay)

if __name__=='__main__':main()
