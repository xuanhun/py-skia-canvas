"""Original canvas export dispatch/options packing; deterministic language separation only."""

def dispatch_blocks(canvas,bodies):
    """Return original buffer/file dispatch statements, no native execution or ownership.
    Inputs source text, returns owned blocks; missing markers raise. Source canvas.rs v3.0.8.
    """
    buf=bodies(canvas,'toBufferSync')[0]['body'];a=buf.index('    if options.format');b=buf.index('\n  };',a);buf=buf[a:b]
    save=bodies(canvas,'saveSync')[0]['body'];a=save.index('    if sequence');b=save.index('\n  };',a);save=save[a:b]
    return buf,save

def core_dispatch(canvas,bodies):
    """Generate original dispatch; options original f32s, paths strings, returns bytes/unit/errors.
    Original PageSequence owns sendable snapshots, never a live Context. Text generation only.
    """
    buf,save=dispatch_blocks(canvas,bodies)
    return '''//! Original canvas.rs encoding/file dispatch after language-only argument reads.
use crate::context::page::{PageSequence,ExportOptions};
/// Encode original selected pages; quality/density/etc use original ExportOptions units.
/// Returns owned bytes/original String error. Caller obeys original owner snapshot/cache
/// materialize before Rayon transfer; no Context/DirectContext is passed here.
/// Source canvas.rs:toBufferSync/toBuffer, v3.0.8, retained dispatch.
pub fn encode(pages:&PageSequence,options:ExportOptions)->Result<Vec<u8>,String>{
'''+buf+'''
}
/// Write selected pages with original sequence/PDF/image branches. Paths native strings,
/// padding digits f32; returns unit/original String error. Original Rayon write_sequence
/// policy retained. No native owner/context movement. Source canvas.rs:save/saveSync.
pub fn write(pages:&PageSequence,name_pattern:&str,padding:f32,sequence:bool,options:ExportOptions)->Result<(),String>{
'''+save+'''
}
'''

def node_dispatch(current,canvas,bodies):
    """Forward Node sync/async branches to unique dispatch, retain original Rayon/materialize.
    Returns source text; no runtime operations. Reader/error return policy remains in Node.
    """
    buf,save=dispatch_blocks(canvas,bodies)
    for name,is_file in [('toBuffer',False),('toBufferSync',False),('save',True),('saveSync',True)]:
        fn=bodies(current,name)[0]['text'];body=bodies(current,name)[0]['body']
        if is_file:a=body.index('if sequence');b=body.index('\n    };' if name=='save' else '\n  };',a)
        else:a=body.index('if options.format');b=body.index('\n    };' if name=='toBuffer' else '\n  };',a)
        block=body[a:b];call='canvas_core::canvas::exports::'+('write(&pages, &name_pattern, padding, sequence, options)' if is_file else 'encode(&pages, options)')
        current=current.replace(fn,fn.replace(block,call,1),1)
    return current

def arguments_block(source,bodies):
    """Original ExportOptions packing with per-field language adapters, owned source only.
    Source utils.rs:export_options_arg; dimensions density, quality, text f32 at original cast.
    """
    fn=bodies(source,'export_options_arg')[0];body=fn['body'];block=body[body.index('  let format ='):body.rfind('}')]
    changes=[('string_for_key(cx, &opts, "format")?','args.string("format")?'),('bool_for_key(cx, &opts, "downsample")?','args.flag("downsample")?'),('bool_for_key(cx, &opts, "outline")?','args.flag("outline")?'),('opt_color_for_key(cx, &opts, "matte")','args.color("matte")'),('opt_float_for_key(cx, &opts, "msaa")','args.optional_number("msaa")'),('opt_string_for_key(cx, &opts, "colorType")','args.optional_string("colorType")')]
    for name in ('quality','density','textContrast','textGamma'):changes.append((f'float_for_key(cx, &opts, "{name}")?',f'args.number("{name}")?'))
    typed=block
    for before,after in changes:assert before in typed;typed=typed.replace(before,after)
    return dict(original=block,typed=typed,line=fn['line'])

def core_arguments(source,bodies):
    """Generate original options factory with typed fields; no rendering/codec algorithms.
    Text only, source drift raises; caller fields owned, conversions/errors documented by trait.
    """
    d=arguments_block(source,bodies)
    return '''//! Original utils.rs:export_options_arg typed field packing only.
use crate::{context::page::ExportOptions,utils::to_color_type};
use skia_safe::{Color,ColorType,ColorSpace};
pub trait ExportArgs {
    type Error;
    /// Owned original string field or original TypeError; no units/native refs.
    fn string(&mut self,name:&str)->Result<String,Self::Error>;
    /// Original bool field or TypeError; no units/native refs.
    fn flag(&mut self,name:&str)->Result<bool,Self::Error>;
    /// Original finite-f64 then f32 field; quality/density/text units, original TypeError.
    fn number(&mut self,name:&str)->Result<f32,Self::Error>;
    /// Original optional float, then core floor/as-usize for MSAA; no field error.
    fn optional_number(&mut self,name:&str)->Option<f32>;
    /// Original optional string field; no units/native objects or errors.
    fn optional_string(&mut self,name:&str)->Option<String>;
    /// Original optional CSS color after language toString; packed color/None, owner local.
    fn color(&mut self,name:&str)->Option<Color>;
}
/// Pack original ExportOptions in the original read order, no callback/render policy.
/// Returns owned options or original field error; f32 conversions stay in language reader.
/// Source utils.rs:export_options_arg v3.0.8; bounds/codec validation stays original core.
pub fn export_options_arg<A:ExportArgs>(args:&mut A)->Result<ExportOptions,A::Error>{
'''+d['typed']+'}\n'

def node_arguments(current,source,bodies):
    """Node reader delegates same original Neon helpers and order to typed core factory.
    Returns source text, no native execution/ownership transfer.
    """
    fn=bodies(current,'export_options_arg')[0]['text']
    reader='''struct ExportFields<'a,'b>{cx:&'a mut FunctionContext<'b>,opts:Handle<'b,JsObject>}
impl canvas_core::canvas::options::ExportArgs for ExportFields<'_, '_>{
  type Error=neon::result::Throw;
  fn string(&mut self,name:&str)->Result<String,Self::Error>{string_for_key(self.cx,&self.opts,name)}
  fn flag(&mut self,name:&str)->Result<bool,Self::Error>{bool_for_key(self.cx,&self.opts,name)}
  fn number(&mut self,name:&str)->Result<f32,Self::Error>{float_for_key(self.cx,&self.opts,name)}
  fn optional_number(&mut self,name:&str)->Option<f32>{opt_float_for_key(self.cx,&self.opts,name)}
  fn optional_string(&mut self,name:&str)->Option<String>{opt_string_for_key(self.cx,&self.opts,name)}
  fn color(&mut self,name:&str)->Option<Color>{opt_color_for_key(self.cx,&self.opts,name)}
}

pub fn export_options_arg(cx:&mut FunctionContext,idx:usize)->NeonResult<ExportOptions>{
  let opts=opt_object_arg(cx,idx).unwrap();
  canvas_core::canvas::options::export_options_arg(&mut ExportFields{cx,opts})
}'''
    return current.replace(fn,reader,1)
