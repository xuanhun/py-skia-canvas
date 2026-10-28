"""Original Canvas constructor validation and float-argument declarations, language-only split."""
import re

def core(source,bodies):
    """Generate original SurfaceProps bounds/epsilon/known gamma condition in read order.
    Source canvas.rs:new; optional f64 settings, bool GPU. Text only, no native transfer.
    """
    body=bodies(source,'new')[1]['body'];a=body.index('  let text_contrast');b=body.index('  let this =',a);block=body[a:b]
    block=block.replace('opt_double_for_key(&mut cx, &opts, "textContrast")','args.number("textContrast")').replace('opt_double_for_key(&mut cx, &opts, "textGamma")','args.number("textGamma")').replace('cx.throw_range_error(', 'Err(OptionsError::Range(')
    # Range error calls add one enum wrapper closing parenthesis.
    block=block.replace('min_c, max_c))','min_c, max_c)))').replace('min_g, max_g))','min_g, max_g)))')
    block=block.replace('bool_for_key(&mut cx, &opts, "gpu")?','args.flag().map_err(OptionsError::Field)?')
    return '''//! Original Canvas construction option validation, separated from language fields.
use super::Canvas;
use skia_safe::SurfaceProps;
pub enum OptionsError<E>{Range(String),Field(E)}
pub trait CanvasArgs{
    type Error;
    /// Optional original finite f64 conversion, unitless contrast/gamma, no native refs.
    fn number(&mut self,key:&str)->Option<f64>;
    /// Original bool field/error, no units or native refs; evaluated after range checks.
    fn flag(&mut self)->Result<bool,Self::Error>;
}
/// Validate and construct original Canvas (default 300x150 canvas units).
/// f64 contrast/gamma, GPU bool; returns original Canvas/range or reader error.
/// Original max-gamma equality adjustment and contrast-vs-max-gamma condition preserved.
/// Owner caller retains Canvas, no Send/Sync or GPU/context creation added.
/// Source canvas.rs:new v3.0.8; exact argument validation after typed field reads.
pub fn construct<A:CanvasArgs>(args:&mut A)->Result<Canvas,OptionsError<A::Error>>{
'''+block+'''  Ok(Canvas::new(text_contrast as f64, text_gamma as f64, !gpu_enabled))
}
'''

def node(current,source,bodies):
    """Forward Node constructor validation to unique core, retain Neon fields/boxing/errors.
    Returns source text; same numeric conversion order, no rendering/ownership change.
    """
    old=bodies(current,'new')[0]['text']
    return current.replace(old,'''struct CanvasFields<'a,'b>{cx:&'a mut FunctionContext<'b>,opts:Handle<'b,JsObject>}
impl canvas_core::canvas::construction::CanvasArgs for CanvasFields<'_, '_>{
  type Error=neon::result::Throw;
  fn number(&mut self,key:&str)->Option<f64>{opt_double_for_key(self.cx,&self.opts,key)}
  fn flag(&mut self)->NeonResult<bool>{bool_for_key(self.cx,&self.opts,"gpu")}
}
pub fn new(mut cx:FunctionContext)->JsResult<BoxedCanvas>{
  let opts=cx.argument::<JsObject>(1)?;
  let canvas=canvas_core::canvas::construction::construct(&mut CanvasFields{cx:&mut cx,opts}).or_else(|e|match e{
    canvas_core::canvas::construction::OptionsError::Range(msg)=>cx.throw_range_error(msg),
    canvas_core::canvas::construction::OptionsError::Field(e)=>Err(e),
  })?;
  Ok(cx.boxed(RefCell::new(Resource(canvas))))
}
''',1)

def arguments(root,bodies):
    """Read original Native float-helper names/stages, bail behavior and argument positions.
    Generates owned Python data only; no algorithms/units changed. Source files immutable.
    """
    groups={};names=('moveTo','lineTo','rect','arc','ellipse','arcTo','bezierCurveTo','quadraticCurveTo','conicCurveTo','fillRect','strokeRect','clearRect','translate','scale','rotate')
    for group,file in [('context','context/api.rs'),('path','path.rs'),('gradient','gradient.rs')]:
        src=(root/file).read_text(encoding='utf-8');entries={}
        for name in (('linear','radial','conic','addColorStop') if group=='gradient' else names):
            fns=bodies(src,name)
            if not fns:continue
            stages=[]
            for match in re.finditer(r'(float_args(?:_or_bail)?|float_arg(?:_or_bail)?)\(&mut cx,\s*(?:&\[(.*?)\]|(\d+),\s*"(.*?)")\)',fns[0]['body'],re.S):
                helper,array,start,single=match.groups();stages.append((int(start or 1),re.findall(r'"(.*?)"',array) if array is not None else [single],helper.endswith('_or_bail')))
            entries[name]=dict(stages=stages,source=f'src/{file}:{fns[0]["line"]}')
        groups[group]=entries
    return '# Generated original float argument declarations; edit only through construction_extraction.py.\nSPECS = '+repr(groups)+'\n'
