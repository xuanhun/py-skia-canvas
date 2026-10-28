"""Original context text-state operations, separating only language reads/results."""
import json,re

SETTERS=[
 ('set_textAlign','name:String','name','  if let Some(mode)',[]),
 ('set_textBaseline','name:String','name','  if let Some(mode)',[]),
 ('set_direction','name:String','name','  let direction =',[]),
 ('set_fontStretch','stretch:String','stretch','    this.set_font_width',[]),
 ('set_letterSpacing','spacing:Option<Spacing>','opt_spacing_arg(&mut cx, 1)?','  if let Some(spacing)',[('opt_spacing_arg(&mut cx, 1)?','spacing')]),
 ('set_wordSpacing','spacing:Option<Spacing>','opt_spacing_arg(&mut cx, 1)?','  if let Some(spacing)',[('opt_spacing_arg(&mut cx, 1)?','spacing')]),
 ('set_fontHinting','flag:bool','flag','  this.state.font_hinting',[]),
 ('set_textWrap','flag:bool','flag','  this.state.text_wrap',[]),
 ('set_fontVariant','variant:String, features:Vec<(String,i32)>','variant, features','  this.set_font_variant',[]),
 ('set_textDecoration','deco_style:DecorationStyle','deco_style','      this.state.text_decoration',[]),
]
GETTERS=[('get_textAlign','String'),('get_textBaseline','String'),('get_direction',"&'static str"),('get_fontStretch','String'),('get_letterSpacing','String'),('get_wordSpacing','String'),('get_fontVariant','String'),('get_fontHinting','bool'),('get_textWrap','bool'),('get_textDecoration','String')]

def definitions(original,bodies):
    """Return owned original/typed text fragments and source lines, no execution/ownership.

    Names/flags unitless, spacing f32 canvas units. Missing source markers fail explicitly.
    Original setters/getters stay unchanged except argument extraction/JS result allocation.
    """
    result=[]
    for name,params,call,start,changes in SETTERS:
        fn=bodies(original,name)[0];body=fn['body'];begin=body.index(start)
        end=body.index('  }',begin) if name=='set_fontStretch' else body.index('\n    }',begin)+1 if name=='set_textDecoration' else body.rindex('  Ok(cx.undefined())')
        block=body[begin:end];typed=block
        for old,new in changes:assert old in typed;typed=typed.replace(old,new,1)
        result.append({'name':name,'params':params,'call':call,'line':fn['line'],'original':block,'typed':typed,'returns':'()','setter':True})
    for name,returns in GETTERS:
        fn=bodies(original,name)[0];body=fn['body'];start=body.index('  let this = this.borrow_mut();')+len('  let this = this.borrow_mut();\n')
        block=body[start:-1];typed=re.sub(r'  Ok\(cx\.(?:string|boolean)\((.*)\)\)',r'  \1',block)
        assert typed!=block
        result.append({'name':name,'params':'','call':'','line':fn['line'],'original':block,'typed':typed,'returns':returns,'setter':False})
    return result

def core_operations(original,bodies):
    """Emit single original typed text-state implementation; no font/layout/GPU changes.

    String parameters unitless, spacing original f32 units, return owned values/unit.
    Owner Context only; adapters validate strings/bools/Spacing, no Python callbacks.
    """
    result='''//! Original text-state API operations; language argument/result allocation removed only.
#![allow(non_snake_case)]
use super::Context2D;
use crate::typography::*;
use skia_safe::textlayout::TextDirection;
'''
    for item in definitions(original,bodies):
        params=(', '+item['params']) if item['params'] else '';owner='&mut Context2D' if item['setter'] else '&Context2D'
        result+=f'''
/// Original {item['name']} statements; names/flags unitless, spacing f32 CSS/canvas units.
/// Returns original owned value/unit, no new errors or invalid-value policy. Owner
/// Context only; no callbacks or transfer of font/GPU objects. Adapters supply typed args.
/// Upstream: src/context/api.rs:{item['line']}, skia-canvas3.0.8.
pub fn {item['name']}(this:{owner}{params}) -> {item['returns']} {{
{item['typed']}}}
'''
    return result

def node_operations(source,original,bodies):
    """Forward only original state fragments; keep Node argument/order/error behavior."""
    for item in definitions(original,bodies):
        if item['setter']:
            replacement='  canvas_core::context::text_state::'+item['name']+'(&mut this, '+item['call']+');\n'
        else:
            method='boolean' if item['returns']=='bool' else 'string'
            replacement='  let value = canvas_core::context::text_state::'+item['name']+'(&this);\n  Ok(cx.'+method+'(value))\n'
        if item['name']=='set_fontStretch':replacement='  '+replacement
        if item['name']=='set_textDecoration':replacement='    '+replacement
        fn=bodies(source,item['name'])[0]['text'];assert item['original'] in fn
        source=source.replace(fn,fn.replace(item['original'],replacement,1),1)
    return source.replace('use skia_safe::textlayout::{TextDirection};\n','').replace('font_features, from_width, to_width,','font_features,').replace('  from_text_align, to_text_align, from_text_baseline, to_text_baseline,\n','')

def feature_data(css):
    """Emit original CSS feature/alternate literal tables; unitless strings, no runtime JS.

    Source css.js const featureMap/alternatesMap, MIT; deterministic literal-only copy.
    """
    feature_block=css.split('const featureMap = {',1)[1].split('\n}',1)[0]
    alternate_block=css.split('const alternatesMap = {',1)[1].split('\n}',1)[0]
    features={k:json.loads('['+v+']') for k,v in re.findall(r'"([^"]+)": \[([^\]]*)\]',feature_block)}
    alternates=dict(re.findall(r'"([^"]+)": "([^"]+)"',alternate_block))
    return '"""Original css.js:featureMap/alternatesMap literals (MIT); unitless, Python-owned."""\nFEATURES = '+repr(features)+'\nALTERNATES = '+repr(alternates)+'\n'
