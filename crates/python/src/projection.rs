//! Projection boundary only: original number parsing/filtering and unique core solver.
use pyo3::{prelude::*, exceptions::PyTypeError, types::{PyBool,PyFloat,PyInt,PyString,PyList,PyTuple}};
use skia_safe::Point;
use crate::ownership::NativeCanvas;
use canvas_core::{utils,context::operations};

/// Original _as_double primitive/array branch for Python values, returning finite f64/None.
/// Unitless; Rust string grammar is the same core helper as Node. Numeric casts/length
/// access do not call user coercion methods. Used outside owner registry borrows.
/// Source: utils.rs:_as_double; tuple aliases the same JS Array boundary implementation.
pub(crate) fn number(value:&Bound<'_,PyAny>) -> Option<f64> {
    let parsed=if value.is_instance_of::<PyFloat>() || value.is_instance_of::<PyInt>() || value.is_instance_of::<PyBool>() {
        value.extract::<f64>().ok()
    } else if let Ok(text)=value.cast::<PyString>() {
        utils::parse_number_string(&text.to_string_lossy())
    } else if value.is_none() { Some(0.0) }
    else if let Ok(list)=value.cast::<PyList>() {
        match list.len() {0=>Some(0.0),1=>list.get_item(0).ok().and_then(|v|number(&v)),_=>None}
    } else if let Ok(list)=value.cast::<PyTuple>() {
        match list.len() {0=>Some(0.0),1=>list.get_item(0).ok().and_then(|v|number(&v)),_=>None}
    } else { None };
    parsed.filter(|v|v.is_finite())
}

/// Original floats_in finite-f64 filtering, then f32 cast/even-pair validation.
/// Returns original Point list in canvas units or original TypeError; no Context borrow.
/// Source: utils.rs:points_arg/_as_float/floats_in. Does not reject f32 overflow after cast.
fn points(values:&Bound<'_,PyList>,which:&str) -> PyResult<Vec<Point>> {
    let nums:Vec<f32>=values.iter().filter_map(|v|number(&v).map(|n|n as f32)).collect();
    if nums.len()%2==1 {
        Err(PyTypeError::new_err(format!("Lists of x/y points must have an even number of values (got {} in {} argument)",nums.len(),which)))
    } else { Ok(nums.chunks_exact(2).map(|pair|Point::new(pair[0],pair[1])).collect()) }
}

/// Original createProjection typed language boundary; input lists represent [arg].flat().
/// Returns owned 9-f32 Skia matrix terms (coefficients unitless, translation canvas units).
/// Owner-only; first-argument error before second, original TypeError/owner RuntimeError.
/// No Python callbacks while Context borrowed; source: context.js/createProjection and API.
pub fn projection(this:&NativeCanvas,quad:&Bound<'_,PyAny>,basis:&Bound<'_,PyAny>) -> PyResult<Vec<f32>> {
    this.with(|_|Ok(()))?;
    let dst=points(quad.cast::<PyList>()?,"first")?;
    let src=points(basis.cast::<PyList>()?,"second")?;
    this.with(|entry| {
        let matrix=operations::createProjection(entry.context(),dst,src).map_err(PyTypeError::new_err)?;
        Ok((0..9).map(|i|matrix[i]).collect())
    })
}
