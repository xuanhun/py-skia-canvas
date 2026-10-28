//! JS Math compatibility for geometry.js, using pinned original standalone V8 code.
use pyo3::{prelude::*, exceptions::PyNotImplementedError};
extern "C" {
    fn py_canvas_number_string(value:f64,output:*mut std::ffi::c_char,capacity:i32);
    fn py_canvas_dom_sin(x:f64)->f64;
    fn py_canvas_dom_cos(x:f64)->f64;
    fn py_canvas_dom_tan(x:f64)->f64;
    fn py_canvas_dom_atan2(y:f64,x:f64)->f64;
}

/// Original Math sin/cos/tan (radians) or atan2(y,x) (radians); owned f64 result.
/// Stateless on any thread, IEEE NaN/Infinity/-0 retained. Unknown private op raises
/// NotImplementedError. Source: pinned Node v22.23.2 deps/v8/src/base/ieee754.cc.
#[pyfunction]
#[pyo3(signature=(kind,x,y=0.0))]
pub fn _dom_math(kind:&str,x:f64,y:f64)->PyResult<f64> {
    // SAFETY: these exact C ABI functions are compiled by build.rs, operate only on
    // f64 values, have no pointers/callbacks or mutable/GPU state, and return f64.
    unsafe { match kind {
        "sin"=>Ok(py_canvas_dom_sin(x)),"cos"=>Ok(py_canvas_dom_cos(x)),
        "tan"=>Ok(py_canvas_dom_tan(x)),"atan2"=>Ok(py_canvas_dom_atan2(x,y)),
        _=>Err(PyNotImplementedError::new_err(kind.to_string())),
    } }
}

/// Original V8 Number::toString decimal formatting, no units/thread/native ownership.
/// Returns owned ASCII string for any f64, including NaN/Infinity/-0. No user callbacks.
/// Source pinned V8 DoubleToCString/DoubleToAscii; byte-identical dtoa implementation.
#[pyfunction]
pub fn _number_string(value:f64)->String {
    let mut bytes=[0u8;128];
    // SAFETY: C ABI adapter writes at most capacity bytes incl NUL, into this owned
    // 128-byte buffer (all original f64 decimal outputs <32 bytes). No native objects.
    unsafe {py_canvas_number_string(value,bytes.as_mut_ptr().cast(),bytes.len() as i32);}
    let length=bytes.iter().position(|b|*b==0).expect("V8 string NUL");
    String::from_utf8(bytes[..length].to_vec()).expect("V8 ASCII number")
}
