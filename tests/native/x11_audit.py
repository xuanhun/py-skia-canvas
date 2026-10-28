"""Test-only X11 capture/input of the exact named fixture window, via system Xlib/XTest.
No production dependency and no capture of unrelated windows. TrueColor depth24/32 only.
"""
import ctypes as C,json,sys,time
from pathlib import Path
X=C.CDLL('libX11.so.6');T=C.CDLL('libXtst.so.6');P=C.c_void_p;U=C.c_ulong;I=C.c_int
def bind(lib,name,restype,args):
    """Declare stable public Xlib/XTest ABI, returns function; test-only, no Skia refs."""
    f=getattr(lib,name);f.restype=restype;f.argtypes=args;return f
open_display=bind(X,'XOpenDisplay',P,[C.c_char_p]);root_window=bind(X,'XDefaultRootWindow',U,[P]);query=bind(X,'XQueryTree',I,[P,U,C.POINTER(U),C.POINTER(U),C.POINTER(C.POINTER(U)),C.POINTER(C.c_uint)]);fetch=bind(X,'XFetchName',I,[P,U,C.POINTER(P)]);free=bind(X,'XFree',I,[P]);sync=bind(X,'XSync',I,[P,I]);close=bind(X,'XCloseDisplay',I,[P])
geometry=bind(X,'XGetGeometry',I,[P,U,C.POINTER(U),C.POINTER(I),C.POINTER(I),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint)])
get_image=bind(X,'XGetImage',P,[P,U,I,I,C.c_uint,C.c_uint,U,I]);get_pixel=bind(X,'XGetPixel',U,[P,I,I]);destroy_image=bind(X,'XDestroyImage',I,[P]);focus=bind(X,'XSetInputFocus',I,[P,U,I,U]);raise_window=bind(X,'XRaiseWindow',I,[P,U]);move_resize=bind(X,'XMoveResizeWindow',I,[P,U,I,I,C.c_uint,C.c_uint]);translate=bind(X,'XTranslateCoordinates',I,[P,U,U,I,I,C.POINTER(I),C.POINTER(I),C.POINTER(U)])
keysym=bind(X,'XStringToKeysym',U,[C.c_char_p]);keycode=bind(X,'XKeysymToKeycode',C.c_ubyte,[P,U]);fake_key=bind(T,'XTestFakeKeyEvent',I,[P,C.c_uint,I,U]);fake_button=bind(T,'XTestFakeButtonEvent',I,[P,C.c_uint,I,U]);fake_motion=bind(T,'XTestFakeMotionEvent',I,[P,I,I,I,U])

def find(display,window,title):
    """Find exact fixture title recursively; no unrelated titles/content are emitted/saved."""
    name=P()
    if fetch(display,window,C.byref(name)) and name.value:
        try:
            if C.string_at(name)==title:return window
        finally:free(name)
    root=U();parent=U();children=C.POINTER(U)();n=C.c_uint()
    if query(display,window,C.byref(root),C.byref(parent),C.byref(children),C.byref(n)):
        try:
            for i in range(n.value):
                result=find(display,children[i],title)
                if result:return result
        finally:
            if children:free(children)
    return None

def main():
    """Capture named true client pixels or inject real XTest events; output owned evidence.
    X11 only, frame/title checks reject missing display/window. No GUI/GPU context transfer.
    """
    title,action,destination=sys.argv[1:];display=open_display(None);assert display,'XOpenDisplay failed'
    try:
        root=root_window(display);window=find(display,root,title.encode());assert window,'Fixture window missing'
        rr=U();x=I();y=I();w=C.c_uint();h=C.c_uint();border=C.c_uint();depth=C.c_uint();assert geometry(display,window,C.byref(rr),C.byref(x),C.byref(y),C.byref(w),C.byref(h),C.byref(border),C.byref(depth));assert depth.value in (24,32),depth.value
        if action in ('input','default-close'):
            raise_window(display,window);focus(display,window,2,0);sync(display,0);time.sleep(.5)
            if action=='input':
                rx=I();ry=I();child=U();translate(display,window,root,20,30,C.byref(rx),C.byref(ry),C.byref(child));assert rx.value>=0 and ry.value>=0,'Fixture client point is outside visible X11 screen';fake_motion(display,-1,rx.value,ry.value,0);sync(display,0);time.sleep(.03);fake_button(display,1,1,0);fake_button(display,1,0,0);fake_button(display,4,1,0);fake_button(display,4,0,0)
                for key in ['a']:
                    code=keycode(display,keysym(key.encode()));assert code;fake_key(display,code,1,0);fake_key(display,code,0,0)
            ctrl=keycode(display,keysym(b'Control_L'));code=keycode(display,keysym(b'c'));assert ctrl and code
            fake_key(display,ctrl,1,0);fake_key(display,code,1,0);fake_key(display,code,0,0);fake_key(display,ctrl,0,0);sync(display,0);time.sleep(.1)
        elif action=='resize':move_resize(display,window,10,10,200,120);sync(display,0);time.sleep(.1)
        else:
            sync(display,0);image=get_image(display,window,0,0,w.value,h.value,U(-1).value,2);assert image,'XGetImage failed'
            try:
                raw=bytearray()
                for yy in range(h.value):
                    for xx in range(w.value):
                        pixel=get_pixel(image,xx,yy);raw.extend(((pixel>>16)&255,(pixel>>8)&255,pixel&255,255))
            finally:destroy_image(image)
            Path(destination+'.rgba').write_bytes(raw)
        Path(destination+'.json').write_text(json.dumps(dict(title=title,action=action,width=w.value,height=h.value,depth=depth.value,x=x.value,y=y.value))+'\n')
    finally:close(display)

if __name__=='__main__':main()
