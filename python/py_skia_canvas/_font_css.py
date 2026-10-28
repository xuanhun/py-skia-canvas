"""Language port of fixed css.js:parseFont/parseSize/parseWeight, with original tokenizer.

Only Python values/cache; no fonts, matching, shaping or GPU objects. Derived tokenizer
sources/versions/licenses are recorded in references/css and THIRD_PARTY_NOTICES.md.
"""
import math
import re
from . import undefined
from ._transform import _SPACE, parse_float, number_string

_WS='['+_SPACE+']'
_SIZE=re.compile(r'^(\-?[0-9\.]+)(px|pt|pc|in|cm|mm|%|em|ex|ch|rem|q)')
_NAMED=re.compile(r'(?:xx?-)?small|smaller|medium|larger|(?:xx?-)?large|normal')
_WEIGHT=re.compile(r'^(1000|[0-9]{1,3})$')
_STRETCH=re.compile(r'^(normal|(semi-|extra-|ultra-)?(condensed|expanded))$')
_SIZES={'xx-small':3/5,'x-small':3/4,'small':8/9,'smaller':8/9,'large':6/5,'larger':6/5,'x-large':3/2,'xx-large':2/1,'normal':1.2}
_WEIGHTS={'lighter':300,'normal':400,'bold':700,'bolder':800}
_CACHE={}

def _split(string,separator,separator_text):
    """Original string-split-by1.0.0 with parenthesis3.1.8 flat parse/stringify.

    String/regex inputs only, unitless owned list; original escape joining, bracket
    pass order and reference errors retained. No native ownership or thread affinity.
    Source: both packages index.js, default options used by css.js:parseFont.
    """
    refs=[string]
    for pair in ('[]','()','{}','<>','""',"''",'``','“”','«»'):
        opening,closing=pair
        pattern=re.compile(re.escape(opening)+'[^'+re.escape(opening+closing)+']*'+re.escape(closing))
        ids=[]
        for i in range(len(refs)):
            value=refs[i];count=0
            while True:
                match=pattern.search(value)
                if match is None:break
                refs.append(match[0][1:-1]);ref=len(refs)-1;ids.append(ref)
                value=value[:match.start()]+'___'+str(ref)+'___'+value[match.end():]
                if count>10000:raise ValueError('References have circular dependency. Please, check them.')
                count+=1
            refs[i]=value
        for i,value in enumerate(refs):
            for ref in reversed(ids):
                value=value.replace('___'+str(ref)+'___',opening+'___'+str(ref)+'___'+closing)
            refs[i]=value
    parts=re.split(separator,refs[0]);clean=[];i=0
    while i<len(parts):
        prev=parts[i]
        if prev.endswith('\\') and not prev.endswith('\\\\'):
            clean.append(prev+separator_text+(parts[i+1] if i+1<len(parts) else 'undefined'));i+=2
        else:clean.append(prev);i+=1
    result=[];pattern=re.compile(r'___([0-9]+)___')
    for part in clean:
        refs[0]=part;count=0
        while True:
            match=pattern.search(part)
            if match is None:break
            if count>10000:raise ValueError('Circular references in '+','.join(refs))
            count+=1;ref=int(match[1])
            if ref>=len(refs):raise ValueError('Reference '+match[1]+'is undefined')
            new=part[:match.start()]+refs[ref]+part[match.end():]
            if new==part:break
            part=new
        result.append(part)
    return result

def _size(text,em_size=16):
    """Original parseSize unit conversion to f64 CSS px, invalid ->NaN, any thread.

    Source css.js:100 parseSize; multiplication/order and permissive prefix matching retained.
    """
    match=_SIZE.search(text)
    if match:
        size,unit=parse_float(match[1]),match[2]
        scale=1 if unit=='px' else 1/.75 if unit=='pt' else em_size/100 if unit=='%' else 16 if unit=='pc' else 96 if unit=='in' else 96/2.54 if unit=='cm' else 96/25.4 if unit=='mm' else 96/25.4/4 if unit=='q' else em_size if re.search('r?em',unit) else math.nan
        return size*scale
    match=_NAMED.search(text)
    return em_size*_SIZES.get(match[0],1.) if match else math.nan

def _key(value):
    """Ordinary JS property-key coercion for primitive/array parser cache access.

    Unitless owned string, any thread. Source css.js:cache.font[str]; arbitrary host,
    proxy/prototype and custom object conversion remain outside this input profile.
    """
    if isinstance(value,str):return value
    if value is undefined:return 'undefined'
    if value is None:return 'null'
    if isinstance(value,bool):return 'true' if value else 'false'
    if isinstance(value,(int,float)):return number_string(value)
    if isinstance(value,(list,tuple)):
        return ','.join('' if v is None or v is undefined else _key(v) for v in value)
    return '[object Object]'

def parse_font(value):
    """Original font descriptor/cache or None for silently ignored invalid values.

    Sizes/leading are f64 CSS px until original native f32 conversion. Returns private
    Python descriptor; no native/font ownership. Source css.js:26 parseFont and
    css.js:142 parseWeight; native errors remain at the owner-only property boundary.
    """
    key=_key(value)
    if key in _CACHE:return _CACHE[key]
    result=None
    try:
        if not isinstance(value,str) or not value:raise ValueError('Invalid string')
        font={'style':'normal','variant':'normal','weight':'normal','stretch':'normal'}
        text=re.sub(_WS+r'*/\*s','/',value,count=1)
        tokens=_split(text,_WS+'+',r'/\s+/')
        while tokens:
            token=tokens.pop(0)
            if not token:break
            kind='style' if token in ('normal','italic','oblique') else 'variant' if token in ('normal','small-caps') else 'stretch' if _STRETCH.fullmatch(token) else 'weight' if token in _WEIGHTS or _WEIGHT.fullmatch(token) else 'size' if _NAMED.search(token) or _SIZE.search(token) else None
            if kind in ('style','variant','stretch','weight'):font[kind]=token;continue
            if kind!='size':raise ValueError('Unrecognized font attribute')
            sizes=_split(token,'/','/');em_size=sizes[0];leading=sizes[1] if len(sizes)>1 else ''
            size=_size(em_size);line_height=_size(re.sub(r'([0-9])$',r'\1em',leading),size) if leading else None
            weight=int(font['weight']) or math.nan if _WEIGHT.fullmatch(font['weight']) else _WEIGHTS.get(font['weight'],math.nan)
            family=[re.sub(r'''^(['"])(.*?)\1$''',r'\2',nm) for nm in _split(' '.join(tokens),_WS+'*,'+_WS+'*',r'/\s*,\s*/')]
            if not math.isfinite(size) or line_height is not None and not math.isfinite(line_height) or not math.isfinite(weight) or not family:raise ValueError('Invalid font fields')
            style,variant,stretch=font['style'],font['variant'],font['stretch']
            canonical=[style,variant if variant!=style else '',number_string(weight) if weight not in (variant,style) else '',stretch if stretch not in (variant,style,weight) else '',number_string(size)+'px'+('/'+number_string(line_height)+'px' if line_height is not None else ''),', '.join('"'+nm+'"' if re.search(_WS,nm) else nm for nm in family)]
            result={**font,'size':size,'lineHeight':line_height,'weight':weight,'family':family,'features':{'on':['smcp','onum']} if variant=='small-caps' else {},'canonical':' '.join(p for p in canonical if p)}
            break
    except (ValueError,TypeError,OverflowError,RecursionError):
        result=None
    _CACHE[key]=result
    return result
