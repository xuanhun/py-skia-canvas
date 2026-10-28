"""Original imagery.js/urls.js language facade; decoding/drawing live in sole Rust core."""
import asyncio,base64,math,os,re,urllib.parse,urllib.request
from . import _native,undefined,_text
from ._text_api import string
from ._text_css import truth
from ._transform import string_number
from ._arguments import STRICT as _STRICT
from ._events import EventEmitter

def number(value):
    """JS Number for ordinary language inputs, f64/unitless; no native ownership.

    Returns NaN for unsupported objects; arrays use ordinary JS join conversion.
    Source imagery.js dimensions and context.js getImageData MSAA arithmetic.
    """
    if value is undefined:return math.nan
    if value is None:return 0.
    if isinstance(value,(int,float)):
        try:return float(value)
        except OverflowError:return -math.inf if value<0 else math.inf
    if isinstance(value,(str,list,tuple)):return string_number(string(value))
    return math.nan

def argc(args,*allowed):
    """Original argc length guard; unitless tuple ->None/TypeError, no native refs.
    Source neon.js:argc, accepts listed arities and counts above largest accepted.
    """
    if len(args) not in allowed and len(args)<=max(allowed):raise TypeError('not enough arguments')

def field(obj,key,default=undefined):
    """Read ordinary settings with JS undefined-default; unitless owned values.
    Source imagery.js/context.js destructuring; null destructuring ->TypeError.
    """
    if obj is undefined:return default
    if obj is None:raise TypeError("Cannot read properties of null (reading '"+key+"')")
    value=obj.get(key,undefined) if isinstance(obj,dict) else getattr(obj,key,undefined)
    return default if value is undefined else value

def pixelSize(color_type):
    """Original pixelSize exact enum strings ->byte count, TypeError for unknown.
    Unit bytes/pixel, any thread, no native refs. Source imagery.js:pixelSize.
    """
    groups=[(1,('Alpha8','Gray8','R8UNorm')),(2,('A16Float','A16UNorm','ARGB4444','R8G8UNorm','RGB565')),(4,('rgb','rgba','bgra','BGR101010x','BGRA1010102','BGRA8888','R16G16Float','R16G16UNorm','RGB101010x','RGB888x','RGBA1010102','RGBA8888','SRGBA8888')),(8,('R16G16B16A16UNorm','RGBAF16','RGBAF16Norm')),(16,('RGBAF32',))]
    for size,names in groups:
        if color_type in names:return size
    raise TypeError('Unknown colorType: '+string(color_type))

class _Pixels(bytearray):
    """Owned Uint8ClampedArray equivalent for ImageData.data; fixed-size byte storage.

    Byte values clamp/tie-to-even as JS; no GPU/font refs or owner affinity. In-place
    views may write bytes. Source imagery.js Uint8ClampedArray; host buffer detachment pending.
    """
    def __setitem__(self,key,value):
        """Set clamped byte(s) without resizing; index unit bytes, None/IndexError.
        Ordinary numeric conversion before assignment; source JS typed-array writes.
        """
        def clamp(v):
            """JS ToUint8Clamp primitive, byte range, any thread; returns integer."""
            n=number(v)
            return 0 if math.isnan(n) or n<=0 else 255 if n>=255 else round(n)
        if isinstance(key,slice):
            values=bytes(clamp(v) for v in value)
            if len(values)!=len(range(*key.indices(len(self)))):raise ValueError('ImageData storage cannot be resized')
            super().__setitem__(key,values)
        else:
            if -len(self)<=key<len(self):super().__setitem__(key,clamp(value))
    def set(self,values,offset=0):
        """Original typed-array .set, copied values at byte offset; RangeError if overrun.
        Returns None, owned data only, any thread. Source Uint8ClampedArray.set.
        """
        values=list(values);offset=math.trunc(number(offset))
        if offset<0 or offset+len(values)>len(self):raise _native.RangeError('offset is out of bounds')
        self[offset:offset+len(values)]=values
    def _fixed(self,*args,**kwargs):
        """Reject Python-only resize operations; no units/native refs, TypeError."""
        raise TypeError('ImageData storage cannot be resized')
    append=extend=insert=pop=remove=clear=__delitem__=__iadd__=__imul__=_fixed

class ImageData:
    """Original ImageData overloads with owned/shared clamped bytes; no Skia handle.

    Dimensions pixels, colors original strings. Initial fields readonly, data mutable;
    values survive Canvas/owner exit. Source imagery.js:ImageData, see constructor.
    """
    def toSharp(self, *extra):
        """Original optional Node Sharp dependency error; no fake image/stream.
        No units/native owner access before dependency check. Source imagery.js:toSharp;
        standalone Python host profile explicitly approved 2026-10-28.
        """
        from ._host import sharp
        return sharp()

    def __init__(self,*args):
        """Construct size, Buffer/clamped data, ImageData shallow copy or Image pixels.

        Original floor/abs/height inference, settings/error order retained. Dimensions
        pixel units; returns object, TypeError/RangeError. Image access owner-only;
        all resulting data Python-owned. Source imagery.js:ImageData constructor.
        """
        first=args[0] if args else undefined
        if isinstance(first,ImageData):
            argc(args,1);values=dict(first._record)
        else:
            if isinstance(first,Image):
                argc(args,1);settings=args[1] if len(args)>1 else undefined
                color_space=field(settings,'colorSpace','srgb');color_type=field(settings,'colorType','rgba')
                w,h=first.width,first.height;bpp=pixelSize(color_type)
                pixels=first._native.pixels(color_type);data=_Pixels(pixels or b'')
            elif isinstance(first,(bytes,bytearray,memoryview)):
                argc(args,2);width=args[1];height=args[2] if len(args)>2 else undefined;settings=args[3] if len(args)>3 else undefined
                color_space=field(settings,'colorSpace','srgb');color_type=field(settings,'colorType','rgba');bpp=pixelSize(color_type)
                w=_dimension(width)
                inferred=len(first)/w/bpp if w else math.inf
                h=_dimension(height if truth(height) else inferred)
                data=first if isinstance(first,_Pixels) else _Pixels(first)
                if len(data)/bpp!=w*h:raise TypeError('ImageData dimensions must match buffer length')
            else:
                argc(args,2);settings=args[2] if len(args)>2 else undefined
                color_space=field(settings,'colorSpace','srgb');color_type=field(settings,'colorType','rgba');bpp=pixelSize(color_type)
                w,h=_dimension(first),_dimension(args[1]);data=None
            if color_space!='srgb':raise TypeError('Unsupported colorSpace: '+string(color_space))
            if not all(math.isfinite(v) and v==int(v) and v>0 for v in (w,h)):raise _native.RangeError('Dimensions must be non-zero')
            w,h=int(w),int(h)
            values=dict(colorSpace=color_space,colorType=color_type,width=w,height=h,bytesPerPixel=bpp,data=data if data is not None else _Pixels(w*h*bpp))
        object.__setattr__(self,'_record',values)
    def __getattr__(self,name):
        """Return original field, pixels/bytes units; missing ->AttributeError, any thread."""
        if name in self._record:return self._record[name]
        raise AttributeError(name)
    def __setattr__(self,name,value):
        """Initial field overwrite ->original TypeError, other Python attrs mutable.
        No native refs/units, source neon.js:readOnly on ImageData fields.
        """
        if name in self._record:raise TypeError("Cannot assign to read only property '"+name+"' of object '#<ImageData>'")
        object.__setattr__(self,name,value)
    def __delattr__(self,name):
        """Initial field delete ->original TypeError; added attrs ordinary, any thread."""
        if name in self._record:raise TypeError("Cannot delete property '"+name+"' of #<ImageData>")
        object.__delattr__(self,name)

def _dimension(value):
    """Original Math.floor(Math.abs(value)), pixel count f64/int, NaN/Infinity retained.
    No native refs/errors beyond conversion; source imagery.js dimensions normalization.
    """
    n=abs(number(value));return math.floor(n) if math.isfinite(n) else n

class URIError(ValueError):
    """Original decodeURIComponent malformed-URI category, no native references."""

def _data_url(value):
    """Original first-40-char data URL header/encoding behavior ->owned bytes.

    No units/native ownership; original TypeError/URIError, source urls.js:decodeDataURL.
    Decoding is transport only, Skia alone decodes the resulting image bytes.
    """
    match=re.match(r'^\s*data:([^;]*);(?:charset=)?([^,]*),',value[:40])
    if not match or not match[1] or not match[2]:raise TypeError('Expected a valid data URL string (got: "'+value+'")')
    content=value[match.end():];encoding=match[2]
    if encoding.lower()!='base64':
        if re.search(r'%(?![0-9a-fA-F]{2})',content):raise URIError('URI malformed')
        try:content=urllib.parse.unquote(content,encoding='utf-8',errors='strict')
        except UnicodeDecodeError:raise URIError('URI malformed') from None
    name=encoding.lower()
    if name in ('base64','base64url'):
        clean=re.sub(r'[^A-Za-z0-9+/=_-]','',content).replace('-','+').replace('_','/').split('=')[0]
        if len(clean)%4==1:clean=clean[:-1]
        return base64.b64decode(clean+'='*((-len(clean))%4))
    if name in ('utf8','utf-8'):return _text(content).encode('utf-8')
    if name in ('utf16le','utf-16le','ucs2','ucs-2'):return content.encode('utf-16-le','surrogatepass')
    if name in ('ascii','latin1','binary'):return bytes(content.encode('utf-16-le','surrogatepass')[::2])
    if name=='hex':return bytes.fromhex(re.match(r'(?:[a-fA-F0-9]{2})*',content)[0])
    raise TypeError('Unknown encoding: '+encoding)

def _expand(src):
    """Accept Python filesystem paths as file URL equivalent; return source unchanged otherwise.
    No native refs, file path units/owned string. Source urls.js:expandURL, URL host pending.
    """
    if isinstance(src,os.PathLike):return os.fspath(src)
    if isinstance(src,(urllib.parse.ParseResult,urllib.parse.SplitResult)):
        if src.scheme.lower()=='file':return urllib.request.url2pathname(urllib.parse.unquote(src.path))
        if src.scheme.lower() in ('http','https','data'):return src.geturl()
        raise _native.Error('Unsupported protocol: '+src.scheme)
    return src

async def _fetch(src,options=undefined):
    """Fetch owned bytes/label from Buffer/data URL/local path/HTTP without native objects.

    Byte I/O may run in worker; decoding/rendering always resumes on caller owner thread.
    Returns (bytes,src) or original decode/HTTP/I/O Error. Source imagery.js:fetchData/urls.
    Full Node agent/proxy/request/Sharp options remain host-interop tasks.
    """
    src=_expand(src)
    if isinstance(src,(bytes,bytearray,memoryview)):return bytes(src),'::Buffer::'
    src=string(src)
    if src.startswith('data:'):return _data_url(src),src
    def read():
        """Byte transport only, no Skia resources; returns owned bytes or I/O error."""
        if re.match(r'^\s*https?://',src):
            from ._http import request_bytes
            return request_bytes(src,options)
        try:
            with open(src,'rb') as f:return f.read()
        except FileNotFoundError:raise _native.Error("ENOENT: no such file or directory, open '"+src+"'") from None
    return await asyncio.to_thread(read),src

class Image(EventEmitter):
    """Original Image decoder/metadata, owner-thread native ID plus language I/O/events.

    Pixel dimensions readonly; constructor Buffer/data URL decode synchronous. src I/O
    and decode() await on owner loop, no GPU/native values enter Python worker threads.
    Source imagery.js Image; Node EventEmitter host-complete API audit remains G0.
    """
    def __setattr__(self,name,value):
        """Original getter-only image dimensions/complete ->TypeError; other attrs ordinary.
        Pixel dimensions/flag unitless, no native borrowing; source imagery.js getters.
        """
        if name in ('width','height','complete'):raise TypeError('Cannot set property '+name+' of #<Image> which has only a getter')
        object.__setattr__(self,name,value)
    def __init__(self,data=undefined,src='',*extra):
        """Allocate Loading then decode Buffer/data URL, extra args ignored.
        Returns Image; invalid truthy data TypeError, failed Skia decode Error. Dimensions
        pixels, src label string. Owner-only native data; source imagery.js:constructor.
        """
        EventEmitter.__init__(self);self._native=_native.NativeImage();self._pending=undefined;self._task=None;self._err=None;self._token=object();self._callbacks={}
        data=_expand(data);self._native.source(string(src) or '::Buffer::')
        if isinstance(data,(bytes,bytearray,memoryview)):
            if not self._native.decode_bytes(bytes(data)):raise _native.Error('Could not decode image data')
        elif isinstance(data,str):
            if not self._native.decode_bytes(_data_url(data)):raise _native.Error('Could not decode image data')
            if not truth(src):self._native.source(data)
        elif truth(data):raise TypeError('Exptected a Buffer or a String containing a data URL (got: '+string(data)+')')
    @property
    def width(self):
        """Original intrinsic pixel width, owner-only/RuntimeError; source image.rs:get_width."""
        return self._native.info()[0]
    @property
    def height(self):
        """Original intrinsic pixel height, owner-only/RuntimeError; source image.rs:get_height."""
        return self._native.info()[1]
    @property
    def complete(self):
        """Original complete flag including Broken, owner-only/RuntimeError; source image.rs."""
        return self._native.info()[2]
    @property
    def src(self):
        """Original owned source label; owner-only/RuntimeError, source imagery.js:src."""
        return self._native.info()[3]
    @src.setter
    def src(self,src):
        """Set latest request token/label, load bytes/data immediately or schedule I/O.
        Returns None, events and decode() resolve latest request; stale completions ignored.
        Owner thread only, errors emit as original. Source imagery.js:src setter.
        """
        src=_expand(src);self._native.source(src if isinstance(src,str) else '')
        self._token=object();self._pending=src
        if isinstance(src,(bytes,bytearray,memoryview)) or isinstance(src,str) and src.startswith('data:'):
            try:data=bytes(src) if not isinstance(src,str) else _data_url(src)
            except Exception as e:self._finish(None,'',e,self._token)
            else:self._finish(data,'::Buffer::' if not isinstance(src,str) else src,None,self._token)
        else:self._start()
    def _start(self):
        """Start pending transport in active owner loop, no native workers; None/no-loop deferral.
        Source src/decode Promise scheduling; outside-loop pending starts when decode awaited.
        """
        try:loop=asyncio.get_running_loop()
        except RuntimeError:return
        token=self._token;src=self._pending
        async def run():
            """Await byte transport then owner-local decode, preserving latest-token semantics."""
            try:data,label=await _fetch(src)
            except Exception as e:self._finish(None,'',e,token)
            else:self._finish(data,label,None,token)
        self._task=loop.create_task(run())
    def _finish(self,data,label,error,token):
        """Apply current owned bytes on owner; emit load/error after native borrow ends.
        No native objects cross workers; stale tokens ignored. Source imagery.js loaded/failed.
        """
        if token is not self._token:return
        self._pending=undefined;self._task=None
        if error is None:
            self._native.source(label)
            self._err=None if self._native.decode_bytes(data) else _native.Error('Could not decode image data')
        else:self._native.decode_bytes(b'');self._err=error
        self.emit('error',self._err) if self._err else self.emit('load',self)
    async def decode(self):
        """Await latest load/error or return complete self, original source-not-set Error.
        Owner thread only; result same Image, no units/native transfer. Source imagery.js:decode.
        """
        self._native.info()
        if self._pending is not undefined:
            loop=asyncio.get_running_loop();future=loop.create_future()
            def loaded(value):
                """Resolve waiter on owner loop, skip cancelled future, no native work."""
                if not future.done():future.set_result(value)
            def failed(error):
                """Reject waiter on owner loop, skip cancelled future, no native work."""
                if not future.done():future.set_exception(error)
            self.once('load',loaded);self.once('error',failed)
            if self._task is None:self._start()
            try:return await future
            finally:self.off('load',loaded);self.off('error',failed)
        if self._err:raise self._err
        if self.complete:return self
        raise _native.Error('Image source not set')
    def _event_property(event):
        """Create onload/onerror property forwarding on/off, no native work. Source imagery.js."""
        def get(self):
            """Return saved callback/undefined; owned value, unitless."""
            return self._callbacks.get(event,undefined)
        def set(self,cb):
            """Remove previous then register callable, None for noncallable; returns None."""
            prior=self._callbacks.get(event)
            if prior:self.off(event,prior)
            self._callbacks[event]=cb if callable(cb) else None
            if callable(cb):self.on(event,cb)
        return property(get,set)
    onload=_event_property('load');onerror=_event_property('error')

async def loadImage(src,options=undefined):
    """Load Buffer/data URL/path/HTTP asynchronously, return decoded owner-local Image.
    Pixel dimensions; fetch/decode errors reject, no GPU moved. Source imagery.js:loadImage.
    """
    data,label=await _fetch(src,options);return Image(data,label)

async def loadImageData(src,*args):
    """Load raw bytes then original ImageData overload; not encoded-image rasterization.
    Pixel dimensions/settings from args, original errors; pure I/O workers, owned values.
    Source imagery.js:loadImageData, Sharp raw host interoperability remains pending.
    """
    options=args[2] if len(args)>2 else undefined
    data,_=await _fetch(src,options);return ImageData(data,*args)

def _float(value,name,ordinal,optional=False):
    """Original finite-f64->f32 native argument reader, canvas units; TypeError/None.
    Source utils.rs:_float_args_at/opt_float_arg; no native object ownership.
    """
    n=_native._text_width(value)
    if n is None and not optional:raise TypeError('Expected a number for `'+name+'` as '+ordinal+' arg')
    return n

def install(cls):
    """Bind original Context imagery facade to owner-local core calls; no rendering here.
    Classes/methods retain Node names. Source context.js imagery methods; unit/error docs below.
    """
    def createImageData(self,*args):
        """Original size ImageData factory, pixels, argc2/3 ->ImageData/TypeError/RangeError.
        Value-only allocation, source context.js:createImageData.
        """
        argc(args,2,3);return ImageData(*args[:3])
    def getImageData(self,*args):
        """Read original owned pixel crop/settings, canvas units->ImageData pixel dimensions.
        Owner-only; original density/MSAA/color/dimension errors. Source context.js/getImageData.
        """
        argc(args,4,5);x,y,w,h=args[:4];settings=args[4] if len(args)>4 else undefined
        color_type=field(settings,'colorType','rgba');color_space=field(settings,'colorSpace','srgb');density=field(settings,'density',1);matte=field(settings,'matte',undefined);msaa=field(settings,'msaa',undefined)
        if not isinstance(density,(int,float)) or isinstance(density,bool) or not math.isfinite(density) or int(density)!=density or density<1:raise TypeError('Expected a non-negative integer for `density`')
        if msaa is undefined or msaa is True:msaa=None
        else:
            n=number(msaa)
            if not math.isfinite(n) or n<0:raise TypeError('The number of MSAA samples must be an integer ≥0')
            parsed=_native._text_width(msaa);msaa=None if parsed is None else int(parsed)
        coords=[_float(v,n,str(i+1)+('st' if i==0 else 'nd' if i==1 else 'rd' if i==2 else 'th')) for i,(v,n) in enumerate(zip((x,y,w,h),('x','y','width','height')))]
        if self.canvas is undefined:raise TypeError('failed to downcast any to neon::types_impl::boxed::JsBox<core::cell::RefCell<skia_canvas::canvas::Canvas>>')
        data=self._native.image_pixels(*coords,color_type if isinstance(color_type,str) else 'rgba',color_space if isinstance(color_space,str) else 'srgb',density,matte if isinstance(matte,str) else None,msaa)
        return ImageData(data,number(w)*density,number(h)*density,dict(colorType=color_type,colorSpace=color_space))
    def putImageData(self,*args):
        """Original blit ignores transform/clip/alpha; pixels, dirty rectangle 3/7 args.
        Owner-only returns None, original argc/type/number errors. Source context.js/API.
        """
        argc(args,3,7);image=args[0]
        if not isinstance(image,ImageData):raise TypeError('Expected an ImageData as 1st arg')
        names=['dx','dy']+(['dirtyX','dirtyY','dirtyWidth','dirtyHeight'] if len(args)>=4 else [])
        if len(args)-1<len(names):raise TypeError('not enough arguments (missing: '+', '.join(names[len(args)-1:])+')')
        coords=[_float(v,n,str(i+2)+('nd' if i==0 else 'rd' if i==1 else 'th')) for i,(v,n) in enumerate(zip(args[1:],names))]
        self._native.draw_data(bytes(image.data),image.width,image.height,image.colorType,image.colorSpace,coords,True)
    def draw(self,image=undefined,*coords,vector=False):
        """Original Image/Canvas/ImageData draw dispatch with 2/4/8 canvas-unit coordinates.
        Owner-only, incomplete Image/error/nonfinite silent bail as ordinary Node mode.
        Source context.js:drawImage/drawCanvas and shared original core layout.
        """
        from . import Canvas
        if not isinstance(image,(Image,ImageData,Canvas)):
            if asyncio.isfuture(image) or asyncio.iscoroutine(image):raise _native.Error('Promise has not yet resolved: `await` image loading before drawing')
            raise _native.Error('Expected an Image or a Canvas argument (got: '+string(image)+')')
        if isinstance(image,Image) and not image.complete:raise _native.Error('Image has not completed loading: listen for `load` event or await `decode()` first')
        names=['srcX','srcY','srcWidth','srcHeight','dstX','dstY','dstWidth','dstHeight']
        nums=[_float(v,n,'',True) for v,n in zip(coords,names)]
        if any(v is None for v in nums):
            if _STRICT:
                i=next(i for i,v in enumerate(nums) if v is None);ordinal=str(i+2)+('nd' if i==0 else 'rd' if i==1 else 'th')
                # Original rustError substr(1) removes U+26A0, retaining U+FE0F.
                raise TypeError('\ufe0fExpected a number for `'+names[i]+'` as '+ordinal+' arg')
            return
        if len(coords)>8:raise NotImplementedError("Original Node native source panics with more than eight coordinates; this input is outside the supported contract")
        if isinstance(image,Canvas):image.getContext('2d');return self._native.draw_canvas_resource(image._native,nums,vector)
        if isinstance(image,Image):return self._native.draw_image_resource(image._native,nums)
        return self._native.draw_data(bytes(image.data),image.width,image.height,image.colorType,image.colorSpace,nums,False)
    def drawImage(self,image=undefined,*coords):
        """Draw source through original bitmap/vector core, canvas units, owner/errors as draw."""
        return draw(self,image,*coords)
    def drawCanvas(self,image=undefined,*coords):
        """Draw Canvas vector snapshot or original drawImage fallback, same units/owner/errors."""
        return draw(self,image,*coords,vector=True)
    def get_enabled(self):
        """Return original sampling flag, owner-only/RuntimeError, unitless; source API."""
        return self._native.smoothing()[0]
    def set_enabled(self,value):
        """Set JS-truth sampling flag, owner-only, None; source context.js imageSmoothingEnabled."""
        self._native.smoothing(truth(value),None)
    def get_quality(self):
        """Return original quality string, owner-only/RuntimeError, unitless; source API."""
        return self._native.smoothing()[1]
    def set_quality(self,value):
        """Set original quality string/ignore invalid string, owner-only/TypeError, None."""
        if not isinstance(value,str):raise TypeError('Expected a string for `imageSmoothingQuality`')
        self._native.smoothing(None,value)
    for name,fn in [('createImageData',createImageData),('getImageData',getImageData),('putImageData',putImageData),('drawImage',drawImage),('drawCanvas',drawCanvas)]:setattr(cls,name,fn)
    cls.imageSmoothingEnabled=property(get_enabled,set_enabled);cls.imageSmoothingQuality=property(get_quality,set_quality)
