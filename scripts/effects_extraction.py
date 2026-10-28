"""Original effect state/FilterSpec extraction, deterministic source tooling only."""
import re

SETTERS=[
 ('set_globalAlpha','num:f32','num','  if (0.0..=1.0)',[]),
 ('set_globalCompositeOperation','name:String','name','  if let Some(mode)',[]),
 ('set_shadowBlur','num:f32','num','  if num >=',[]),
 ('set_shadowColor','color:Option<Color>','opt_color_arg(&mut cx, 1)','  if let Some(color)',[('opt_color_arg(&mut cx, 1)','color')]),
 ('set_shadowOffsetX','num:f32','float_arg_or_bail(&mut cx, 1, "shadowOffsetX")?','  this.state.shadow_offset.x',[('float_arg_or_bail(&mut cx, 1, "shadowOffsetX")?','num')]),
 ('set_shadowOffsetY','num:f32','float_arg_or_bail(&mut cx, 1, "shadowOffsetY")?','  this.state.shadow_offset.y',[('float_arg_or_bail(&mut cx, 1, "shadowOffsetY")?','num')]),
 ('set_lineDashFit','style:String','style','  if let Some(fit)',[('this.borrow_mut().state','this.state')]),
 ('set_filter','filter_text:String, specs:Vec<FilterSpec>','filter_text, specs','    if filter_text',[]),
]
GETTERS=[('get_globalAlpha','f32'),('get_globalCompositeOperation','String'),('get_shadowBlur','f32'),('get_shadowColor','Color'),('get_shadowOffsetX','f32'),('get_shadowOffsetY','f32'),('get_lineDashFit','String'),('get_filter','String')]

def definitions(source,bodies):
    """Describe retained original statements and language substitutions as owned strings.
    Units/owner/error documented in generated core; source offsets text only, drift raises.
    """
    out=[]
    for name,params,call,start,changes in SETTERS:
        fn=bodies(source,name)[0];body=fn['body'];a=body.index(start);end=body.rindex('  Ok(cx.undefined())')
        if name=='set_filter':end=body.rindex('\n  }')
        block=body[a:end];typed=block
        for before,after in changes:assert before in typed;typed=typed.replace(before,after)
        out.append(dict(name=name,params=params,call=call,line=fn['line'],original=block,typed=typed,returns='()',setter=True))
    for name,returns in GETTERS:
        fn=bodies(source,name)[0];body=fn['body']
        if name=='get_lineDashFit':block=body[body.index('  let fit ='):body.rfind('}')];typed=block.replace('this.borrow().state','this.state')
        else:
            a=body.index('  let this = this.borrow_mut();')+len('  let this = this.borrow_mut();\n');block=body[a:body.rfind('}')];typed=block
        if name=='get_shadowColor':typed=typed.replace('  color_to_css(&mut cx, &shadow_color)','  shadow_color')
        else:typed=re.sub(r'  Ok\(cx\.(?:string|number)\((.*)\)\)',r'  \1',typed)
        assert typed!=block
        out.append(dict(name=name,params='',call='',line=fn['line'],original=block,typed=typed,returns=returns,setter=False))
    return out

def core_operations(api,bodies):
    """Generate original typed state operations; no painting/shaping/blending changes.
    Returns UTF-8 source, no native objects; invalid original source raises explicitly.
    """
    out='''//! Original context/api.rs effect state, language reads/results removed only.
#![allow(non_snake_case)]
use super::Context2D;
use skia_safe::Color;
use crate::{utils::*,filter::{Filter,FilterSpec}};
'''
    for d in definitions(api,bodies):
        owner='&mut Context2D' if d['setter'] else '&Context2D';params=', '+d['params'] if d['params'] else ''
        out+=f'''
/// Original {d['name']} operation; alpha/style unitless, offsets/blur canvas units.
/// Returns original value/unit after typed adapter reads, no new errors. Owner thread
/// only, no callbacks/Skia transfer/Send or Sync. Source context/api.rs:{d['line']} v3.0.8.
pub fn {d['name']}(this:{owner}{params})->{d['returns']} {{
{d['typed']}}}
'''
    return out

def node_operations(current,api,bodies):
    """Forward Node state statements to same typed core, preserving reader/null gates.
    Returns source text only; missing original block raises, no runtime/ownership work.
    """
    for d in definitions(api,bodies):
        if d['setter']:
            this='&mut this.borrow_mut()' if d['name']=='set_lineDashFit' else '&mut this'
            repl='  canvas_core::context::effects::'+d['name']+'('+this+', '+d['call']+');\n'
            if d['name']=='set_filter':repl='  '+repl
        else:
            this='&this.borrow()' if d['name']=='get_lineDashFit' else '&this'
            expr='canvas_core::context::effects::'+d['name']+'('+this+')'
            if d['name']=='get_shadowColor':repl='  let shadow_color = '+expr+';\n  color_to_css(&mut cx, &shadow_color)\n'
            else:repl='  let value = '+expr+';\n  Ok(cx.'+('string' if d['returns']=='String' else 'number')+'(value))\n'
        fn=bodies(current,d['name'])[0]['text'];assert d['original'] in fn
        current=current.replace(fn,fn.replace(d['original'],repl,1),1)
    return current

def argument_definition(source,bodies):
    """Separate original FilterSpec selection from typed field reads, no drawing work.
    Data/units f32 original CSS/canvas values, owned source and declared substitutions.
    Source utils.rs:filter_arg v3.0.8; shadow dimensions are native reader validated.
    """
    fn=bodies(source,'filter_arg')[0];body=fn['body']
    block=body[body.index('  let mut filters'):body.rindex('  Ok( (canonical, filters) )')]
    typed=block.replace('for (name, key) in strings_in(cx, &keys).iter().zip(keys)', 'for name in names')
    old='''        let values = obj.get::<JsArray, _, _>(cx, key)?;
        let nums = values.to_vec(cx)?;
        let dims = floats_in(cx, &nums);
        let color_str = values.get::<JsString, _, _>(cx, 3)?.value(cx);'''
    assert old in typed;typed=typed.replace(old,'        let (dims, color_str) = args.shadow(&name)?;')
    typed=typed.replace('obj.get::<JsNumber, _, _>(cx, key)?.value(cx) as f32','args.number(&name)?')
    return dict(original=block,typed=typed,line=fn['line'])

def core_arguments(source,bodies):
    """Emit single original FilterSpec packing loop with lazy language field reader.
    No rendering/alpha/color algorithms replaced; source-only generator, drift raises.
    """
    d=argument_definition(source,bodies)
    return '''//! Original utils.rs:filter_arg packing; only language field reads abstracted.
use crate::{filter::FilterSpec,utils::css_to_color};
use skia_safe::Point;
pub trait FilterArgs {
    type Error;
    /// Read original canonical string, unitless; owned value or original field error.
    fn canonical(&mut self)->Result<String,Self::Error>;
    /// Read original own filter names/insertion order; owned strings, original field error.
    fn names(&mut self)->Result<Vec<String>,Self::Error>;
    /// Read original array/float filtering/color string in order; f32 CSS/canvas units.
    /// Returns owned values/original field error, never borrowed native objects.
    fn shadow(&mut self,name:&str)->Result<(Vec<f32>,String),Self::Error>;
    /// Read original JsNumber-as-f32; amount/degree/CSS units, original field error.
    fn number(&mut self,name:&str)->Result<f32,Self::Error>;
}
/// Original FilterSpec packing, lazy reader preserves error/field order and color ignore.
/// Returns owned canonical/specs; widths/offsets canvas units, hue degrees, plain amounts
/// unitless. Owner-native objects do not escape; source utils.rs:filter_arg v3.0.8.
pub fn filter_arg<A:FilterArgs>(args:&mut A)->Result<(String,Vec<FilterSpec>),A::Error> {
  let canonical=args.canonical()?;
  let names=args.names()?;
'''+d['typed']+'  Ok( (canonical, filters) )\n}\n'

def node_arguments(current,source,bodies):
    """Replace Node packing loop with original Neon reader and shared typed algorithm.
    Returns source, reads exact original field/order/types. No runtime objects in core.
    """
    fn=bodies(current,'filter_arg')[0]['text']
    reader='''struct FilterFields<'a,'b> { cx:&'a mut FunctionContext<'b>,arg:Handle<'b,JsObject>,obj:Option<Handle<'b,JsObject>> }
impl canvas_core::filter::arguments::FilterArgs for FilterFields<'_, '_> {
  type Error=neon::result::Throw;
  fn canonical(&mut self)->Result<String,Self::Error>{string_for_key(self.cx,&self.arg,"canonical")}
  fn names(&mut self)->Result<Vec<String>,Self::Error>{
    let obj:Handle<JsObject>=self.arg.get(self.cx,"filters")?;
    let keys=obj.get_own_property_names(self.cx)?.to_vec(self.cx)?;
    let names=strings_in(self.cx,&keys);self.obj=Some(obj);Ok(names)
  }
  fn shadow(&mut self,name:&str)->Result<(Vec<f32>,String),Self::Error>{
    let values=self.obj.unwrap().get::<JsArray,_,_>(self.cx,name)?;
    let nums=values.to_vec(self.cx)?;
    let dims=floats_in(self.cx,&nums);
    let color_str=values.get::<JsString,_,_>(self.cx,3)?.value(self.cx);
    Ok((dims,color_str))
  }
  fn number(&mut self,name:&str)->Result<f32,Self::Error>{Ok(self.obj.unwrap().get::<JsNumber,_,_>(self.cx,name)?.value(self.cx) as f32)}
}

'''
    replacement='''pub fn filter_arg(cx: &mut FunctionContext, idx: usize) -> NeonResult<(String, Vec<FilterSpec>)> {
  let arg=cx.argument::<JsObject>(idx)?;
  canvas_core::filter::arguments::filter_arg(&mut FilterFields{cx,arg,obj:None})
}'''
    return current.replace(fn,reader+replacement,1)
