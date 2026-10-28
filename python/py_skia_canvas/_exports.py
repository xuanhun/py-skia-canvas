"""Original canvas.js exportOptions and Promise facade; encoding is solely original core."""
import asyncio,base64,json,math,os,re,sys
from . import _native,undefined,_text
from ._imagery import number,field,pixelSize
from ._text_css import truth
from ._text_api import string

_MIMES={'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','webp':'image/webp','pdf':'application/pdf','svg':'image/svg+xml','raw':'application/octet-stream'}
_FORMATS={v:k for k,v in _MIMES.items() if k!='jpeg'}
_WARNED=set()

def options(canvas,extension='',filename='',opts=undefined):
    """Port original ordinary JS export validation in order; dimensions canvas units,
    quality 0–1, density positive integer, MSAA samples, page 1-based/negative. Returns
    owned normalized fields and fixed owner handles, original Error/TypeError/RangeError.
    Fractional valid page indexes/native host objects remain explicitly unsupported G0.
    Source canvas.js:exportOptions/Format; no render/codec/layout policies live here.
    """
    if isinstance(opts,(int,float)) and not isinstance(opts,bool):opts={'quality':opts}
    if opts is None:raise TypeError("Cannot destructure property 'page' of 'opts' as it is null.")
    values={k:field(opts,k) for k in ('page','quality','matte','density','msaa','outline','downsample','colorType')}
    image_format=field(opts,'format') if truth(filename) else undefined
    if isinstance(filename,os.PathLike):filename=os.fspath(filename)
    if not isinstance(filename,str) or not isinstance(extension,str):raise NotImplementedError('Export host objects are pending G0; paths accept str or os.PathLike')
    if not canvas.pages:canvas.getContext('2d')
    ext=image_format if truth(image_format) else re.sub(r'@\d+x$','',extension,flags=re.I) or os.path.splitext(filename)[1]
    mime=_MIMES.get(re.sub(r'^\.','',ext).lower()) if isinstance(ext,str) else None
    fmt=_FORMATS.get(mime or ext) if isinstance(ext,str) else None
    if not truth(ext):raise _native.Error("Cannot determine image format (use a filename extension or 'format' argument)")
    if not fmt:raise _native.Error(f'Unsupported file format "{string(ext)}" (expected "png", "jpg", "webp", "raw", "pdf", or "svg")')
    padding=None
    def replace(m):
        """Original filename placeholder replacement; width digits, no native objects/errors."""
        nonlocal padding
        padding=int(m[1]) if m[1] else padding if padding is not None else -1
        return '{}'
    pattern=re.sub(r'{(\d*)}',replace,filename);sequence=padding is not None
    pages=canvas.pages;pp=len(pages);page=values['page'];n=number(page)
    idx=n-1 if n>0 else (string(pp)+string(page) if isinstance(page,(str,list,tuple)) else pp+n) if n<0 else math.nan
    idx=number(idx)
    if (math.isfinite(idx) and idx<0) or idx>=pp:
        label=f'Canvas only has a ‘page 1’' if pp==1 else f'Canvas has pages 1–{pp}'
        raise _native.RangeError(f'{label} ({string(idx)} is out of bounds)')
    if math.isfinite(idx):
        if idx%1:raise NotImplementedError('Fractional page indexing is pending G0 (original native empty-page panic)')
        pages=[pages[int(idx)]]
    elif not(sequence or fmt=='pdf'):pages=pages[-1:]
    engine=canvas.engine
    quality=values['quality']
    if quality is undefined:quality=.92
    elif isinstance(quality,bool) or not isinstance(quality,(int,float)) or not math.isfinite(quality) or not 0<=quality<=1:raise TypeError('Expected a number between 0.0–1.0 for `quality`')
    density=values['density']
    if density is undefined:
        name=extension or os.path.basename(filename).removesuffix(ext);m=re.search(r'@(\d+)x$',name,re.I);density=int(m[1]) if m else 1
    elif isinstance(density,bool) or not isinstance(density,(int,float)) or not math.isfinite(density) or density%1 or density<1:raise TypeError('Expected a non-negative integer for `density`')
    msaa=values['msaa']
    if msaa is undefined or msaa is True:msaa=None
    elif not math.isfinite(number(msaa)) or number(msaa)<0:raise TypeError('The number of MSAA samples must be an integer ≥0')
    else:msaa=number(msaa) if _native._text_width(msaa) is not None else None
    color=values['colorType']
    if color is not undefined:pixelSize(color)
    matte=values['matte']
    normalized=dict(format=fmt,quality=quality,density=density,msaa=msaa,outline=truth(values['outline']),downsample=truth(values['downsample']),textContrast=engine['textContrast'],textGamma=engine['textGamma'])
    if matte is not undefined:normalized['matte']=_text(string(matte))
    if color is not undefined:normalized['colorType']=color
    return [p._native for p in pages],json.dumps(normalized,ensure_ascii=True,allow_nan=False),_MIMES[fmt],pattern,padding if padding is not None else -1,sequence

def data_url(data,mime):
    """Owned bytes -> original MIME/base64 URL; any thread, no units/native refs/errors."""
    return 'data:'+mime+';base64,'+base64.b64encode(data).decode('ascii')

class ExportPromise:
    """Awaitable original eagerly started export. Cancellation stops one waiter only;
    worker owns original materialized snapshots. Results/errors may be awaited repeatedly.
    Source Canvas.toBuffer/toURL JS Promise; Python waiting never moves GPU context.
    """
    __slots__=('_task','_done','_value','_error','_mime','_audit')
    def __init__(self,task,mime=None):
        """Own channel-only task/optional URL MIME, no native owner refs, no units/errors."""
        self._task=task;self._done=False;self._value=None;self._error=None;self._mime=mime;self._audit=None
    def __await__(self):
        """Poll owned result cooperatively; bytes/None/URL, original Error, any loop/thread.
        No Python executor/owner native calls. Source original deferred.settle_with.
        """
        async def wait():
            """Cooperative receiver wait, cached result; CancelledError affects waiter only."""
            while not self._done:
                ready,value,error,audit=self._task.poll()
                if ready:
                    self._done=True;self._audit=json.loads(audit);self._task=None
                    if error is not None:self._error=_native.Error(error)
                    else:self._value=data_url(value,self._mime) if self._mime else value
                else:await asyncio.sleep(.002)
            if self._error is not None:raise self._error
            return self._value
        return wait().__await__()

def export(canvas,extension='png',opts=undefined,filename=None,asynchronous=False,url=False):
    """Route original public exports through shared normalization/native dispatch.
    Returns bytes/None/URL or eagerly started awaitable, original validation/native errors.
    Owner required at call; async worker contains no Canvas/Context. Source Canvas methods.
    """
    pages,settings,mime,pattern,padding,sequence=options(canvas,extension,'' if filename is None else filename,opts)
    args=(pages,settings,pattern if filename is not None else None,padding,sequence)
    if asynchronous:return ExportPromise(canvas._native.export_start(*args),mime if url else None)
    value=canvas._native.export_sync(*args)
    return data_url(value,mime) if url else value

def deprecated(old,new):
    """Original once/process stderr rename warning, no units/ownership/errors. Source _deprecated."""
    if old not in _WARNED:
        print(f'Deprecation warning: Canvas.{old}() has been renamed to Canvas.{new} and will stop working in a future release.',file=sys.stderr);_WARNED.add(old)
