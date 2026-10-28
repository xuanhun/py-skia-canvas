"""Original Context text properties forwarding to sole Rust core state, no layout."""
import json,math
import warnings
from . import _text,undefined
from . import _text_css as css

class PropertyRemoved(UserWarning):
    """Original process.emitWarning category; no units/native resources, context.js textTracking."""

def _tracking_get(self):
    """Original setter-only removed property reads undefined; no state/owner/GPU access."""
    return undefined

def _tracking_set(self,value):
    """Emit original PropertyRemoved warning, ignore value without changing letterSpacing.
    Any thread, None/warning-filter exception; no native state or GPU access. Source
    context.js:textTracking setter. Fresh registry preserves per-assignment default warning.
    """
    warnings.warn_explicit('The .textTracking property has been removed; use the .letterSpacing property instead',PropertyRemoved,__file__,0,registry={})

def _property(name,kind):
    """Create original getter/setter descriptor forwarding one shared implementation.

    Names/flags/features unitless, spacing CSS/canvas units. All native access owner-only;
    returns owned Python values/None or original TypeError/Error/owner RuntimeError.
    Source context.js:fontStretch/textAlign/textBaseline/direction/letterSpacing/
    wordSpacing/fontVariant/fontHinting/textWrap/textDecoration and corresponding API.
    """
    def get(self):
        """Return original native value snapshot, owner-only; no callback/native transfer."""
        method=getattr(self._native,'text_'+kind)
        return method() if kind in ('variant','decoration') else method(name)
    def set(self,value):
        """Apply original JS parser/coercion before native borrow, no font/layout rewrite."""
        get(self)  # Validate owner without Python callbacks during a registry borrow.
        if kind=='name':
            if name=='fontStretch':
                value=css.stretch(value)
                self._native.text_name(name,None if value is undefined else _text(value))
            else:
                if not isinstance(value,str):raise TypeError('Expected a string for `'+name+'`')
                self._native.text_name(name,_text(value))
        elif kind=='flag':self._native.text_flag(name,css.truth(value))
        elif kind=='spacing':
            desc=css.spacing(value)
            if desc is None:self._native.text_spacing(name);return
            for key in ('size','px'):
                if not math.isfinite(desc[key]):raise TypeError('Exptected a numerical value for "'+key+'"')
            self._native.text_spacing(name,desc['size'],desc['unit'],desc['px'])
        elif kind=='decoration':
            desc=css.decoration(value)
            def owned(item):
                """Encode only owned language fields before borrow; original undefined/null
                and nonfinite thickness tags preserve lazy field-read validation order.
                """
                if item is undefined:return None
                if isinstance(item,str):return _text(item)
                if isinstance(item,float) and not math.isfinite(item):return {'$number':'NaN' if math.isnan(item) else 'Infinity' if item>0 else '-Infinity'}
                if isinstance(item,dict):return {k:owned(v) for k,v in item.items()}
                return item
            self._native.text_decoration(json.dumps(owned(desc),allow_nan=False))
        else:
            desc=css.variant(value)
            if isinstance(desc,css._Inherited) and desc.function:raise TypeError('failed to downcast any to object')
            if not isinstance(desc,dict) or not isinstance(desc.get('variant'),str):raise TypeError('Exptected a string for "variant"')
            for key,val in desc['features'].items():
                if key not in ('on','off') and not math.isfinite(val):raise TypeError('Exptected a numerical value for "'+key+'"')
            self._native.text_variant(_text(desc['variant']),json.dumps(desc['features'],allow_nan=False))
    status='decoration-api-status.json' if kind=='decoration' else 'text-state-api-status.json'
    return property(get,set,doc='Original '+name+' property; owner TLS, typed values/snapshots. Source context.js/context/api.rs; see '+status+' for units/errors.')

def install(cls):
    """Attach original text-state descriptors to Context type, no instances/state/resources.

    Unitless names, returns None; module initialization only. Source context.js properties.
    """
    for name,kind in [('textAlign','name'),('textBaseline','name'),('direction','name'),('fontStretch','name'),('letterSpacing','spacing'),('wordSpacing','spacing'),('fontVariant','variant'),('fontHinting','flag'),('textWrap','flag'),('textDecoration','decoration')]:
        setattr(cls,name,_property(name,kind))
    cls.textTracking=property(_tracking_get,_tracking_set)
