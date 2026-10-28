//! Node-only page array downcast; all recording/cache/encoding/GPU logic is in core.
use neon::prelude::*;
use crate::canvas::BoxedCanvas;
use crate::context::BoxedContext2D;
pub use canvas_core::context::page::*;

/// Downcast original JS page array and snapshot with original options/canvas engine.
/// Parameters: cx (Node thread), idx (argument slot), opts and boxed canvas borrowed.
/// Returns owned PageSequence or original Neon argument/downcast error; GPU objects stay on owner thread.
/// Upstream: src/context/page.rs:655-665, skia-canvas 3.0.8; body unchanged.
pub fn pages_arg(cx: &mut FunctionContext, idx:usize, opts:&ExportOptions, canvas:&BoxedCanvas) -> NeonResult<PageSequence> {
  let engine = canvas.borrow_mut().engine();
  let pages = cx.argument::<JsArray>(idx)?
      .to_vec(cx)?
      .iter()
      .map(|obj| obj.downcast::<BoxedContext2D, _>(cx))
      .filter( |ctx| ctx.is_ok() )
      .map(|obj| obj.unwrap().borrow().get_page_for_export(opts, &engine))
      .collect();
  Ok(PageSequence::from(pages, engine))
}
