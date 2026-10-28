"""Original typography.js FontLibrary singleton facade over caller-thread Rust TLS."""
import json
from . import _native, _MISSING, _text, undefined

def _flat(value):
    """Original [value].flat() one-layer array boundary; owned list, no units/native objects.

    Python tuple forwards to same JS Array representation. Source: typography.js:use.
    """
    return list(value) if isinstance(value,(list,tuple)) else [value]

def _entries(mapping):
    """Original ordinary string-key Object.entries order; canonical array indices first.

    Returns owned alias/value pairs, unitless, no font state. Non-string Python keys
    outside Record<string,...> profile ->TypeError; host/prototype keys audit pending.
    Source: typography.js:FontLibrary.use/Object.entries.
    """
    if any(not isinstance(k,str) for k in mapping): raise TypeError("Font family names must be strings")
    indices=[];other=[]
    for key,value in mapping.items():
        if key.isascii() and key.isdecimal() and str(int(key))==key and int(key)<4294967295:
            indices.append((key,value))
        else: other.append((key,value))
    indices.sort(key=lambda pair:int(pair[0]))
    return indices+other

class _FontLibrary:
    """Original singleton surface, querying/mutating each calling thread's own library.

    Holds no font/GPU references, so facade itself has no creation-thread affinity.
    All returned data is independent Python-owned snapshots. Source: typography.js.
    """
    __slots__=()

    @property
    def families(self):
        """Return original sorted/deduplicated family list snapshot; no units/errors.

        Current-thread system+registered names; Source: get families/font_library.rs:families.
        """
        return _native._font_families()

    def has(self,familyName=_MISSING,*extra):
        """Original case-sensitive membership; unitless string ->bool, extra args ignored.

        Missing/non-string ->original TypeError; current-thread TLS. Source: has/string_arg.
        """
        if not isinstance(familyName,str): raise TypeError("Expected a string for `familyName`")
        return _native._font_has(_text(familyName))

    def family(self,name=_MISSING,*extra):
        """Original family weight/width/style metadata snapshot or distinct undefined.

        Names/weights unitless, missing/non-string ->original TypeError, any calling thread.
        Source: typography.js:family and native family/family_details.
        """
        if not isinstance(name,str): raise TypeError("Expected a string for `familyName`")
        result=_native._font_family(_text(name))
        return undefined if result is None else json.loads(result)

    def _add(self,alias,paths):
        """Original filtered string files and pre-sized result slots; owned metadata list.

        Paths/aliases unitless strings; original Error on I/O/decode, partial commit kept.
        Earlier native strings compress into first slots, unused slots remain undefined.
        Caller-thread TLS only. Source: font_library.rs:addFamily/strings_in/JsArray sizing.
        """
        values=_flat(paths)
        files=[_text(value) for value in values if isinstance(value,str)]
        result=json.loads(_native._font_add(None if alias is None else _text(alias),files))
        return result+[undefined]*(len(values)-len(files))

    def use(self,*args):
        """Original file/list, alias+file/list or mapping registration; return metadata.

        File contents/path strings are passed unchanged to original Rust reader/decoder.
        Array entries of other types are filtered with original undefined slots. Ordinary
        string-key mapping preserves order and partial commits; errors are original Error/
        TypeError. Current calling thread owns registrations. Source: typography.js:use.
        """
        if len(args)==1 and args[0] is None:
            raise TypeError("Cannot convert undefined or null to object")
        if len(args)==1 and isinstance(args[0],dict):
            result={}
            for alias,paths in _entries(args[0]): result[alias]=self._add(alias,paths)
            return result
        if len(args)==1 and isinstance(args[0],(str,list,tuple)):
            return self._add(None,args[0])
        if len(args)==2 and isinstance(args[0],str) and isinstance(args[1],(str,list,tuple)):
            return self._add(args[0],args[1])
        raise _native.Error("Expected an array of file paths or an object mapping family names to font files")

    def reset(self,*extra):
        """Clear original current-thread user fonts/collections/cache, return undefined.

        System/generic mappings follow original reset; no native data moves to Python.
        Source: typography.js:reset/font_library.rs:reset. No parameters/units/errors.
        """
        _native._font_reset()
        return undefined

FontLibrary=_FontLibrary()
