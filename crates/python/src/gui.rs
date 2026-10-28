//! Python GUI boundary; original App/WindowManager/Renderer stay in optional shared core.
use pyo3::{prelude::*,exceptions::{PyRuntimeError,PyTypeError}};
use crate::{Error,ownership::NativeCanvas};

/// Check OS event-loop owner before native callbacks/borrows. No units/return or GPU refs;
/// Python threading identity only, rejects foreign threads with RuntimeError. winit main-thread
/// restriction; no thread pool or context movement. Applies even to direct private calls.
fn owner(py:Python<'_>)->PyResult<()>{
    let threading=py.import("threading")?;
    if threading.call_method0("get_ident")?.extract::<u64>()? != threading.call_method0("main_thread")?.getattr("ident")?.extract::<u64>()?{
        return Err(PyRuntimeError::new_err("App and Window must be used on the main thread"));
    }Ok(())
}

/// Original compiled-window support flag; no initialization/units/native objects, any thread.
/// Source gui.js:checkSupport; false means actual feature absence, never a fake window.
#[pyfunction]
fn _gui_support()->bool{cfg!(feature="window")}

#[cfg(feature="window")]
mod enabled{
    use super::*;
    use std::cell::Cell;
    use canvas_core::{gui::{app::{App,LoopMode},window::WindowSpec,window_mgr::WindowManager},gpu::RenderingEngine};
    thread_local!{static DISPATCHING:Cell<bool>=const{Cell::new(false)};}

    /// Original support guard: selected engine must support platform windows; returns Error
    /// before event-loop creation. No units/native transfer; source gui/mod.rs:validate_gpu.
    fn supported()->PyResult<()>{
        if let Some(reason)=RenderingEngine::default().lacks_gpu_support(){return Err(Error::new_err(reason));}Ok(())
    }

    /// Original openWindow receives JSON WindowSpec and owner fixed-page snapshot, returns
    /// None/Error. Logical pixel spec, Page canvas units; no owner GPU context is sent.
    /// Source gui/mod.rs:open; original App::open_window/proxy remains sole implementation.
    #[pyfunction]
    pub fn _gui_open(py:Python<'_>,spec:&str,page:&NativeCanvas)->PyResult<()>{
        owner(py)?;let spec:WindowSpec=serde_json::from_str(spec).map_err(|e|PyTypeError::new_err(format!("Invalid window state: {e}")))?;
        if spec.width<=0.0 || spec.height<=0.0{return Err(pyo3::exceptions::PyNotImplementedError::new_err("Non-positive Window dimensions remain an unsafe upstream GUI profile"));}
        let page=page.with(|e|Ok(e.context().get_page()))?;supported()?;App::open_window(spec,page);Ok(())
    }
    /// Queue original u32 window token close; no units/return, main-thread RuntimeError.
    /// Source gui/mod.rs:close original f32-as-u32 token boundary, callback safe via proxy.
    #[pyfunction]
    pub fn _gui_close(py:Python<'_>,token:f32)->PyResult<()>{owner(py)?;App::close_window(token as u32);Ok(())}

    /// Original loop mode setting; unitless native/node string ->same string/Error.
    /// Owner only, source gui/mod.rs:set_mode. Public facade freezes after first launch.
    #[pyfunction]
    pub fn _gui_mode(py:Python<'_>,mode:&str)->PyResult<String>{owner(py)?;App::set_mode(match mode{"native"=>LoopMode::Native,"node"=>LoopMode::Node,_=>return Err(Error::new_err(format!("Invalid event loop mode: {mode}")))});Ok(mode.to_owned())}

    /// Original frames/sec f32 ->f32 and queued u64 cadence, None not substituted.
    /// Main-thread only, no native refs; source gui/mod.rs:set_rate/App::set_fps.
    #[pyfunction]
    pub fn _gui_rate(py:Python<'_>,fps:f32)->PyResult<f32>{owner(py)?;App::set_fps(fps);Ok(fps)}

    /// Original quit outside native callback; no units/return, owner errors. Reentrant
    /// quit is rejected before original RefCell panic (explicit G0 unsupported profile).
    /// Source gui/mod.rs:quit/App::quit; window.close is callback-safe as original.
    #[pyfunction]
    pub fn _gui_quit(py:Python<'_>)->PyResult<()>{owner(py)?;if DISPATCHING.with(Cell::get){return Err(PyRuntimeError::new_err("Reentrant App.quit is unsupported; close windows from their callbacks"));}App::quit();Ok(())}

    /// Run original native event loop or one original node pump; callback maps JSON and
    /// owner metadata handles to original WindowSpec/Page updates. Returns keep-running bool,
    /// main-thread/type errors; original core ignores dispatch errors as upstream. No TLS
    /// App borrow is stored in Python; callback can access owner Canvas safely. GIL is
    /// released only while executing native work on this same OS thread, reacquired for
    /// each callback; the unbound callback reference is metadata, not a GUI/GPU object.
    /// Source app.rs:activate/dispatch_events; zip/update ordering retained exactly.
    #[pyfunction]
    pub fn _gui_step(py:Python<'_>,callback:&Bound<'_,PyAny>)->PyResult<bool>{
        owner(py)?;supported()?;
        let callback=callback.clone().unbind();
        py.detach(move||App::activate(|events,windows:Option<&mut WindowManager>|->PyResult<()>{Python::attach(|py|{
            struct InCallback(bool);
            impl Drop for InCallback{fn drop(&mut self){DISPATCHING.with(|v|v.set(self.0));}}
            let _scope=InCallback(DISPATCHING.with(|v|v.replace(true)));
            let response=callback.bind(py).call1((windows.is_some(),events.to_string()))?;
            if let Some(windows)=windows{
                let (specs,handles):(String,Vec<Py<NativeCanvas>>)=response.extract()?;
                let specs:Vec<WindowSpec>=serde_json::from_str(&specs).map_err(|e|Error::new_err(format!("Malformed response from window event handler: {e}")))?;
                let pages=handles.iter().map(|h|h.borrow(py).with(|e|Ok(e.context().get_page()))).collect::<PyResult<Vec<_>>>()?;
                std::iter::zip(specs,pages).for_each(|(spec,page)|windows.update_window(spec,page));
            }Ok(())
        })}))
    }
}

/// Register actual optional GUI functions, no event-loop/device creation at import.
/// Returns PyO3 registration errors, any importing thread; source gui/mod.rs exports.
pub fn register(module:&Bound<'_,PyModule>)->PyResult<()>{
    module.add_function(wrap_pyfunction!(_gui_support,module)?)?;
    #[cfg(feature="window")]{
        module.add_function(wrap_pyfunction!(enabled::_gui_open,module)?)?;
        module.add_function(wrap_pyfunction!(enabled::_gui_close,module)?)?;
        module.add_function(wrap_pyfunction!(enabled::_gui_mode,module)?)?;
        module.add_function(wrap_pyfunction!(enabled::_gui_rate,module)?)?;
        module.add_function(wrap_pyfunction!(enabled::_gui_quit,module)?)?;
        module.add_function(wrap_pyfunction!(enabled::_gui_step,module)?)?;
    }Ok(())
}
