"""Deterministic language separation of original 3.0.8 GUI; no window/render policy rewrite."""
import re

def documented(text,filename,origin=None):
    """Add source/ownership/unit docs only; original Rust statements retained byte-for-byte.
    Pure text ->text, missing/malformed source raises in subsequent source guards.
    """
    purpose={'new':'Construct original native window/event sieve','id':'Read original native window identity','resize':'Apply original physical pixel resize','reposition':'Record original logical pixel position','update_fit':'Apply original inverse fit to input coordinates','fitting_matrix':'Calculate original page-to-window fit matrix','redraw':'Render original page through original platform swapchain','redraw_if_resized':'Request original delayed vector redraw','get_ui_changes':'Collect original UI events and window state','get_geometry':'Collect original logical pixel window origins','capture':'Capture original winit event and input conversion','collect':'Drain original serialized UI events','next_wakeup':'Calculate original cadence deadline','on_next_frame':'Apply original frame scheduling and callback cadence'}
    lines=text.splitlines(keepends=True);out=[];locations={};seen={}
    for i,line in enumerate((origin or text).splitlines()):
        m=re.match(r'\s*(?:pub )?fn (\w+)',line)
        if m:locations.setdefault(m[1],[]).append(i+1)
    for i,line in enumerate(lines):
        m=re.match(r'(\s*)(?:pub )?fn (\w+)',line)
        if m:
            indent,name=m.groups();index=seen.get(name,0);seen[name]=index+1
            if filename=='app.rs' and name=='activate':out.append(line);continue
            location=locations.get(name,[i+1])[index]
            out.extend([indent+'/// '+purpose.get(name,'Execute original '+name+' window/event operation')+'; original arguments and return type retained.\n',indent+'/// Geometry uses original logical/physical pixels, Page uses canvas units, timing uses original durations.\n',indent+'/// Owner event-loop thread only; original errors/panics/callback order retained, no native objects transferred.\n',indent+f'/// Upstream src/gui/{filename}:{location}, skia-canvas 3.0.8; body retained.\n'])
        out.append(line)
    return ''.join(out)

def core_app(source,bodies):
    """Separate Neon scheduling/callback reads from original App event loop and cadence.
    Text only; original event handler body, FPS, native/node pump policy remain intact.
    """
    text=source.replace('use neon::prelude::*;\n','').replace('sync::{Arc, OnceLock},\n','').replace('use crate::context::{page::Page, BoxedContext2D};','use crate::context::page::Page;')
    text=text.replace('static RENDER_CALLBACK: OnceLock<Arc<Root<JsFunction>>> = OnceLock::new();\n','')
    for name in ('register','dispatch_events'):text=text.replace(bodies(text,name)[0]['text'],'')
    old=bodies(text,'activate')[0]['text'];body=bodies(source,'activate')[0]['body'];a=body.index('                    APP.with_borrow_mut');b=body.index('\n                }).join();',a)
    block=body[a:b]
    text=text.replace(old,'''    /// Run original owner event loop/pump once; callback receives original event JSON and
    /// optional mutable manager. Returns original keep-running bool or adapter error E.
    /// No Neon scheduling in core, no GPU/context movement. Source app.rs:activate inner callback.
    pub fn activate<F,E>(dispatch:F)->Result<bool,E>
        where F:FnMut(Value,Option<&mut WindowManager>)->Result<(),E>
    {
'''+block+'''
    }
''')
    text=text.replace('fn event_handler<F>','fn event_handler<F,E>').replace("+ use<'_, F>","+ use<'_, F,E>").replace('-> NeonResult<()>','-> Result<(),E>')
    # The preceding allow(deprecated) originally applied to activate; preserve it.
    return documented(text,'app.rs',source)

def node_app(source,bodies):
    """Node keeps original channel/Promise/Root boundary and delegates sole core loop.
    Text source output; callback decoding and original dispatch_events body preserved.
    """
    reg=bodies(source,'register')[0]['text'];dispatch=bodies(source,'dispatch_events')[0]['text'];activate=bodies(source,'activate')[0]['text']
    body=bodies(source,'activate')[0]['body'];a=body.index('                    APP.with_borrow_mut');b=body.index('\n                }).join();',a)
    activate=activate.replace(body[a:b],'                    canvas_core::gui::app::App::activate(dispatch)')
    forwards=''
    for name,params,args in [('set_mode','mode:LoopMode','mode'),('set_fps','fps:f32','fps'),('open_window','spec:WindowSpec, page:Page','spec,page'),('close_window','token:u32','token'),('quit','','')]:
        forwards+=f'    /// Forward original {name}; same units/errors, owner loop only, no native transfer.\n    pub fn {name}({params}){{canvas_core::gui::app::App::{name}({args})}}\n'
    return '''//! Node-only callback/channel adapter; all native window/event/render algorithms in core.
use neon::prelude::*;
use serde_json::Value;
use std::{sync::{Arc,OnceLock},iter::zip};
use crate::context::{page::Page,BoxedContext2D};
use super::{window_mgr::WindowManager,window::WindowSpec};
pub use canvas_core::gui::app::LoopMode;
static RENDER_CALLBACK:OnceLock<Arc<Root<JsFunction>>>=OnceLock::new();
pub struct App;
impl App{
'''+reg+forwards+activate+dispatch+'}\n'
