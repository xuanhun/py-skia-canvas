"""Original gui.js facade: no window renderer, input layout or native cadence in Python."""
import asyncio,json,math,os,threading,traceback
from collections.abc import Coroutine
from . import Canvas,undefined,_native,_text
from ._events import EventEmitter
from ._imagery import number,field
from ._text_api import string
from ._text_css import truth
_CURSORS=('default','none','context-menu','help','pointer','progress','wait','cell','crosshair','text','vertical-text','alias','copy','move','no-drop','not-allowed','grab','grabbing','e-resize','n-resize','ne-resize','nw-resize','s-resize','se-resize','sw-resize','w-resize','ew-resize','ns-resize','nesw-resize','nwse-resize','col-resize','row-resize','all-scroll','zoom-in','zoom-out')
_FITS=('none','contain-x','contain-y','contain','cover','fill','scale-down','resize')
_KWARGS='id,left,top,width,height,title,page,background,fullscreen,cursor,fit,visible,resizable,borderless,closed'.split(',')
_LOCALE=next((os.environ[k] for k in ('LC_ALL','LC_MESSAGES','LANG','LANGUAGE') if os.environ.get(k)),undefined)

def _check():
    """Original checkSupport plus Python main-thread boundary; None/Error/RuntimeError.
    Unitless; no fake window on feature absence, no GPU context movement. gui.js/winit.
    """
    if not _native._gui_support():raise _native.Error('Skia Canvas was compiled without window support')
    if threading.current_thread() is not threading.main_thread():raise RuntimeError('App and Window must be used on the main thread')

def _finite(value):
    """Original Number.isFinite without coercion, bool/no units/native refs. gui.js setters."""
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def _json(value):
    """Original ordinary JSON.stringify for GUI DTOs: omit undefined, integral Number
    serializes as integer; returns JSON string, no native refs. Cycles/host profiles G0.
    """
    def clean(v):
        """Own JSON primitives recursively, no units/graphics or rendering policy."""
        if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if x is not undefined}
        if isinstance(v,(list,tuple)):return [None if x is undefined else clean(x) for x in v]
        if isinstance(v,float):return None if not math.isfinite(v) else int(v) if v.is_integer() else v
        return v
    return _text(json.dumps(clean(value),ensure_ascii=True,allow_nan=False,separators=(',',':')))

class _Event(dict):
    """Owned original event fields with optional Python attribute access, no native refs."""
    def __getattr__(self,name):
        """Read event field, value/AttributeError; unit inherited, any thread. gui.js payload."""
        try:return self[name]
        except KeyError:raise AttributeError(name) from None

class _Session(Coroutine):
    """Owner-loop coroutine/awaitable for original App session; no native objects in task.
    Explicit App.launch works with asyncio.run; active asyncio loops auto-launch Window.
    Waiting cancellation is shielded; loop shutdown closes actual windows on owner.
    """
    def __init__(self,app):
        """Hold Python App and lazy task, unitless metadata, no native ownership/errors."""
        self.app=app;self.task=None;self.iterator=None
    def start(self):
        """Start owner task in current asyncio loop, no native transfer; RuntimeError if absent."""
        if self.task is None:self.task=asyncio.create_task(self.run())
    async def run(self):
        """Run original native loop or node pump until closed, return None/errors.
        Main thread only; native callback reenters Python synchronously. Original loop-mode
        cadence stays core. Task cancellation at loop shutdown performs owner cleanup.
        """
        try:
            while _native._gui_step(self.app._dispatch):await asyncio.sleep(0)
        except asyncio.CancelledError:
            for win in self.app.windows:win.close()
            _native._gui_quit();_native._gui_step(self.app._dispatch)
            raise
        finally:
            self.app._session=None;self.app._launcher=None
            self.app.emit('idle',_Event(type='idle',target=self.app))
    async def wait(self):
        """Shield session task from individual waiter cancellation, None/errors, owner loop."""
        self.start();return await asyncio.shield(self.task)
    def __await__(self):
        """Return repeatable session await iterator, no units; original App Promise result."""
        return self.wait().__await__()
    def send(self,value):
        """Coroutine protocol for asyncio.run, no units/native refs; delegates same awaiter."""
        if self.iterator is None:self.iterator=self.__await__()
        return self.iterator.send(value)
    def throw(self,*args):
        """Coroutine exception protocol, exception propagated to waiter only; no native move."""
        if self.iterator is None:self.iterator=self.__await__()
        return self.iterator.throw(*args)
    def close(self):
        """Close waiter iterator, not native session job; no units/return, Coroutine API."""
        if self.iterator is not None:self.iterator.close()

class _App(EventEmitter):
    """Original App singleton; mode/fps/windows/frame/UI semantics from gui.js.
    Main-thread GUI access; Python launch is awaitable, original core owns OS loop/renderer.
    """
    def __init__(self):
        """Original native mode, not-started, no windows, 60 FPS; import creates no display."""
        super().__init__();self._mode='native';self._started=False;self._windows=[];self._frames={};self._fps=60;self._launcher=None;self._session=None
    @property
    def windows(self):
        """Copied original active Window wrappers, no units/errors; gui.js App.windows."""
        return self._windows[:]
    @property
    def running(self):
        """Original started-once flag (stays true after idle), bool/no units/errors. gui.js."""
        return self._started
    @property
    def eventLoop(self):
        """Original native/node mode label, no units/errors/native refs; gui.js getter."""
        return self._mode
    @eventLoop.setter
    def eventLoop(self,mode):
        """Set recognized mode before first launch, ignore unknown; Error once started.
        Main-thread only; source gui.js App.eventLoop and original core set_mode.
        """
        if self._started:raise _native.Error('Cannot alter event loop after it has begun')
        if mode in ('native','node') and mode!=self._mode:_check();self._mode=_native._gui_mode(mode)
    @property
    def fps(self):
        """Original current f32 FPS value, no ownership transfer/errors; gui.js getter."""
        return self._fps
    @fps.setter
    def fps(self,rate):
        """Original >=1 guard and native f32 FPS conversion, ignore lower/NaN; TypeError
        for nonfinite native conversion. Main-thread only; gui.js fps/setRate.
        """
        _check()
        if number(rate)>=1 and number(rate)!=self._fps:
            value=_native._text_width(rate)
            if value is None:raise TypeError('Expected a number for `framesPerSecond` as 1st arg')
            self._fps=_native._gui_rate(value)
    def _open(self,win):
        """Track original opened wrapper/frame count and queue real page snapshot; None/errors.
        Logical pixel state, owner-only. Source Window.events open listener in gui.js.
        """
        _check();self._windows.append(win);self._frames[win.id]=0
        if self._launcher is None:
            try:self._launcher=asyncio.get_running_loop().call_soon(self.launch)
            except RuntimeError:pass
        _native._gui_open(_json(win.state),win.ctx._native)
    def _close(self,win):
        """Remove wrapper, queue real close and emit original close event; None/owner errors.
        Unitless ID, source Window.events close listener; original snapshot iteration retained.
        """
        _check();self._windows=[w for w in self._windows if w is not win];_native._gui_close(win.id);win.emit('close')
    def launch(self):
        """Mark started immediately, return shared awaitable until original windows close.
        Main-thread only/Error on unsupported build. Running asyncio loops start promptly;
        without a running loop use asyncio.run(App.launch()). Source gui.js App.launch.
        """
        _check()
        if self._launcher is not None:self._launcher.cancel()
        self._started=True
        if self._session is None:self._session=_Session(self)
        try:asyncio.get_running_loop();self._session.start()
        except RuntimeError:pass
        return self._session
    def quit(self):
        """Original native quit outside callback, None/owner errors; gui.js App.quit.
        Reentrant native RefCell panic is rejected explicitly by binding (G0 profile).
        """
        _check();_native._gui_quit()
    def _each(self,updates,callback):
        """Find original ID-matching active wrapper, deliver owned payload; None/errors.
        Unitless IDs, owner callbacks only, source gui.js #eachWindow.
        """
        for ident,payload in (updates or {}).items():
            win=next((w for w in self._windows if number(w.id)==number(ident)),None)
            if win is not None:callback(win,payload)
    def _dispatch(self,is_frame,payload):
        """Port original state/geometry/UI/frame ordering; returns JSON specs + fixed-page
        metadata handles on render roundtrip, otherwise False. Events carry original
        units and keyboard preventDefault semantics; renderer/fitting/input capture stay
        Rust. Synchronous owner callback, source gui.js #dispatch.
        """
        data=json.loads(payload);geom=data.get('geom');state=data.get('state');ui=data.get('ui')
        if geom:
            def merge(win,loc):
                """Original falsy-location merge, logical pixels, owner-only/None."""
                win.left=win.left if truth(win.left) else loc['left'];win.top=win.top if truth(win.top) else loc['top']
            self._each(geom,merge)
        if state is not None:
            active=[]
            for win in self._windows:
                if str(win.id) in state or win.top is undefined:
                    for k,v in state.get(str(win.id),{}).items():setattr(win,k,v)
                    active.append(win)
                else:win.close()
            self._windows=active
        if ui:
            def deliver(win,events):
                """Original event family conversion/default keys, owned payload/None; gui.js."""
                for item in events:
                    kind,e=next(iter(item.items()))
                    if kind=='mouse':win.emit(e['event'],dict(button=e['button'],buttons=e['buttons'],**e['point'],pageX=e['page_point']['x'],pageY=e['page_point']['y'],**e['modifiers']))
                    elif kind=='input':win.emit(kind,dict(data=e[0],inputType=e[1]))
                    elif kind=='composition':win.emit(e['event'],dict(data=e['data'],locale=_LOCALE))
                    elif kind=='keyboard':
                        defaults=[True]
                        def prevent():
                            """Original preventDefault flag, no units/native refs/errors."""
                            defaults[0]=False
                        win.emit(e['event'],dict(key=e['key'],code=e['code'],location=e['location'],repeat=e['repeat'],**e['modifiers'],preventDefault=prevent))
                        if defaults[0] and e['event']=='keydown' and not e['repeat']:
                            mod=e['modifiers'];key=e['key']
                            if (mod['metaKey'] and key=='w') or (mod['ctrlKey'] and key=='c') or (mod['altKey'] and key=='F4'):win.close()
                            elif (mod['metaKey'] and key=='f') or (mod['altKey'] and key=='F8'):win.fullscreen=not win.fullscreen
                    elif kind=='focus':win.emit('focus' if e else 'blur')
                    elif kind=='resize':
                        if win.fit=='resize':win.ctx._native.gui_context_size(e['width'],e['height']);win.canvas._native.gui_canvas_size(e['width'],e['height'])
                        win.emit(kind,e)
                    elif kind in ('move','wheel'):win.emit(kind,e)
                    elif kind=='fullscreen':win.emit(kind,dict(enabled=e))
                    else:print(kind,e)
            self._each(ui,deliver)
        if is_frame:
            for win in self._windows:
                self._frames[win.id]+=1;frame=self._frames[win.id]
                if frame==0:win.emit('setup')
                win.emit('frame',dict(frame=frame))
                if win.listenerCount('draw'):win.canvas.getContext('2d').reset();win.emit('draw',dict(frame=frame))
            return _json([w.state for w in self._windows]),[w.ctx._native for w in self._windows]
        return False

class Window(EventEmitter):
    """Original public GUI Window wrapper; original Rust owns Winit/renderer/swapchain.
    Logical pixel state, independent Canvas/page references, main-thread-only GUI changes.
    Source gui.js Window; no empty window or replacement drawing implementation.
    """
    events=EventEmitter();_next_id=1
    def __init__(self,*args):
        """Original (width=512,height=512,opts={}) or (opts) overload, create real window.
        Logical px, optional Canvas/text settings; returns instance/validation/owner errors.
        Initial native open is queued on owner; App auto-launches in active asyncio loop.
        """
        _check();width=args[0] if args and args[0] is not undefined else 512;height=args[1] if len(args)>1 and args[1] is not undefined else 512;opts=args[2] if len(args)>2 and args[2] is not undefined else {}
        if not _finite(width) or not _finite(height):
            opts=args[-1] if args and truth(args[-1]) else {};canvas=field(opts,'canvas');width=field(opts,'width');height=field(opts,'height')
            width=width if truth(width) else field(canvas,'width') if canvas is not undefined and truth(field(canvas,'width')) else 512
            height=height if truth(height) else field(canvas,'height') if canvas is not undefined and truth(field(canvas,'height')) else 512
        canvas=field(opts,'canvas');has_canvas=isinstance(canvas,Canvas);engine=canvas.engine if has_canvas else opts
        contrast=field(engine,'textContrast',0);gamma=field(engine,'textGamma',1.4)
        canvas=canvas if has_canvas else Canvas(width,height,{'textContrast':contrast,'textGamma':gamma})
        super().__init__();self._state=dict(title='',visible=True,resizable=True,borderless=False,background='white',fullscreen=False,closed=False,page=len(canvas.pages),left=undefined,top=undefined,width=width,height=height,textContrast=contrast,textGamma=gamma,cursor='default',fit='contain',id=Window._next_id);Window._next_id+=1
        self._canvas=None;self.canvas=canvas
        for k,v in (opts.items() if isinstance(opts,dict) else []):
            if k in _KWARGS and v is not undefined:setattr(self,k,v)
        if self.width<=0 or self.height<=0:raise NotImplementedError('Non-positive Window dimensions remain an unsafe upstream GUI profile')
        Window.events.emit('open',self)
    @property
    def state(self):
        """Copied original state dict with undefined positions, units logical px; no errors."""
        return self._state.copy()
    @property
    def ctx(self):
        """Original selected Canvas page context/undefined, owner native handle only. gui.js."""
        idx=number(self.page)-1;pages=self.canvas.pages
        return pages[int(idx)] if math.isfinite(idx) and idx%1==0 and 0<=idx<len(pages) else undefined
    @property
    def id(self):
        """Immutable original numeric ID, unitless/readable metadata; gui.js id getter."""
        return self._state['id']
    @id.setter
    def id(self,value):
        """Original loose inequality guard, None/Error if changing ID; no native transfer."""
        if number(value)!=number(self.id):raise _native.Error('Window IDs are immutable')
    @property
    def canvas(self):
        """Original retained Canvas wrapper, owner GPU objects stay TLS; no units/errors."""
        return self._canvas
    @canvas.setter
    def canvas(self,value):
        """Accept Canvas, ensure page and inherit text settings/current page; ignore others.
        Owner only, None/native errors; source gui.js canvas setter.
        """
        if isinstance(value,Canvas):
            _check();value.getContext('2d');self._canvas=value;self._state.update(page=len(value.pages),textContrast=value.engine['textContrast'],textGamma=value.engine['textGamma'])
    @property
    def page(self):
        """Original 1-based selected page index, canvas-unit bounds remain core; no errors."""
        return self._state['page']
    @page.setter
    def page(self,value):
        """Original positive/negative page selection, ignore missing/fractional; update global
        Canvas dimensions without reset. None/owner errors; source gui.js page setter.
        """
        if number(value)<0:value=string(value)+string(len(self.canvas.pages)+1) if isinstance(value,(str,list,tuple)) else number(value)+len(self.canvas.pages)+1
        idx=number(value)-1
        if math.isfinite(idx) and idx%1==0 and 0<=idx<len(self.canvas.pages) and number(self.page)!=number(value):
            size=self.canvas.pages[int(idx)]._native.context_size();self.canvas._native.gui_canvas_size(*size);self._state['page']=value
    @property
    def closed(self):
        """Original logical closed flag, bool/no units/errors; gui.js getter only."""
        return self._state['closed']
    @closed.setter
    def closed(self,value):
        """Match original readonly assignment TypeError; no units/state/native changes."""
        raise TypeError('Cannot set property closed of #<Window> which has only a getter')
    def close(self):
        """Mark once and emit original static close event; None/owner/callback errors.
        Native close queued on same owner, source gui.js Window.close.
        """
        _check()
        if not self.closed:self._state['closed']=True;Window.events.emit('close',self)
    def open(self):
        """Reopen once with original ID/state/page, None/owner errors. gui.js Window.open."""
        _check()
        if self.closed:self._state['closed']=False;Window.events.emit('open',self)
    def emit(self,kind,e=undefined,*ignored):
        """Wrap original target/type and event fields, sync deliver, catch/report handler
        exceptions as original Window override; returns None. No units/native transfer.
        """
        payload=_Event(target=self,type=kind)
        if isinstance(e,dict):payload.update(e)
        elif isinstance(e,(str,list,tuple)):payload.update({str(i):v for i,v in enumerate(e)})
        try:super().emit(kind,payload)
        except Exception:traceback.print_exc()

def _property(name,kind):
    """Generate original state accessor using same single storage, not duplicate policies.
    Units logical pixels/bools/CSS names, getter value/setter None; owner setters/error guard.
    Source gui.js Window scalar properties and css.js parseCursor/parseFit.
    """
    def get(self):
        """Read original copied scalar metadata, units as property; no errors/native refs."""
        return self._state[name]
    def set_(self,value):
        """Original scalar validation/coercion, None/owner errors, keep invalid old value."""
        _check()
        if kind=='bool':value=truth(value)
        elif kind=='text':value='' if value is None or value is undefined else string(value)
        elif kind=='finite' and not _finite(value):return
        elif kind=='finite' and name in ('width','height') and value<=0:raise NotImplementedError('Non-positive Window dimensions remain an unsafe upstream GUI profile')
        elif kind=='cursor' and value not in _CURSORS:return
        elif kind=='fit' and value not in _FITS:return
        self._state[name]=value
    return property(get,set_)

for _name in ('visible','resizable','borderless','fullscreen'):setattr(Window,_name,_property(_name,'bool'))
for _name in ('left','top','width','height'):setattr(Window,_name,_property(_name,'finite'))
for _name in ('title','background'):setattr(Window,_name,_property(_name,'text'))
Window.cursor=_property('cursor','cursor');Window.fit=_property('fit','fit')
App=_App();Window.events.on('open',App._open);Window.events.on('close',App._close)
