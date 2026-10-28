//! Diagnostic observation of original measurement layout; never selects/replaces glyphs.
use super::{Typesetter,from_slant,from_width};
use crate::context::State;
use serde_json::{json,Value};
use skia_safe::Paint;

/// Observe original Typesetter::new/layout/extended_visit on the owner thread.
/// Text UTF-8, width/font positions canvas units and glyph IDs unitless.
/// Returns only owned JSON values. Borrowed visitor/font/table
/// objects never escape; no Send/Sync changes or drawing/matching policy overrides.
/// Selected SFNT bytes are temporary diagnostic transport to hash outside native
/// borrow; audit runners must discard them without persistence/redistribution.
/// Sources: original typography.rs:35/51/79; skia-safe0.88 ExtendedVisitorInfo/Typeface.
pub fn glyphs(state:&State,text:&str,width:Option<f32>) -> Value {
    let typesetter=Typesetter::new(state,text,width);
    let (mut paragraph,origin)=typesetter.layout(&Paint::default());
    paragraph_record(&mut paragraph,&typesetter.text,typesetter.width,origin)
}

/// Safely observe glyph/font/grapheme data from an existing original Paragraph.
/// UTF16 cluster ranges and canvas-unit bounds; owned JSON, no native values escape.
/// Uses getGlyphInfoAtUTF16Offset, NEVER the unsafe count+1 utf8_starts visitor slice.
/// Sources: pinned SkParagraph public GlyphInfo API and original Typesetter::layout.
fn paragraph_record(paragraph:&mut skia_safe::textlayout::Paragraph,text:&str,width:f32,origin:skia_safe::Point)->Value {
    let mut runs=Vec::new();
    paragraph.extended_visit(|line,visit| {
        if let Some(info)=visit {
            let font=info.font();let face=font.typeface();let style=face.font_style();
            let tables=[*b"head",*b"name",*b"cmap",*b"OS/2"].iter().map(|tag| {
                let bytes=face.copy_table_data(u32::from_be_bytes(*tag)).map(|data|data.as_bytes().to_vec());
                json!({"tag":String::from_utf8_lossy(tag).to_string(),"data":bytes})
            }).collect::<Vec<_>>();
            let variations=face.variation_design_position().map(|values|values.iter().map(|c|{
                let axis:u32=*c.axis;json!({"axis":axis,"value":c.value})
            }).collect::<Vec<_>>());
            // Do not read utf8_starts(): Skia m140 extendedVisit allocates only
            // context.size entries when fClusterStart>0, while the safe wrapper
            // forms a count+1 slice. Cluster offsets need a separate safe audit;
            // original shaping/layout/rendering is retained without modification.
            runs.push(json!({"line":line,"flags":info.flags().bits(),"glyphs":info.glyphs(),
                "positions":info.positions().iter().map(|p|[p.x,p.y]).collect::<Vec<_>>(),
                "bounds":info.bounds().iter().map(|r|[r.left,r.top,r.right,r.bottom]).collect::<Vec<_>>(),
                "font":{"family":face.family_name(),"postScriptName":face.post_script_name(),"weight":*style.weight(),
                        "width":from_width(style.width()),"slant":from_slant(style.slant()),"size":font.size(),
                        "unitsPerEm":face.units_per_em(),"variations":variations,"tables":tables}}));
        }
    });
    let clusters=(0..text.encode_utf16().count()).map(|index| {
        let info=paragraph.get_glyph_info_at_utf16_offset(index);
        json!({"codeUnit":index,"info":info.map(|g|json!({"range":[g.grapheme_cluster_text_range.start,g.grapheme_cluster_text_range.end],
            "bounds":[g.grapheme_layout_bounds.left,g.grapheme_layout_bounds.top,g.grapheme_layout_bounds.right,g.grapheme_layout_bounds.bottom],
            "direction":format!("{:?}",g.text_direction),"ellipsis":g.is_ellipsis}))})
    }).collect::<Vec<_>>();
    json!({"inputText":text,"layoutText":text,"layoutWidth":width,"clusters":clusters,
           "origin":[origin.x,origin.y],"runs":runs})
}

use std::cell::RefCell;
thread_local! {
    static DRAW_RECORDS:RefCell<Option<Vec<Value>>>=const{RefCell::new(None)};
    static OPERATION:RefCell<&'static str>=const{RefCell::new("layout")};
}
/// Start/end private draw observation; owner TLS only, no units/native transfer.
/// Returns owned JSON on end. Only explicit diagnostic callers enable observation.
pub fn capture(enabled:bool)->Value {DRAW_RECORDS.with(|r|{
    if enabled {*r.borrow_mut()=Some(Vec::new());json!(null)} else {json!(r.borrow_mut().take().unwrap_or_default())}
})}
pub struct Operation(&'static str);
impl Drop for Operation {fn drop(&mut self){OPERATION.with(|r|*r.borrow_mut()=self.0);}}
/// Tag original binding call for diagnostic correlation; static label, RAII owner scope.
/// No rendering state/paint changes, no native objects/errors. Original native call follows.
pub fn operation(name:&'static str)->Operation {Operation(OPERATION.with(|r|r.replace(name)))}
/// Observe the exact Paragraph after its original layout and before original paint/path.
/// Owner TLS, no-op outside explicit diagnostic sessions; no layout/selection mutations.
/// Records actual draw input/paint paragraph, not a recomputed measurement paragraph.
pub fn record_layout(paragraph:&mut skia_safe::textlayout::Paragraph,typesetter:&Typesetter,origin:skia_safe::Point){
    if DRAW_RECORDS.with(|r|r.borrow().is_none()){return}
    let mut record=paragraph_record(paragraph,&typesetter.text,typesetter.width,origin);
    OPERATION.with(|r|record["operation"]=json!(*r.borrow()));
    DRAW_RECORDS.with(|r|{if let Some(records)=r.borrow_mut().as_mut(){records.push(record);}});
}
