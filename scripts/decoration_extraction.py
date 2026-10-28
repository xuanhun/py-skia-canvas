"""Controlled extraction of original decoration_arg through a typed language reader."""

def definition(original,bodies):
    """Return original/typed decoration block and original optional-spacing reader.

    Only source text, unitless strings and f32 Spacing semantics; no execution/threads.
    Missing markers fail. Native order, default early return, color/size guard retained.
    """
    fn=bodies(original,'decoration_arg')[0];body=fn['body']
    block=body[body.index('    let css ='):body.index('  }else{')]
    spacing=block[block.index('match opt_object_for_key'):block.index('\n    };',block.index('match opt_object_for_key'))]
    typed=block.replace('string_for_key(cx, &deco, ','reader.string(').replace(spacing,'reader.spacing()?')
    return {'name':'decoration_style','line':fn['line'],'original':block,'typed':typed,'spacing':spacing}

def core_module(original,bodies):
    """Emit single original style selection through owned language fields; no layout changes.

    Generic reader errors returned unchanged; no runtime language/Context/GPU types involved.
    Original Spacing/DecorationStyle/for_layout and matching remain in parent typography.
    """
    item=definition(original,bodies)
    return f'''//! Original decoration_arg decision/order, with language field access separated only.
use super::{{DecorationStyle,Spacing}};
use crate::utils::css_to_color;
use skia_safe::textlayout::{{Decoration,TextDecoration,TextDecorationMode,TextDecorationStyle}};

/// Typed field boundary for original decoration_arg. Names/styles/colors are strings,
/// thickness is original f32 Spacing. Errors are the adapter's original field errors.
/// No Context borrow is held while reading fields; implementations must retain their
/// language's original property/error rules. Upstream: src/typography.rs:{item['line']}.
pub trait DecorationArgs {{
    type Error;
    /// Read original named string field, returning owned text or original error; no units.
    fn string(&mut self,name:&str) -> Result<String,Self::Error>;
    /// Read optional thickness object in original raw-size/unit/px order, or None.
    /// Sizes are original f32 CSS/canvas units; errors propagate without changing state.
    fn spacing(&mut self) -> Result<Option<Spacing>,Self::Error>;
}}

/// Original decoration selection/default/color/size guard and Through mode. Returns
/// owned DecorationStyle/None or reader error. CurrentColor handling and early default
/// are retained exactly; no font/layout/drawing or GPU changes. Called before borrowing
/// owner Context; no handles cross threads. Upstream: src/typography.rs:{item['line']}.
pub fn decoration_style<R:DecorationArgs>(reader:&mut R) -> Result<Option<DecorationStyle>,R::Error> {{
{item['typed']}}}
'''

def node_reader(original,bodies):
    """Generate original Node string/optional-thickness field reader, no typed policy copy."""
    item=definition(original,bodies)
    spacing=item['spacing'].replace('opt_object_for_key(cx, &deco,','opt_object_for_key(self.cx, &self.deco,').replace('Spacing::from_obj(cx,','Spacing::from_obj(self.cx,')
    return '''
/// Original decoration argument reads; no Context borrow, original Neon field errors.
struct NodeDecorationArgs<'a,'b> { cx:&'b mut FunctionContext<'a>, deco:Handle<'a,JsObject> }
impl<'a,'b> canvas_core::typography::decoration::DecorationArgs for NodeDecorationArgs<'a,'b> {
  type Error = neon::result::Throw;
  /// Read original owned string, unitless; source typography.rs:decoration_arg.
  fn string(&mut self,name:&str) -> Result<String,Self::Error> {
    string_for_key(self.cx,&self.deco,name)
  }
  /// Read optional raw-size/unit/px f32 fields in original order; same field errors.
  fn spacing(&mut self) -> Result<Option<Spacing>,Self::Error> {
    Ok('''+spacing+''')
  }
}
'''

def node_module(source,original,bodies):
    """Keep original optional-object boundary and forward decision to sole shared core."""
    old=bodies(original,'decoration_arg')[0]['body']
    new='''{
  if let Some(deco) = opt_object_arg(cx, idx){
    let mut reader = NodeDecorationArgs{cx,deco};
    canvas_core::typography::decoration::decoration_style(&mut reader)
  }else{
    Ok(None)
  }
}'''
    assert old in source
    return source.replace(old,new,1).replace('use skia_safe::textlayout::{Decoration, TextDecoration, TextDecorationMode, TextDecorationStyle};\n','')+node_reader(original,bodies)
