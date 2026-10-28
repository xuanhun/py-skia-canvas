"""Ordinary EventEmitter listener semantics for App/Window; no graphics implementation."""
from . import undefined,_native
import warnings,math

class MaxListenersExceededWarning(RuntimeWarning):
    """Original listener-limit warning with emitter/type/count metadata, no GPU refs moved."""

def _key(value):
    """Original ordinary ToPropertyKey for event names; owned str/no units/errors.
    Python host profile has no JS Symbol identity; source Node events property table.
    """
    from ._text_api import string
    return value if isinstance(value,str) else string(value)

def _received(value):
    """Node ordinary invalid-argument value description; unitless string/no native refs.
    Source pinned Node internal/errors.js, Python callable/array/object host mapping.
    """
    from ._text_api import string
    if value is undefined:return 'undefined'
    if value is None:return 'null'
    if isinstance(value,bool):return 'type boolean ('+string(value)+')'
    if isinstance(value,(int,float)):return 'type number ('+string(value)+')'
    if isinstance(value,str):return 'type string ('+repr(value)+')'
    if isinstance(value,(list,tuple)):return 'an instance of Array'
    if callable(value):return 'function '+getattr(value,'__name__','')
    return 'an instance of Object'

def _listener(value):
    """Original listener callable guard, None/TypeError with value description, Node events.
    Unitless language-only metadata, no owner/native access.
    """
    if not callable(value):raise TypeError('The "listener" argument must be of type function. Received '+_received(value))

class _Once:
    """Original once wrapper: remove before invoke, retain listener identity; owner callbacks."""
    def __init__(self,emitter,event,listener):
        """Store unitless listener metadata; no native objects/errors, EventEmitter.once."""
        self.emitter=emitter;self.event=event;self.listener=listener;self.fired=False
    def __call__(self,*args):
        """Invoke once with original args, return callback value/errors; no GPU movement."""
        if self.fired:return
        self.fired=True;self.emitter.removeListener(self.event,self)
        return self.listener(*args)

class EventEmitter:
    """Ordinary Node EventEmitter callback lists, sync delivery, listener identity/mutation.
    Python callables stand in for JS functions; full Node async/host/meta APIs remain G0.
    No units/native ownership, source Node events API inherited by gui.js App/Window.
    """
    def __init__(self):
        """Create owned listener table, default limit 10; no units/errors/native refs."""
        self._listeners={};self._max_listeners=10;self._warned=set()
    def _add(self,event,listener,once=False,prepend=False):
        """Register original sync listener, return self/TypeError; emit newListener first.
        Unitless event key, owner callback semantics; source EventEmitter add/once helpers.
        """
        _listener(listener);event=_key(event)
        if self._listeners.get('newListener'):self.emit('newListener',event,listener)
        raw=_Once(self,event,listener) if once else listener
        group=self._listeners.setdefault(event,[]);group.insert(0,raw) if prepend else group.append(raw)
        if self._max_listeners>0 and len(group)>self._max_listeners and event not in self._warned:
            self._warned.add(event)
            label='Image [Object]' if type(self).__name__=='Image' else '['+type(self).__name__+']'
            from ._text_api import string
            warning=MaxListenersExceededWarning('Possible EventEmitter memory leak detected. '+str(len(group))+' '+event+' listeners added to '+label+'. MaxListeners is '+string(self._max_listeners)+'. Use emitter.setMaxListeners() to increase limit')
            warning.emitter=self;warning.type=event;warning.count=len(group);warnings.warn(warning,stacklevel=3)
        return self
    def on(self,event=undefined,listener=undefined,*extra):
        """Append sync listener, return self/TypeError; no units/native transfer. Node .on."""
        return self._add(event,listener)
    addListener=on
    def prependListener(self,event=undefined,listener=undefined,*extra):
        """Prepend sync listener, return self/TypeError; unitless keys. Node .prependListener."""
        return self._add(event,listener,prepend=True)
    def once(self,event=undefined,listener=undefined,*extra):
        """Append once wrapper, remove before callback; self/TypeError. Node .once."""
        return self._add(event,listener,once=True)
    def prependOnceListener(self,event=undefined,listener=undefined,*extra):
        """Prepend once wrapper; same ownership/errors/return as once, Node public API."""
        return self._add(event,listener,once=True,prepend=True)
    def removeListener(self,event=undefined,listener=undefined,*extra):
        """Remove last matching original/wrapper identity, return self/TypeError.
        Unitless callback table, sync removeListener meta delivery; Node .removeListener.
        """
        _listener(listener);event=_key(event)
        group=self._listeners.get(event,[])
        for i in range(len(group)-1,-1,-1):
            raw=group[i]
            if raw is listener or getattr(raw,'listener',None) is listener:
                removed=(getattr(raw,'listener',None) or listener) if len(group)==1 else listener
                group.pop(i)
                if not group:self._listeners.pop(event,None);self._warned.discard(event)
                if self._listeners.get('removeListener'):self.emit('removeListener',event,removed)
                break
        return self
    off=removeListener
    def removeAllListeners(self,*args):
        """Remove one/all listener sets, reverse per-event removal; return self, Node API.
        Unitless metadata, meta callbacks may raise; never transfers native graphics.
        """
        if not args:
            for key in self.eventNames():
                if key!='removeListener':self.removeAllListeners(key)
            self.removeAllListeners('removeListener')
        else:
            event=_key(args[0])
            for raw in self._listeners.get(event,[])[:][::-1]:self.removeListener(event,raw)
        return self
    def emit(self,event=undefined,*args):
        """Snapshot listeners and deliver sync in order, bool present/propagated exception.
        Unitless event args, original unhandled error raises; source EventEmitter.emit.
        """
        event=_key(event);group=self._listeners.get(event,[])[:]
        if not group and event=='error':
            if args and isinstance(args[0],BaseException):raise args[0]
            from ._text_api import string
            value=args[0] if args else undefined
            detail=repr(value) if isinstance(value,str) else string(value) if value is None or value is undefined or isinstance(value,(bool,int,float)) else repr(value)
            raise _native.Error('Unhandled error. ('+detail+')')
        for raw in group:raw(*args)
        return bool(group)
    def listenerCount(self,event=undefined,listener=undefined,*extra):
        """Count original listener identities/total, integer/no units/errors, Node API."""
        raw=self._listeners.get(_key(event),[])
        return len(raw) if listener is undefined else sum(x is listener or getattr(x,'listener',None) is listener for x in raw)
    def listeners(self,event=undefined,*extra):
        """Copied original callbacks (unwrap once), no units/errors/native refs; Node API."""
        return [getattr(x,'listener',None) or x for x in self._listeners.get(_key(event),[])]
    def rawListeners(self,event=undefined,*extra):
        """Copied stable raw wrapper/callback identities, no units/errors; Node API."""
        return self._listeners.get(_key(event),[])[:]
    def eventNames(self,*extra):
        """Copied active keys in insertion order, no units/errors/native refs; Node API."""
        integer=lambda k:k.isascii() and k.isdigit() and str(int(k))==k and int(k)<2**32-1
        return sorted((k for k in self._listeners if integer(k)),key=int)+[k for k in self._listeners if not integer(k)]
    def getMaxListeners(self,*extra):
        """Read listener warning threshold, numeric count/no units/errors; Node API."""
        return self._max_listeners
    def setMaxListeners(self,n=undefined,*extra):
        """Set nonnegative numeric threshold, self/RangeError, Node API; metadata only.
        Warning/proxy/symbol host integration remains G0; no listener is discarded.
        """
        if isinstance(n,bool) or not isinstance(n,(int,float)):raise TypeError('The "setMaxListeners" argument must be of type number. Received '+_received(n))
        try:n=float(n)
        except OverflowError:n=-math.inf if n<0 else math.inf
        if math.isnan(n) or n<0:
            from ._text_api import string
            raise _native.RangeError('The value of "setMaxListeners" is out of range. It must be >= 0. Received '+string(n))
        self._max_listeners=n;return self
