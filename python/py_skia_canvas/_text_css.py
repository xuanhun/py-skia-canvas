"""Original CSS text parser/value boundaries; no native fonts, layout or GPU objects."""
import math,re
from . import _native,undefined
from ._font_css import _key,_split,_SIZE,_WS,_STRETCH
from ._transform import _SPACE,parse_float,number_string
from ._text_css_data import FEATURES,ALTERNATES

_VARIANTS={}
_PROTOTYPE_KEYS={'constructor','__defineGetter__','__defineSetter__','hasOwnProperty','__lookupGetter__','__lookupSetter__','isPrototypeOf','propertyIsEnumerable','toString','valueOf','__proto__','toLocaleString'}
class _Inherited:
    """Ordinary cache Object.prototype member marker; no public result/native ownership.

    Source css.js cache.variant[str]. Only its later Native object-downcast/string
    error is observable here; custom prototype/host mutation remains unaudited.
    """
    __slots__=('function',)
    def __init__(self,key):
        """Record original function-vs-prototype-object kind, unitless/any thread."""
        self.function=key!='__proto__'

def truth(value):
    """Original JS !!value for ordinary Python primitive/array/object inputs.

    Returns bool, no errors/native state. Objects including empty list/dict are true;
    None/undefined/zero/NaN/empty string false. Source context.js flag setters.
    """
    if value is None or value is undefined:return False
    if isinstance(value,(bool,int,float)):return value!=0 and not(isinstance(value,float) and math.isnan(value))
    if isinstance(value,str):return bool(value)
    return True

def spacing(value):
    """Original parseFlexibleSize descriptor or None; raw f64 and px f64, unit string.

    Source css.js:122, RegExp string coercion uses same ordinary key conversion.
    Unsupported relative-unit px stays NaN for original Native field error, no affinity.
    """
    match=_SIZE.search(_key(value))
    if match:
        size,unit=parse_float(match[1]),match[2]
        scale=1 if unit=='px' else 1/.75 if unit=='pt' else 16 if unit=='pc' else 96 if unit=='in' else 96/2.54 if unit=='cm' else 96/25.4 if unit=='mm' else 96/25.4/4 if unit=='q' else math.nan
        return {'size':size,'unit':unit,'px':size*scale}
    return None

def stretch(value):
    """Original parseStretch label or undefined; unitless, no native state/errors.

    Source css.js:138 parseStretch; original non-multiline regex requires the full value.
    """
    match=_STRETCH.fullmatch(_key(value))
    return match[0] if match else undefined

def _integer(value):
    """Original parseInt(text,10) prefix for alternate parameters, f64/NaN, no units.

    Source css.js:parseVariant; clamping/stringification occurs in original order.
    """
    m=re.match(r'[+-]?[0-9]+',value.lstrip(_SPACE))
    if not m:return math.nan
    try:return float(int(m[0]))
    except OverflowError:return -math.inf if m[0].startswith('-') else math.inf

def variant(value):
    """Original parseVariant cache/descriptor or original parser Error/TypeError.

    Feature tags/values unitless, Python values only. Source css.js:148; normal's
    original variants key is retained, not repaired to variant. Native field errors
    occur at the separate setter boundary, no font mutation during parsing.
    """
    key=_key(value)
    if key in _VARIANTS:return _VARIANTS[key]
    if key in _PROTOTYPE_KEYS:return _Inherited(key)
    if value is None or value is undefined:raise _native.Error('First argument should be a string')
    if not isinstance(value,str):raise TypeError('str.split is not a function')
    variants=[];features={'on':[],'off':[]}
    for token in _split(value,_WS+'+',r'/\s+/'):
        if token=='normal':return {'variants':[token],'features':{'on':[],'off':[]}}
        if token in FEATURES:
            for feat in FEATURES[token]:
                if feat.startswith('-'):features['off'].append(feat[1:])
                else:features['on'].append(feat)
            variants.append(token)
        elif token in _PROTOTYPE_KEYS:
            raise TypeError('featureMap[token].forEach is not a function')
        elif m:=re.search(r'([A-Za-z0-9_\-]+)\((.*?)\)',token):
            sub_pattern=ALTERNATES.get(m[1]);raw=_integer(m[2]);sub_value=math.nan if math.isnan(raw) else max(0.,min(99.,raw))
            if sub_pattern is None:raise TypeError("Cannot read properties of undefined (reading 'replace')")
            sub_text=number_string(sub_value)
            expanded=sub_pattern.replace('##',('0'+sub_text) if sub_value<10 else sub_text,1).replace('#',number_string(math.nan if math.isnan(sub_value) else min(9.,sub_value)),1).split(' ')
            feat=expanded[0]
            if len(expanded)==1:features['on'].append(feat)
            else:features[feat]=_integer(expanded[1])
            variants.append(m[1]+'('+sub_text+')')
        else:raise _native.Error('Invalid font variant "'+token+'"')
    result={'variant':' '.join(variants),'features':features};_VARIANTS[key]=result
    return result

def decoration(value):
    """Original parseTextDecoration descriptor, including first-only whitespace collapse.

    Text is unitless, thickness original f64 raw/px/unit descriptor or undefined.
    Non-string ->empty text, original substring/priority and last-token behavior;
    no native font/layout state or errors. Source css.js:182 parseTextDecoration.
    """
    style='solid';line='none';color='currentColor';inherit='auto';thickness=undefined
    text=re.sub(_WS+'+',' ',(value if isinstance(value,str) else '').strip(_SPACE),count=1)
    for token in text.split(' '):
        if re.search('solid|double|dotted|dashed|wavy',token):style=token
        elif re.search('none|initial|revert(-layer)?|unset',token):line='none'
        elif re.search('underline|overline|line-through',token):line=token
        elif (size:=spacing(token)) is not None:thickness=size
        elif re.search('auto|from-font',token):inherit=token
        else:color=token
    return {'style':style,'line':line,'color':color,'thickness':thickness,'inherit':inherit,'str':text}
