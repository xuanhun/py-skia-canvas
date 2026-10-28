"""Controlled original font-file/metadata extraction; never loads fonts during validation."""

def load_definition(original,bodies):
    """Return original read/decode/match blocks and owned-Typeface boundary substitutions.

    Source text only; file paths unitless, bytes unchanged. Original Windows WOFF
    decode functions and all fallback/order rules stay intact; errors become Rust strings.
    """
    fn=bodies(original,'addFamily')[0];body=fn['body']
    start=body.index('    let path = Path::new(&filename);')
    split=body.index('    match typeface {',start)
    end=body.index('\n  }\n\n  Ok(results.upcast())',split)
    load=body[start:split];match=body[split:end]
    some_start=match.index('      Some(font) => {\n');some_end=match.index('      None => {',some_start)
    some=match[some_start:some_end]
    registration=some[len('      Some(font) => {\n'):some.rindex('      },')]
    typed=load+match.replace(some,'      Some(font) => Ok(font),\n',1)
    typed=typed.replace('cx.throw_error(', 'Err(')
    begin=original.index('#[cfg(target_os = "windows")]\nuse allsorts::{')
    finish=original.index('};\n',begin)+3
    return {'name':'load_typeface','line':fn['line'],'original':load+match,'typed':typed,'registration':registration,'imports':original[begin:finish]}

def core_loading(original,bodies):
    """Emit sole original font-file loader; returns original owner-thread Typeface/error.

    Paths/bytes unchanged, no Unicode/path normalization; no language or GPU objects.
    """
    item=load_definition(original,bodies)
    return f'''
/// Read/decode original font file, returning owned Typeface or original I/O/decode error.
/// filename is the caller's path string; no units or normalization. Windows WOFF/WOFF2
/// conversion and fallback are retained verbatim. Uses current thread's FontLibrary;
/// Typeface remains on its owner, no Send/Sync changes. Upstream: font_library.rs:{item['line']}.
pub fn load_typeface(filename:&str) -> Result<Typeface,String> {{
{item['imports']}
{item['typed']}
}}
'''

def node_loading(source,original,bodies):
    """Forward only read/decode into core, preserving metadata-before-register/partial commit.

    Returns source text, no execution. Original JS array sizing/filtered-path slots stay.
    """
    item=load_definition(original,bodies)
    replacement='    let font = canvas_core::font_library::load_typeface(filename).or_else(|e| cx.throw_error(e))?;\n'+item['registration']
    source=source.replace('lib.new_from_data(&bytes)', 'lib.mgr.new_from_data(&bytes, None)')
    assert item['original'] in source
    source=source.replace(item['original'],replacement,1)
    return source.replace('use std::fs;\n','').replace('use std::path::Path;\n','').replace(item['imports'],'')

def metadata_definition(original,bodies):
    """Return original Typeface style/alias values separated from JS string/number allocation.

    Metadata names unitless, weight original numeric value; no new font matching policy.
    """
    fn=bodies(original,'typeface_details')[0];body=fn['body']
    start=body.index('  let style = font.font_style();');end=body.index('  let dict = JsObject::new(cx);',start)
    block=body[start:end]
    typed=block.replace('  let filename = cx.string(filename);\n','')
    typed=typed.replace('cx.string(match alias{','match alias{').replace('  });\n','  };\n',1)
    typed=typed.replace('cx.number(*style.weight() as f64)','*style.weight() as f64')
    typed=typed.replace('cx.string(from_slant(style.slant()))','from_slant(style.slant())')
    typed=typed.replace('cx.string(from_width(style.width()))','from_width(style.width())')
    return {'name':'typeface_metadata','line':fn['line'],'original':block,'typed':typed}

def core_metadata(original,bodies):
    """Emit original font metadata tuple; names/weight unchanged, no callbacks/native transfer."""
    item=metadata_definition(original,bodies)
    return f'''
/// Return original (family, weight, style, width) values for a Typeface and optional alias.
/// Names are unitless strings, weight original numeric value. Returns owned metadata;
/// font stays on current owner, no callbacks/errors or matching policy changes.
/// Upstream: typography.rs:{item['line']} (typeface_details), JS allocations separated only.
pub fn typeface_metadata(font:&Typeface, alias:Option<String>) -> (String,f64,String,String) {{
{item['typed']}  (family,weight,slant,width)
}}
'''

def node_metadata(source,original,bodies):
    """Keep original Node result fields/allocation; fetch values from sole core metadata helper."""
    item=metadata_definition(original,bodies)
    replacement='''  let (family, weight, slant, width) = canvas_core::font_library::typeface_metadata(font, alias);
  let filename = cx.string(filename);
  let family = cx.string(family);
  let weight = cx.number(weight);
  let slant = cx.string(slant);
  let width = cx.string(width);

'''
    assert item['original'] in source
    return source.replace(item['original'],replacement,1)
