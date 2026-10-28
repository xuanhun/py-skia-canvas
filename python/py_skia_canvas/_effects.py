"""Original CSS filter/state facade only; all effects/blending/drawing live in shared core."""
import json,math,re
from . import _native,undefined,_text
from ._font_css import _split,_size,_WS
from ._transform import _SPACE,parse_float,string_number
from ._text_api import string
from ._imagery import _STRICT

_PLAIN=re.compile(r'(blur|hue-rotate|brightness|contrast|grayscale|invert|opacity|saturate|sepia)\((.*?)\)')
_SHADOW=re.compile(r'drop-shadow\((.*)\)')
_PERCENT=re.compile(r'^[+-]?[0-9]+%$')
_ANGLE=re.compile(r'([0-9\.]+)(deg|g?rad|turn)')

def parse_filter(value):
    """Port original css.js:parseFilter/parsePercentage/parseAngle without rendering.

    Returns owned canonical/ordered filters or None (ignored assignment). Lengths default
    to original 16px em, hue degrees, amounts unitless f64 until native f32 boundary.
    Original null/nonstring/tokenizer errors propagate; no native objects/owner affinity.
    """
    if value is None or value is undefined:raise _native.Error('First argument should be a string')
    if not isinstance(value,str):raise TypeError('str.split is not a function')
    filters={};canonical=[]
    try:tokens=_split(value,_WS+'+',r'/\s+/')
    except ValueError as error:raise _native.Error(str(error)) from None
    for spec in tokens:
        shadow=_SHADOW.search(spec)
        if shadow:
            args=re.split(_WS+'+',shadow[1].strip(_SPACE));lengths=args[:3];color=' '.join(args[3:]);dims=[_size(s) for s in lengths];dims=[n for n in dims if math.isfinite(n)]
            if len(dims)==3 and color:
                filters['drop-shadow']=[*dims,color]
                canonical.append('drop-shadow('+' '.join(lengths)+' '+color.replace(' ','')+')')
        else:
            plain=_PLAIN.search(spec)
            if plain is None:continue
            kind,arg=plain[1],plain[2]
            if kind=='blur':amount=_size(arg)
            elif kind=='hue-rotate':
                match=_ANGLE.search(arg.strip(_SPACE))
                if match is None:amount=math.nan
                else:
                    n,unit=parse_float(match[1]),match[2]
                    amount=n if unit=='deg' else 360*n/(2*math.pi) if unit=='rad' else 360*n/400 if unit=='grad' else 360*n
            else:
                token=arg.strip(_SPACE)
                amount=parse_float(token)/100 if _PERCENT.fullmatch(token) else parse_float(arg) if not math.isnan(string_number(arg)) else math.nan
            if math.isfinite(amount):
                filters[kind]=amount
                canonical.append(kind+'('+arg.strip(_SPACE)+')')
    return {'canonical':'none','filters':filters} if value.strip(_SPACE)=='none' else {'canonical':' '.join(canonical),'filters':filters} if canonical else None

def _property(name,kind):
    """Create original effect accessor using shared native owner State, no draw algorithms.
    Returned values/units/errors documented below. Source context.js effect accessors.
    """
    def get(self):
        """Return owned current original effect value; owner-only/RuntimeError.
        Alpha/style unitless, shadow offsets/blur canvas units, filter CSS string.
        """
        method=self._native.effects_filter if kind=='filter' else self._native.effects_color if kind=='color' else self._native.effects_number if kind=='number' else self._native.effects_name
        return method() if kind in ('filter','color') else method(name)
    def set(self,value):
        """Apply original language reads before native borrow, None/original errors.

        Owner checked first; nonfinite numeric bail keeps default/STRICT behavior (U+FE0F
        retained after original rustError substr(1)); plain object host callbacks pending.
        Original units/defaults/State operation source context/api.rs effect functions.
        """
        get(self)
        if kind=='filter':
            desc=parse_filter(value)
            if desc is not None:
                def owned(item):
                    """Original Neon JsString.value UTF-16 replacement at native field reads.
                    Owned descriptors only, no units/callbacks; preserve parser's raw result.
                    """
                    if isinstance(item,str):return _text(item)
                    if isinstance(item,list):return [owned(v) for v in item]
                    if isinstance(item,dict):return {k:owned(v) for k,v in item.items()}
                    return item
                self._native.effects_filter(json.dumps(owned({**desc,'order':list(desc['filters'])}),allow_nan=False,ensure_ascii=True))
        elif kind=='color':
            # Original color_in calls ordinary object.toString, primitives are ignored.
            text=string(value) if isinstance(value,(str,list,tuple,dict)) else None
            self._native.effects_color(text)
        elif kind=='number':
            number=_native._text_width(value)
            if number is None:
                if _STRICT:raise TypeError('\ufe0fExpected a number for `'+name+'` as 1st arg')
                return
            self._native.effects_number(name,number)
        else:
            field='fitStyle' if name=='lineDashFit' else name
            if not isinstance(value,str):raise TypeError('Expected a string for `'+field+'`')
            self._native.effects_name(name,_text(value))
    return property(get,set)

def install(cls):
    """Bind original filter/shadow/composite/alpha/dashFit names to shared native State.
    Units and errors belong to original accessors, no independent policy or rendering.
    """
    for name,kind in [('filter','filter'),('shadowColor','color'),('shadowBlur','number'),('shadowOffsetX','number'),('shadowOffsetY','number'),('globalAlpha','number'),('globalCompositeOperation','name'),('lineDashFit','name')]:setattr(cls,name,_property(name,kind))
