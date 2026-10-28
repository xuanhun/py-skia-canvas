//! Language-only gradient adapter; original ramp, epsilon sorting and shader stay in core.
use pyo3::{prelude::*, exceptions::PyTypeError};
use canvas_core::{gradient::CanvasGradient, utils::css_to_color};
use skia_safe::Point;
use crate::{ownership::NativeGradient, RangeError};

#[pymethods]
impl NativeGradient {
    /// Create original linear/radial/conic shared ramp; coordinates/radii f32 canvas units,
    /// conic angle radians. Returns owner-local handle; private invalid arity/style ->TypeError.
    /// Source: gradient.rs:linear/radial/conic. No context capture, renderer or validation rewrite.
    #[new]
    fn new(kind:&str, values:Vec<f32>) -> PyResult<Self> {
        let arity=match kind {"linear"=>4,"radial"=>6,"conic"=>3,_=>return Err(PyTypeError::new_err("Invalid gradient style"))};
        if values.len()!=arity { return Err(PyTypeError::new_err("Invalid internal gradient argument count")); }
        let gradient=match kind {
            "linear"=>CanvasGradient::linear(Point::new(values[0],values[1]),Point::new(values[2],values[3])),
            "radial"=>CanvasGradient::radial(Point::new(values[0],values[1]),values[2],Point::new(values[3],values[4]),values[5]),
            "conic"=>CanvasGradient::conic(values[0],Point::new(values[1],values[2])),
            _=>unreachable!(),
        };
        Self::create(gradient)
    }

    /// Add original normalized f32 offset and CSS packed color; returns None, owner-only.
    /// Offset validation precedes color parsing. Original RangeError/TypeError text retained;
    /// sorting/duplicate stops/Rc mutation are core methods. Source: gradient.rs:addColorStop.
    #[pyo3(signature = (offset, color, provided))]
    fn stop(&self, offset:f32, color:Option<&str>, provided:bool) -> PyResult<()> {
        self.with(|g| {
            CanvasGradient::validate_offset(offset).map_err(RangeError::new_err)?;
            let color=color.and_then(css_to_color).ok_or_else(|| PyTypeError::new_err(if provided {"Could not be parsed as a color"} else {"not enough arguments"}))?;
            g.add_color_stop(offset,color);
            Ok(())
        })
    }

    /// Return original style label as owned string; unitless, owner-only, no ramp clone/data move.
    /// Source: gradient.rs:repr. Unknown private operation is not used as a renderer fallback.
    fn kind(&self) -> PyResult<String> { self.with(|g| Ok(g.repr().to_string())) }
}
