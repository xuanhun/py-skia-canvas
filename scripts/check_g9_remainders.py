"""Installed removed textTracking warning and DOMMatrix.dump numeric-content checks."""
import json,sys,warnings
from pathlib import Path
from unittest.mock import patch
from py_skia_canvas import Canvas,DOMMatrix,undefined
out=Path(sys.argv[1]);c=Canvas(32,24);x=c.getContext('2d');x.letterSpacing='2px'
with warnings.catch_warnings(record=True) as captured:
    warnings.simplefilter('always');x.textTracking=8;x.textTracking=None
warnings_=[dict(name=w.category.__name__,message=str(w.message)) for w in captured];dump=[]
def print_values(*args):
    """Capture numeric columns/typed-array data, not console styling; no pixel adjustment."""
    dump.append([[[v for v in column] for column in value] for value in args])
m=DOMMatrix([1,2,3,4,5,6]);before=list(m.toFloat64Array())
with patch('builtins.print',print_values):returned=m.dump() is None
out.write_text(json.dumps(dict(warnings=warnings_,spacing=x.letterSpacing,trackingUndefined=x.textTracking is undefined,dump=dump,before=before,after=list(m.toFloat64Array()),returned=returned))+'\n')
