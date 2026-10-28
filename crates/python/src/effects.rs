//! Owned original CSS descriptor reader only; unique core packs FilterSpec and applies effects.
use pyo3::{prelude::*,exceptions::PyTypeError};
use serde_json::Value;
use canvas_core::{filter::{FilterSpec,arguments::{FilterArgs,filter_arg}},utils};

struct Fields { data:Value }
impl FilterArgs for Fields {
    type Error=PyErr;
    /// Original canonical string field ->owned String/TypeError. Unitless, no native refs.
    fn canonical(&mut self)->PyResult<String>{self.data["canonical"].as_str().map(str::to_string).ok_or_else(||PyTypeError::new_err("Exptected a string for \"canonical\""))}
    /// Return original first-insertion filter order from transport array; source JSON map
    /// sorting cannot reorder filters. Unitless strings, malformed private fields TypeError.
    fn names(&mut self)->PyResult<Vec<String>>{
        self.data["order"].as_array().ok_or_else(||PyTypeError::new_err("Invalid internal filter order"))?.iter().map(|v|v.as_str().map(str::to_string).ok_or_else(||PyTypeError::new_err("Invalid internal filter name"))).collect()
    }
    /// Read original numeric values as f32 with finite-f64 filtering and color-string order.
    /// CSS/canvas lengths; owned data only. Private malformed descriptors TypeError.
    fn shadow(&mut self,name:&str)->PyResult<(Vec<f32>,String)>{
        let list=self.data["filters"][name].as_array().ok_or_else(||PyTypeError::new_err("Invalid internal drop-shadow"))?;
        let dims=list.iter().filter_map(|v|v.as_f64().filter(|n|n.is_finite()).map(|n|n as f32).or_else(||v.as_str().and_then(utils::parse_number_string).filter(|n|n.is_finite()).map(|n|n as f32))).collect::<Vec<_>>();
        let color=list.get(3).and_then(Value::as_str).ok_or_else(||PyTypeError::new_err("Invalid internal drop-shadow color"))?.to_string();
        if dims.len()<3{return Err(PyTypeError::new_err("Invalid internal drop-shadow dimensions"));}
        Ok((dims,color))
    }
    /// Original JsNumber value-as-f32; no color/layout math. Unitless/degree/CSS input,
    /// returns f32 or private malformed TypeError, before Context borrow.
    fn number(&mut self,name:&str)->PyResult<f32>{self.data["filters"][name].as_f64().map(|n|n as f32).ok_or_else(||PyTypeError::new_err("Invalid internal plain filter value"))}
}

/// Decode owned transport with explicit insertion order then use original core packing.
/// Returns owned canonical/specs or original field TypeError; units as FilterArgs docs.
/// No native handles/callbacks cross this boundary. Source utils.rs:filter_arg.
pub fn decode(text:&str)->PyResult<(String,Vec<FilterSpec>)>{
    let data=serde_json::from_str(text).map_err(|_|PyTypeError::new_err("Invalid internal parsed filter"))?;
    filter_arg(&mut Fields{data})
}
