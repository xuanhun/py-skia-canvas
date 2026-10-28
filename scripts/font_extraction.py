"""Controlled FontSpec argument/allocation separation, preserving original typed rules."""

def definition(original,bodies):
    """Return original font_arg and typed body; strings/weights unitless, sizes canvas units.

    Source-text transformation only, no fonts/threads; missing markers raise assertions.
    Reads are separated from original enum casts/f32 line-height ratio and empty-family rule.
    """
    fn=bodies(original,'font_arg')[0];body=fn['body'][1:-1]
    typed=body
    remove=['  let arg = cx.argument::<JsValue>(idx)?;\n  if arg.is_a::<JsNull, _>(cx){ return Ok(None) }\n',
            '  let font_desc = cx.argument::<JsObject>(idx)?;\n',
            '  let families = strings_at_key(cx, &font_desc, "family")?;\n',
            '  let canonical = string_for_key(cx, &font_desc, "canonical")?;\n',
            '  let variant = string_for_key(cx, &font_desc, "variant")?;\n',
            '  let size = float_for_key(cx, &font_desc, "size")?;\n',
            '  let feat_obj:Handle<JsObject> = font_desc.get(cx, "features")?;\n  let features = font_features(cx, &feat_obj)?;\n']
    for s in remove:assert s in typed;typed=typed.replace(s,'',1)
    for before,after in [('float_for_key(cx, &font_desc, "weight")?','weight'),('string_for_key(cx, &font_desc, "style")?.as_str()','style'),('string_for_key(cx, &font_desc, "stretch")?.as_str()','stretch'),('opt_float_for_key(cx, &font_desc, "lineHeight")','line_height')]:
        assert before in typed;typed=typed.replace(before,after,1)
    typed=typed.replace('  Ok(match families[0] == ""{','  match families[0] == ""{',1)
    assert typed.endswith('  })\n');typed=typed[:-5]+'  }\n'
    return {'name':'font_spec','line':fn['line'],'original':body,'typed':typed}

def core_spec(original,bodies):
    """Generate sole original typed FontSpec packing; no matching/shaping/ownership changes.

    Returns source; no units of its own. Original f32 ratio and empty family retention stay.
    """
    item=definition(original,bodies)
    return f'''
/// Pack original parsed font fields; size/line_height are f32 canvas units, weight
/// original numeric weight, remaining values unitless. Returns None for empty first
/// family, otherwise owned FontSpec. Adapters supply original parser fields/nonempty
/// family array; no callbacks/errors or Skia handles, usable before owner borrow.
/// Upstream: src/typography.rs:{item['line']} font_arg, only Neon field reads separated.
pub fn font_spec(families:Vec<String>, canonical:String, variant:String, size:f32,
                 weight:f32, style:&str, stretch:&str, line_height:Option<f32>,
                 features:Vec<(String,i32)>) -> Option<FontSpec> {{{item['typed']}}}
'''

def node_spec(source,original,bodies):
    """Preserve Node descriptor reads/order/null behavior; forward typed fields to sole core."""
    old=bodies(original,'font_arg')[0]['body']
    new=old.replace('Weight::from(float_for_key(cx, &font_desc, "weight")? as i32)','float_for_key(cx, &font_desc, "weight")?')
    new=new.replace('let slant = to_slant(string_for_key(cx, &font_desc, "style")?.as_str())','let style = string_for_key(cx, &font_desc, "style")?')
    new=new.replace('let width = to_width(string_for_key(cx, &font_desc, "stretch")?.as_str())','let stretch = string_for_key(cx, &font_desc, "stretch")?')
    new=new.replace('\n    .map(|pt_size| pt_size / size)','')
    start=new.index('  Ok(match families[0] == ""{')
    new=new[:start]+'''  Ok(canvas_core::typography::font_spec(families,canonical,variant,size,weight,
                                         &style,&stretch,line_height,features))
}'''
    assert old in source
    return source.replace(old,new,1).replace('use skia_safe::font_style::Weight;\n','')
