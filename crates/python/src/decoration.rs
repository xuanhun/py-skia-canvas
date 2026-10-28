//! Original decoration fields from owned JSON, no Python callbacks/native font handles.
use pyo3::{prelude::*,exceptions::PyTypeError};
use serde_json::Value;
use canvas_core::typography::{DecorationStyle,Spacing,decoration::{DecorationArgs,decoration_style}};

struct Fields(Value);
impl DecorationArgs for Fields {
    type Error=PyErr;
    /// Original string_for_key boundary, unitless owned text or original field TypeError.
    /// Source typography.rs:decoration_arg/utils.rs:string_for_key; any thread, no handles.
    fn string(&mut self,name:&str) -> PyResult<String> {
        self.0[name].as_str().map(str::to_string).ok_or_else(||PyTypeError::new_err(format!("Exptected a string for \"{}\"",name)))
    }
    /// Original optional-object/Spacing::from_obj raw/unit/px read order. Units original
    /// f32 CSS/canvas; f64 finite check before cast, original TypeError on NaN/Infinity.
    /// No callback/Context borrow. Source typography.rs:decoration_arg/Spacing::from_obj.
    fn spacing(&mut self) -> PyResult<Option<Spacing>> {
        let d=&self.0["thickness"];
        if !d.is_object(){return Ok(None);}
        let number=|name:&str|d[name].as_f64().filter(|v|v.is_finite()).map(|v|v as f32).ok_or_else(||PyTypeError::new_err(format!("Exptected a numerical value for \"{}\"",name)));
        let raw_size=number("size")?;
        let unit=d["unit"].as_str().ok_or_else(||PyTypeError::new_err("Exptected a string for \"unit\""))?.to_string();
        let px_size=number("px")?;
        Ok(Spacing::parse(raw_size,unit,px_size))
    }
}

/// Decode original private CSS descriptor, return original style/ignore/field error.
/// JSON carries owned strings/numbers only, NaN tags stay nonnumeric for original
/// finite checks if/when thickness is read. Core controls validation order/early returns;
/// no Context/font/GPU handles or callbacks. Upstream typography.rs:509 decoration_arg.
pub fn decode(text:&str) -> PyResult<Option<DecorationStyle>> {
    let data=serde_json::from_str(text).map_err(|_|PyTypeError::new_err("Invalid internal parsed decoration"))?;
    decoration_style(&mut Fields(data))
}
