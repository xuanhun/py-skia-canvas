//! Language-only export boundary. Original snapshots/options/codec dispatch stay in core.
use std::{sync::{Mutex,mpsc,atomic::{AtomicUsize,Ordering}},thread};
use canvas_core::{canvas::{exports,options::{ExportArgs,export_options_arg}},context::page::{ExportOptions,PageSequence},utils};
use pyo3::{prelude::*,exceptions::PyTypeError,types::PyBytes};
use serde_json::{Value,json};
use crate::{ownership::{NativeCanvas,arm_gpu_cleanup},Error};
static JOBS:AtomicUsize=AtomicUsize::new(0);
struct Fields(Value);
impl ExportArgs for Fields {
    type Error=PyErr;
    fn string(&mut self,k:&str)->PyResult<String>{self.0[k].as_str().map(str::to_owned).ok_or_else(||PyTypeError::new_err(format!("Expected a string for \"{k}\"")))}
    fn flag(&mut self,k:&str)->PyResult<bool>{self.0[k].as_bool().ok_or_else(||PyTypeError::new_err(format!("Expected a boolean for \"{k}\"")))}
    fn number(&mut self,k:&str)->PyResult<f32>{self.optional_number(k).ok_or_else(||PyTypeError::new_err(format!("Exptected a numerical value for \"{k}\"")))}
    fn optional_number(&mut self,k:&str)->Option<f32>{self.0[k].as_f64().filter(|v|v.is_finite()).map(|v|v as f32)}
    fn optional_string(&mut self,k:&str)->Option<String>{self.0[k].as_str().map(str::to_owned)}
    fn color(&mut self,k:&str)->Option<skia_safe::Color>{self.0[k].as_str().and_then(utils::css_to_color)}
}
/// Decode normalized JS-facing fields, quality fraction/density scale/MSAA samples,
/// returning original options/TypeError. Owned primitives only; no owner borrow/callback.
/// Source utils.rs:export_options_arg; field packing is generated original core code.
fn options(text:&str)->PyResult<ExportOptions>{
    let v=serde_json::from_str(text).map_err(|_|PyTypeError::new_err("Invalid internal export options"))?;
    export_options_arg(&mut Fields(v))
}
/// Snapshot selected fixed-page handles on their owners in chronological order.
/// No coordinate changes, returns original PageSequence/owner errors. Original pages_arg;
/// materialize is performed on owner before async transfer, matching canvas.rs:toBuffer/save.
fn prepare(root:&NativeCanvas,handles:Vec<PyRef<'_,NativeCanvas>>,opts:&ExportOptions,asynchronous:bool)->PyResult<(PageSequence,Value)>{
    let engine=root.with(|e|{let engine=e.canvas.engine();arm_gpu_cleanup(engine);Ok(engine)})?;
    let mut pages=Vec::with_capacity(handles.len());
    for h in handles{pages.push(h.with(|e|Ok(e.context().get_page_for_export(opts,&engine)))?);}
    if pages.is_empty(){return Err(PyTypeError::new_err("No valid canvas pages selected"));}
    let mut pages=PageSequence::from(pages,engine);
    let before=canvas_core::context::page::audit::selected(&pages,opts);
    if asynchronous{pages.materialize(&engine,opts);}
    let after=canvas_core::context::page::audit::selected(&pages,opts);
    Ok((pages,json!({"cachedImagesBefore":before.0,"cachedTexturesBefore":before.1,"cachedImagesAfter":after.0,"cachedTexturesAfter":after.1})))
}
/// Encode/write immediately on owner; bytes or None, original Error on codec/I/O failure.
/// Paths and sequence digit padding are native strings/f32, all rendering units original.
/// Source canvas.rs:toBufferSync/saveSync; no asynchronous materialize policy added.
pub fn synchronous<'py>(root:&NativeCanvas,py:Python<'py>,pages:Vec<PyRef<'_,NativeCanvas>>,text:&str,file:Option<String>,padding:f32,sequence:bool)->PyResult<Option<Bound<'py,PyBytes>>>{
    let opts=options(text)?;let (pages,_)=prepare(root,pages,&opts,false)?;
    if let Some(file)=file{exports::write(&pages,&file,padding,sequence,opts).map_err(Error::new_err)?;Ok(None)}
    else{Ok(Some(PyBytes::new(py,&exports::encode(&pages,opts).map_err(Error::new_err)?)))}
}
struct Completed{result:Result<Option<Vec<u8>>,String>,worker:String}
#[pyclass(frozen,module="py_skia_canvas._native")]
pub struct NativeExportTask{receiver:Mutex<mpsc::Receiver<Completed>>,owner:String,audit:Value}
/// Start original Rayon export after owner snapshot/materialize. Returns ID-free task;
/// task contains channel metadata only, no Canvas/Context/GPU objects. Original PageSequence
/// and options must satisfy compiler Send; no unsafe impl. File errors retain async prefix.
pub fn start(root:&NativeCanvas,pages:Vec<PyRef<'_,NativeCanvas>>,text:&str,file:Option<String>,padding:f32,sequence:bool)->PyResult<NativeExportTask>{
    let opts=options(text)?;let (pages,audit)=prepare(root,pages,&opts,true)?;
    let (sender,receiver)=mpsc::channel();let owner=format!("{:?}",thread::current().id());
    JOBS.fetch_add(1,Ordering::SeqCst);
    rayon::spawn_fifo(move||{
        let result=if let Some(file)=file{exports::write(&pages,&file,padding,sequence,opts).map(|_|None).map_err(|e|format!("I/O Error: {e}"))}
            else{exports::encode(&pages,opts).map(Some)};
        let _=sender.send(Completed{result,worker:format!("{:?}",thread::current().id())});
        JOBS.fetch_sub(1,Ordering::SeqCst);
    });
    Ok(NativeExportTask{receiver:Mutex::new(receiver),owner,audit})
}
#[pymethods]
impl NativeExportTask{
    /// Nonblocking completed-result read; (ready,bytes,error,audit JSON). Unitless status,
    /// owned bytes only, any Python thread/loop; disconnection ->Error. Python caches result
    /// for repeated await. No worker calls Python or accesses original owner's native data.
    fn poll<'py>(&self,py:Python<'py>)->PyResult<(bool,Option<Bound<'py,PyBytes>>,Option<String>,String)>{
        match self.receiver.lock().unwrap_or_else(|e|e.into_inner()).try_recv(){
            Ok(done)=>{let mut audit=self.audit.clone();audit["owner"]=json!(self.owner);audit["worker"]=json!(done.worker);audit["materializedOnOwner"]=json!(true);let audit=audit.to_string();
                Ok(match done.result{Ok(b)=>(true,b.map(|b|PyBytes::new(py,&b)),None,audit),Err(e)=>(true,None,Some(e),audit)})},
            Err(mpsc::TryRecvError::Empty)=>Ok((false,None,None,String::new())),
            Err(mpsc::TryRecvError::Disconnected)=>Err(Error::new_err("Export worker disconnected")),
        }
    }
}
/// Current native export jobs, diagnostic count/no units/handles, any thread, no errors.
#[pyfunction]
pub fn _debug_export_jobs()->usize{JOBS.load(Ordering::SeqCst)}
