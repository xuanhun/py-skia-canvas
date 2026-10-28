"""Original typography.js TextMetrics value facade; no font/shaping/layout calculation."""
from types import MappingProxyType
from . import _MISSING,undefined

_FIELDS={'width','actualBoundingBoxLeft','actualBoundingBoxRight','actualBoundingBoxAscent','actualBoundingBoxDescent','fontBoundingBoxAscent','fontBoundingBoxDescent','emHeightAscent','emHeightDescent','hangingBaseline','alphabeticBaseline','ideographicBaseline','lines'}

class TextMetrics:
    """Original shallow, read-only initial fields; nested lists/maps retain normal mutability.

    Distances canvas units, line indices UTF-16. Python-owned data only, any thread;
    native Context/font lifetimes are independent. Source typography.js:41 TextMetrics.
    Nested JS plain objects use ordinary Python mappings, with original key names.
    """
    __slots__=('_data','_values','_initial')
    def __init__(self,values=_MISSING,*extra):
        """Copy enumerable top fields once, preserve child references; no args/null ->empty.

        Ordinary mapping/TextMetrics, array and string inputs follow original for-in;
        string keys are UTF-16 code-unit indices. No units conversion/native ownership.
        Extra args ignored; arbitrary custom prototype/subclass contracts remain scoped.
        Source typography.js:TextMetrics constructor/readOnly helper in neon.js.
        """
        if isinstance(values,TextMetrics):data=dict(values._values)
        elif isinstance(values,dict):
            from ._font_css import _key
            data={_key(k):v for k,v in values.items()}
        elif isinstance(values,(list,tuple)):data={str(i):v for i,v in enumerate(values)}
        elif isinstance(values,str):
            raw=values.encode('utf-16-le','surrogatepass')
            data={str(i//2):raw[i:i+2].decode('utf-16-le','surrogatepass') for i in range(0,len(raw),2)}
        else:data={}
        object.__setattr__(self,'_data',data)
        object.__setattr__(self,'_values',MappingProxyType(data))
        object.__setattr__(self,'_initial',frozenset(data))
    def __getattr__(self,name):
        """Read original owned field; absent standard metrics ->undefined, other names ->AttributeError.

        No units/errors beyond missing Python attributes, no owner affinity.
        """
        if name in self._data:return self._data[name]
        if name in _FIELDS:return undefined
        raise AttributeError(name)
    def __setattr__(self,name,value):
        """Original initial-field TypeError, new ordinary fields remain writable.

        Values retained by reference without calculation/native state. Any thread.
        Source neon.js:readOnly Object.defineProperty writable:false.
        """
        if name in self._initial:raise TypeError("Cannot assign to read only property '"+name+"' of object '#<TextMetrics>'")
        if name in self.__slots__:raise AttributeError('Private TextMetrics storage is read-only')
        self._data[name]=value
    def __delattr__(self,name):
        """Original nonconfigurable initial-field TypeError, added fields can be deleted.

        No units/native references. Source neon.js:readOnly default configurable:false.
        """
        if name in self._initial:raise TypeError("Cannot delete property '"+name+"' of #<TextMetrics>")
        if name in self.__slots__:raise AttributeError('Private TextMetrics storage is read-only')
        self._data.pop(name,None)
