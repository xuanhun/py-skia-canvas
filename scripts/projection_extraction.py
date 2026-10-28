"""Controlled extraction of original projection and string-number blocks; never renders."""

def projection(original, bodies):
    """Return original/typed projection block and unchanged JS array allocation.

    Text-only source spans, no units/native objects. Only result/error allocation changes;
    basis/quad expansion, solver call order and original error formatting remain exact.
    """
    fn=bodies(original,'createProjection')[0];body=fn['body']
    block=body[body.index('  let basis:'):body.rfind('}')]
    start=block.index('      let array = JsArray::new(');end=block.index('    },',start)
    allocation=block[start:end]
    typed=block.replace(allocation,'      Ok(projection)\n',1).replace('_ => cx.throw_type_error(format!(','_ => Err(format!(',1)
    return {'name':'createProjection','original':block,'typed':typed,'allocation':allocation,'line':fn['line']}

def core_projection(original,bodies):
    """Generate unique original core projection, returning owned Matrix/original error.

    Geometry f32 canvas units; Context bounds are owner-local, solver unchanged.
    """
    item=projection(original,bodies)
    return f'''
/// Original projection from coordinate basis to output quad, f32 canvas units.
/// Zero/one/two basis points expand using current bounds/size/edges; destination
/// one/two points expand as size/edges. Returns owned Skia Matrix or original error.
/// Does not modify Context/CTM; owner thread only, no GPU ownership transfer.
/// Upstream: src/context/api.rs:{item['line']}; only JS allocation/error boundary changes.
pub fn createProjection(this:&Context2D, dst:Vec<Point>, src:Vec<Point>) -> Result<Matrix,String> {{
{item['typed']}}}
'''

def node_projection(source,original,bodies):
    """Forward original Node projection to sole core, retaining Node argument/return parsing.

    Returns source text; original units/error/allocation/thread policy unchanged.
    """
    item=projection(original,bodies);fn=bodies(source,'createProjection')[0]['text']
    replacement='  let projection = canvas_core::context::operations::createProjection(&this, dst, src).or_else(|e| cx.throw_type_error(e))?;\n'+item['allocation']
    changed=fn.replace(item['original'],replacement,1)
    assert changed!=fn
    return source.replace(fn,changed,1)

def number_string(original,bodies):
    """Return original Rust string parse branch; owned text/line, no parsing at runtime here.

    The native language binding keeps value type tests/finite filtering; one core owns
    original empty/base-prefix/u64/f64 string grammar. Source: utils.rs:_as_double.
    """
    fn=bodies(original,'_as_double')[0];body=fn['body']
    start=body.index('      if let Some(s) = s.strip_prefix("0x")')
    end=body.index('    })',start)
    block=body[start:end]
    return {'name':'parse_number_string','original':block,'typed':block,'line':fn['line']+body[:start].count('\n')}

def core_number_string(original,bodies):
    """Emit original Rust string→Option<f64> branch without language object tests.

    Unitless parsing, owner-independent; returns None on original parse/u64 errors.
    Finite filtering/f32 conversion stay at original adapter point after parsing.
    """
    item=number_string(original,bodies)
    return f'''
/// Original _as_double string branch, unitless f64 parsing with original prefix/u64 rules.
/// Empty string ->0; errors ->None. NaN/Infinity may be parsed and are filtered by caller
/// before original f32 cast. Stateless/any thread, no Python/Node/Skia ownership.
/// Upstream: src/utils.rs:{item['line']}; original statements retained verbatim.
pub fn parse_number_string(s:&str) -> Option<f64> {{
{item['typed']}}}
'''

def node_number_string(source,original,bodies):
    """Replace only original Node string parsing statements with shared core forwarding.

    Original JsString allocation, primitive tests, finite filtering and casts are retained.
    """
    item=number_string(original,bodies)
    assert item['original'] in source
    return source.replace(item['original'],'      canvas_core::utils::parse_number_string(&s)\n',1)
