//! Original primitive numeric boundary and Canvas option reader; no drawing algorithms.
use pyo3::prelude::*;
use canvas_core::canvas::construction::{CanvasArgs,OptionsError};

pub struct CanvasFields<'a,'py>{pub contrast:&'a Bound<'py,PyAny>,pub gamma:&'a Bound<'py,PyAny>,pub gpu:bool}
impl CanvasArgs for CanvasFields<'_, '_>{
    type Error=PyErr;
    /// Original finite f64 conversion, unitless settings, no owner borrow/callback policy.
    fn number(&mut self,key:&str)->Option<f64>{crate::projection::number(if key=="textContrast"{self.contrast}else{self.gamma})}
    /// Read already normalized public GPU truth value, bool/no units/error, no native refs.
    fn flag(&mut self)->PyResult<bool>{Ok(self.gpu)}
}
/// Map original construction validation errors, no units/native objects or callbacks.
/// Source canvas.rs:new range checks, shared construction factory preserves order/typo.
pub fn error(e:OptionsError<PyErr>)->PyErr{match e{OptionsError::Range(e)=>crate::RangeError::new_err(e),OptionsError::Field(e)=>e}}

/// Original finite f64 primitive/string/array conversion before the original f32 cast.
/// Returns owned number/None; no owner affinity, native handles, custom host callbacks.
/// Source utils.rs:_as_double. Used by constructor/options and argument validation.
#[pyfunction]
pub fn _argument_double(value:&Bound<'_,PyAny>)->Option<f64>{crate::projection::number(value)}
