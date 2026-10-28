//! Original canvas.rs encoding/file dispatch after language-only argument reads.
use crate::context::page::{PageSequence,ExportOptions};
/// Encode original selected pages; quality/density/etc use original ExportOptions units.
/// Returns owned bytes/original String error. Caller obeys original owner snapshot/cache
/// materialize before Rayon transfer; no Context/DirectContext is passed here.
/// Source canvas.rs:toBufferSync/toBuffer, v3.0.8, retained dispatch.
pub fn encode(pages:&PageSequence,options:ExportOptions)->Result<Vec<u8>,String>{
    if options.format=="pdf" && pages.len() > 1 {
      pages.as_pdf(options)
    }else{
      pages.first().encoded_as(options, pages.engine)
    }
}
/// Write selected pages with original sequence/PDF/image branches. Paths native strings,
/// padding digits f32; returns unit/original String error. Original Rayon write_sequence
/// policy retained. No native owner/context movement. Source canvas.rs:save/saveSync.
pub fn write(pages:&PageSequence,name_pattern:&str,padding:f32,sequence:bool,options:ExportOptions)->Result<(),String>{
    if sequence {
      pages.write_sequence(&name_pattern, padding, options)
    } else if options.format == "pdf" {
      pages.write_pdf(&name_pattern, options)
    } else {
      pages.write_image(&name_pattern, options)
    }
}
