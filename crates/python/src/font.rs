//! Parsed font value adapter; original FontSpec packing and selection live in core.
use canvas_core::typography::{font_spec,FontSpec};
use pyo3::{prelude::*,exceptions::PyTypeError};
use serde_json::Value;

/// Convert private parsed JSON fields to original native f32 boundary and FontSpec.
/// Units: size/leading CSS px, weight numeric, other fields strings/features. Returns
/// None for empty first family. Invalid private descriptors ->TypeError. No callbacks,
/// native handles or thread affinity; call before borrowing owner Context.
/// Upstream: typography.rs:font_arg/font_features, css.js:parseFont small-caps features.
pub fn decode(text:&str) -> PyResult<Option<FontSpec>> {
    let invalid=||PyTypeError::new_err("Invalid internal parsed font descriptor");
    let d:Value=serde_json::from_str(text).map_err(|_|invalid())?;
    let string=|key:&str|d[key].as_str().map(str::to_string).ok_or_else(invalid);
    let families=d["family"].as_array().ok_or_else(invalid)?.iter().map(|v|v.as_str().map(str::to_string).ok_or_else(invalid)).collect::<PyResult<Vec<_>>>()?;
    if families.is_empty(){return Err(invalid());}
    let canonical=string("canonical")?;let variant=string("variant")?;
    let size=d["size"].as_f64().ok_or_else(invalid)? as f32;
    let weight=d["weight"].as_f64().ok_or_else(invalid)? as f32;
    let style=string("style")?;let stretch=string("stretch")?;
    let line_height=d["lineHeight"].as_f64().map(|v|v as f32);
    let features=features(&d["features"])?;
    Ok(font_spec(families,canonical,variant,size,weight,&style,&stretch,line_height,features))
}

/// Read original font_features on/off/numeric fields from owned JSON, returning
/// owned tags/i32 values, unitless. No callbacks or native handles; TypeError for
/// invalid private descriptors. Source typography.rs:font_features; same order/casts.
pub fn features(d:&Value) -> PyResult<Vec<(String,i32)>> {
    let invalid=||PyTypeError::new_err("Invalid internal parsed font features");
    let mut features=Vec::new();
    for (key,value) in d.as_object().ok_or_else(invalid)? {
        if key=="on" || key=="off" {
            for feat in value.as_array().ok_or_else(invalid)? {
                features.push((feat.as_str().ok_or_else(invalid)?.to_string(),if key=="on"{1}else{0}));
            }
        }else{features.push((key.clone(),value.as_f64().ok_or_else(invalid)? as f32 as i32));}
    }
    Ok(features)
}
