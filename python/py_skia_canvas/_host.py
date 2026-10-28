"""Explicit Python host profile accepted 2026-10-28; never starts Node or fakes Sharp."""
from . import _native,undefined
def sharp(options=undefined,canvas=False):
    """Original optional Node Sharp dependency failure under standalone Python profile.
    Unitless options, raises original Error; no object/stream placeholder or native work.
    Canvas null destructuring fails first as original. Sources canvas.js/imagery.js:getSharp.
    """
    if canvas and options is None:raise TypeError("Cannot destructure property 'page' of '(intermediate value)(intermediate value)(intermediate value)' as it is null.")
    raise _native.Error("Cannot find module 'sharp' (try running `npm install sharp` first)")
