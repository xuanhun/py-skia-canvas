//! Path2D language adapter; all geometry and effects live in the unique core.
use pyo3::{prelude::*, exceptions::{PyTypeError, PyNotImplementedError}};
use canvas_core::{path::{Path2D, operations as ops}, utils};
use serde_json::json;
use crate::{ownership::NativePath, RangeError, Error};

#[pymethods]
impl NativePath {
    /// Check original path owner without serializing or changing geometry; None/RuntimeError.
    /// Binding-only metadata guard before public primitive argument reads, no GPU transfer.
    fn check_owner(&self)->PyResult<()>{self.with(|_|Ok(()))}
    /// Construct original default/SVG/copied path on this thread; canvas-unit geometry.
    /// Invalid SVG constructor retains original empty path; ownership/ID errors propagate.
    /// No Python references or Skia data in handle. Source: path.rs:new/from_svg/from_path.
    #[new]
    #[pyo3(signature = (svg=None, source=None))]
    fn new(svg:Option<String>, source:Option<PyRef<'_, NativePath>>) -> PyResult<Self> {
        let path=if let Some(source)=source { source.with(|p| Ok(ops::from_path(p)))? }
                 else if let Some(svg)=svg { ops::from_svg(svg) } else { ops::new() };
        Self::create(path)
    }

    /// Get/set original SVG d; owned string, unitless text; invalid setter -> original TypeError.
    /// Owner-only; no callbacks while borrowed. Source: path.rs:get_d/set_d.
    #[pyo3(signature = (value=None))]
    fn svg(&self, value:Option<String>) -> PyResult<String> {
        self.with(|p| {
            if let Some(value)=value { ops::set_d(p,value).map_err(PyTypeError::new_err)?; }
            Ok(ops::get_d(p))
        })
    }

    /// Return owned original edges/bounds JSON; coordinates in canvas units, weights unitless.
    /// Owner-only, unknown private kind ->NotImplementedError. Source: path.rs:edges/bounds.
    fn data(&self, kind:&str) -> PyResult<String> {
        self.with(|p| match kind {
            "edges" => Ok(serde_json::to_string(&ops::edges(p)).unwrap()),
            "bounds" => { let b=ops::bounds(p); Ok(json!({"left":ops::number_token(b.left),"top":ops::number_token(b.top),"right":ops::number_token(b.right),"bottom":ops::number_token(b.bottom),"width":ops::number_token(b.width()),"height":ops::number_token(b.height())}).to_string()) }
            _ => Err(PyNotImplementedError::new_err(kind.to_string())),
        })
    }

    /// Apply original path primitive; fixed-arity f32 canvas units/radians and original bool flag.
    /// Returns None; ellipse radius ->RangeError(ValueError), owner-only. Source: path.rs primitives.
    fn command(&self, name:&str, values:Vec<f32>, ccw:bool) -> PyResult<()> {
        let arity=match name { "closePath"=>0,"moveTo"|"lineTo"=>2,"rect"|"quadraticCurveTo"=>4,"arc"|"arcTo"|"conicCurveTo"=>5,"bezierCurveTo"=>6,"ellipse"=>7,"roundRect"=>12,_=>return Err(PyNotImplementedError::new_err(name.to_string())) };
        if values.len()!=arity { return Err(PyTypeError::new_err("Invalid internal path argument count")); }
        self.with(|p| {
            match name {
                "closePath"=>ops::closePath(p),"moveTo"=>ops::moveTo(p,values),"lineTo"=>ops::lineTo(p,values),
                "rect"=>ops::rect(p,values),"arc"=>ops::arc(p,values,ccw),"arcTo"=>ops::arcTo(p,values),
                "roundRect"=>ops::roundRect(p,values),
                "bezierCurveTo"=>ops::bezierCurveTo(p,values),"quadraticCurveTo"=>ops::quadraticCurveTo(p,values),
                "conicCurveTo"=>ops::conicCurveTo(p,values),"ellipse"=>ops::ellipse(p,values,ccw).map_err(RangeError::new_err)?,
                _=>unreachable!(),
            }
            Ok(())
        })
    }

    /// Original path contains() at f32 canvas-unit coordinates; bool result, owner-only.
    /// No new errors/geometry policy. Source: path.rs:contains.
    fn contains(&self, x:f32, y:f32) -> PyResult<bool> { self.with(|p| Ok(ops::contains(p,x,y))) }

    /// Append original same-thread path with Skia row-order matrix; returns None.
    /// Coordinates canvas units; invalid filtered matrix defaults to original identity;
    /// foreign path ->RuntimeError. Facade constructor errors occur before this entry.
    /// Source: path.rs:addPath; self-add clones before mutable borrow as original.
    fn add(&self, other:&NativePath, matrix:Vec<f32>) -> PyResult<()> {
        let source=other.snapshot()?;
        let matrix=utils::to_matrix(&matrix).unwrap_or_else(skia_safe::Matrix::new_identity);
        self.with(|p| { ops::addPath(&mut p.path,&source,&matrix); Ok(()) })
    }

    /// Return original boolean/interpolated path; weight unitless, geometry canvas units.
    /// Original boolean errors ->Error(RuntimeError), mismatch ->TypeError; owner-only snapshots.
    /// Source: path.rs:op/interpolate, including original reversed interpolation order.
    fn combine(&self, other:&NativePath, operation:&str, weight:f32) -> PyResult<Self> {
        let other=Path2D { path:other.snapshot()? };
        let value=self.with(|p| {
            if operation=="interpolate" { ops::interpolate(p,&other,weight).map_err(PyTypeError::new_err) }
            else { ops::op(p,&other,operation).map_err(Error::new_err) }
        })?;
        Self::create(value)
    }

    /// Return original path effect; lengths canvas units, trim fractions/seed unitless.
    /// Preserves original mutation/fallback rules; owner-only, no GPU transfer. Rule errors
    /// ->TypeError. Source: path.rs:simplify/unwind/round/trim/jitter/offset/transform.
    fn effect(&self, name:&str, values:Vec<f32>, flag:bool, rule:String) -> PyResult<Self> {
        let arity=match name {"simplify"|"unwind"=>0,"round"=>1,"offset"|"trim"=>2,"jitter"=>3,"transform"=>values.len(),_=>return Err(PyNotImplementedError::new_err(name.to_string()))};
        if values.len()!=arity { return Err(PyTypeError::new_err("Invalid internal effect argument count")); }
        let matrix = if name=="transform" { Some(utils::to_matrix(&values).ok_or_else(|| PyTypeError::new_err("Expected a DOMMatrix"))?) } else { None };
        let value=self.with(|p| match name {
            "simplify"=> { let error="Expected `fillRule` to be \"nonzero\" or \"evenodd\" for 1st arg".to_string(); Ok(ops::simplify(p,utils::fill_rule(&rule,&error).map_err(PyTypeError::new_err)?)) }
            "unwind"=>Ok(ops::unwind(p)),"round"=>Ok(ops::round(p,values[0])),
            "offset"=>Ok(ops::offset(p,values[0],values[1])),"trim"=>Ok(ops::trim(p,values[0],values[1],flag)),
            "jitter"=>Ok(ops::jitter(p,values[0],values[1],values[2] as u32)),
            "transform"=>Ok(ops::transform(p,matrix.as_ref().unwrap())),
            _=>unreachable!(),
        })?;
        Self::create(value)
    }
}
