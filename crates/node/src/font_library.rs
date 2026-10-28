//! Node metadata/file argument adapter; the original font singleton/cache is in core.
#![allow(non_snake_case)]
use neon::prelude::*;
use crate::utils::*;
use crate::typography::typeface_details;
pub use canvas_core::font_library::FontLibrary;

//
// Javascript Methods
//

pub fn get_families(mut cx: FunctionContext) -> JsResult<JsArray> {
  strings_to_array(&mut cx, &FontLibrary::with_shared(|lib|
    lib.families()
  ))
}

pub fn has(mut cx: FunctionContext) -> JsResult<JsBoolean> {
  let family = string_arg(&mut cx, 1, "familyName")?;
  let found = FontLibrary::with_shared(|lib|
    lib.families().contains(&family)
  );
  Ok(cx.boolean(found))
}

pub fn family(mut cx: FunctionContext) -> JsResult<JsValue> {
  let family = string_arg(&mut cx, 1, "familyName")?;
  let (weights, widths, styles) = FontLibrary::with_shared(|lib|
    lib.family_details(&family)
  );

  if weights.is_empty() {
    return Ok(cx.undefined().upcast())
  }

  let name = cx.string(family);
  let weights = floats_to_array(&mut cx, &weights)?;
  let widths = strings_to_array(&mut cx, &widths)?;
  let styles = strings_to_array(&mut cx, &styles)?;

  let details = JsObject::new(&mut cx);
  let attr = cx.string("family"); details.set(&mut cx, attr, name)?;
  let attr = cx.string("weights"); details.set(&mut cx, attr, weights)?;
  let attr = cx.string("widths"); details.set(&mut cx, attr, widths)?;
  let attr = cx.string("styles"); details.set(&mut cx, attr, styles)?;

  Ok(details.upcast())
}

pub fn addFamily(mut cx: FunctionContext) -> JsResult<JsValue> {
  let alias = opt_string_arg(&mut cx, 1);
  let filenames = cx.argument::<JsArray>(2)?.to_vec(&mut cx)?;
  let results = JsArray::new(&mut cx, filenames.len());

  for (i, filename) in strings_in(&mut cx, &filenames).iter().enumerate(){
    let font = canvas_core::font_library::load_typeface(filename).or_else(|e| cx.throw_error(e))?;
        // add family/weight/width/slant details to return value
        let details = typeface_details(&mut cx, filename, &font, alias.clone())?;
        results.set(&mut cx, i as u32, details)?;

        // register the typeface
        FontLibrary::with_shared(|lib|
          lib.add_typeface(font, alias.clone())
        );

  }

  Ok(results.upcast())
}

pub fn reset(mut cx: FunctionContext) -> JsResult<JsUndefined> {
  FontLibrary::with_shared(|lib|{
    lib.reset();
  });

  Ok(cx.undefined())
}
