//! Current-thread FontLibrary facade; no Python-owned fonts or cross-thread Skia values.
use pyo3::{prelude::*,types::PyModule};
use canvas_core::font_library::{FontLibrary,load_typeface,typeface_metadata};
use serde_json::json;
use crate::Error;

/// Query original case-sensitive families membership; family string unitless, bool result.
/// Current-thread TLS library, no transferable native objects or callbacks. Source: has.
#[pyfunction]
fn _font_has(family:&str) -> bool { FontLibrary::with_shared(|lib|lib.families().contains(&family.to_string())) }

/// Query original family weights/widths/styles, None for original undefined on no weights.
/// Returns owned JSON string or None; unitless metadata, current-thread TLS, no callbacks.
/// Source: font_library.rs:family/family_details; no normalization or matching rewrite.
#[pyfunction]
fn _font_family(family:&str) -> Option<String> {
    let (weights,widths,styles)=FontLibrary::with_shared(|lib|lib.family_details(family));
    if weights.is_empty() { None } else { Some(json!({"family":family,"weights":weights,"widths":widths,"styles":styles}).to_string()) }
}

/// Load original filtered string paths, return owned metadata JSON; paths/alias unitless.
/// File read/decode errors ->original Error; earlier successful registrations remain.
/// Typeface/FontMgr stay current-thread TLS; no callbacks during borrow/GPU transfer.
/// Source: font_library.rs:addFamily, metadata allocation separated from same core helpers.
#[pyfunction]
#[pyo3(signature=(alias,filenames))]
fn _font_add(alias:Option<String>,filenames:Vec<String>) -> PyResult<String> {
    let mut results=Vec::new();
    for filename in filenames {
        let font=load_typeface(&filename).map_err(Error::new_err)?;
        let (family,weight,style,width)=typeface_metadata(&font,alias.clone());
        results.push(json!({"family":family,"weight":weight,"style":style,"width":width,"file":filename}));
        FontLibrary::with_shared(|lib|lib.add_typeface(font,alias.clone()));
    }
    Ok(serde_json::to_string(&results).unwrap())
}

/// Original reset of user registrations/collections/caches, current thread only, unit return.
/// Generic/system font caches retained as original; no GPU or Python objects. Source: reset.
#[pyfunction]
fn _font_reset() { FontLibrary::with_shared(|lib|lib.reset()); }

/// Register private language entry points; no units/native ownership, PyO3 errors propagate.
pub fn register(module:&Bound<'_,PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(_font_has,module)?)?;
    module.add_function(wrap_pyfunction!(_font_family,module)?)?;
    module.add_function(wrap_pyfunction!(_font_add,module)?)?;
    module.add_function(wrap_pyfunction!(_font_reset,module)?)?;
    Ok(())
}
