"""Capture/send test messages only to an exact-title HWND owned by a supplied test PID."""
import ctypes as C,json,sys,time
from ctypes import wintypes as W
from pathlib import Path
u=C.WinDLL('user32',use_last_error=True);g=C.WinDLL('gdi32',use_last_error=True)
def bind(lib,name,result,args):
    f=getattr(lib,name);f.restype=result;f.argtypes=args;return f
bind(u,'FindWindowW',W.HWND,[W.LPCWSTR,W.LPCWSTR]);bind(u,'GetWindowThreadProcessId',W.DWORD,[W.HWND,C.POINTER(W.DWORD)])
bind(u,'GetClientRect',W.BOOL,[W.HWND,C.POINTER(W.RECT)]);bind(u,'GetDC',W.HDC,[W.HWND]);bind(u,'ReleaseDC',C.c_int,[W.HWND,W.HDC])
bind(g,'CreateCompatibleDC',W.HDC,[W.HDC]);bind(g,'DeleteDC',W.BOOL,[W.HDC]);bind(g,'SelectObject',W.HANDLE,[W.HDC,W.HANDLE]);bind(g,'DeleteObject',W.BOOL,[W.HANDLE])
bind(g,'BitBlt',W.BOOL,[W.HDC,C.c_int,C.c_int,C.c_int,C.c_int,W.HDC,C.c_int,C.c_int,W.DWORD])
bind(g,'CreateDIBSection',W.HBITMAP,[W.HDC,C.c_void_p,W.UINT,C.POINTER(C.c_void_p),W.HANDLE,W.DWORD])
bind(u,'PostMessageW',W.BOOL,[W.HWND,W.UINT,W.WPARAM,W.LPARAM]);bind(u,'SetWindowPos',W.BOOL,[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT])
class Header(C.Structure):
    _fields_=[('size',W.DWORD),('width',W.LONG),('height',W.LONG),('planes',W.WORD),('bits',W.WORD),('compression',W.DWORD),('bytes',W.DWORD),('x',W.LONG),('y',W.LONG),('used',W.DWORD),('important',W.DWORD)]

def owned_process(actual,root):
    """Check exact PID or its launcher ancestry; Windows venv python.exe is a proxy.
    Process IDs only, no command line/content inspection. Owner chain must reach
    the test process started by this controller, never an unrelated matching title.
    """
    if actual==root:return True
    class Entry(C.Structure):
        _fields_=[('size',W.DWORD),('usage',W.DWORD),('pid',W.DWORD),('heap',C.c_size_t),('module',W.DWORD),('threads',W.DWORD),('parent',W.DWORD),('priority',W.LONG),('flags',W.DWORD),('exe',W.WCHAR*260)]
    k=C.WinDLL('kernel32',use_last_error=True);snapshot=bind(k,'CreateToolhelp32Snapshot',W.HANDLE,[W.DWORD,W.DWORD])(2,0);assert snapshot!=C.c_void_p(-1).value
    first=bind(k,'Process32FirstW',W.BOOL,[W.HANDLE,C.POINTER(Entry)]);next_=bind(k,'Process32NextW',W.BOOL,[W.HANDLE,C.POINTER(Entry)]);parents={};entry=Entry();entry.size=C.sizeof(entry)
    try:
        okay=first(snapshot,C.byref(entry))
        while okay:
            parents[entry.pid]=entry.parent;okay=next_(snapshot,C.byref(entry))
    finally:bind(k,'CloseHandle',W.BOOL,[W.HANDLE])(snapshot)
    seen=set()
    while actual not in seen:
        if actual==root:return True
        seen.add(actual);actual=parents.get(actual,0)
    return False

class WhiteBackdrop:
    """Owned opaque test window behind the client, isolating composited transparency.
    Physical pixels, caller main thread only. Win32 errors raise; close destroys only
    this test HWND. No desktop content or unrelated HWND is read or controlled.
    """
    def __enter__(self):
        create=bind(u,'CreateWindowExW',W.HWND,[W.DWORD,W.LPCWSTR,W.LPCWSTR,W.DWORD,C.c_int,C.c_int,C.c_int,C.c_int,W.HWND,W.HMENU,W.HINSTANCE,C.c_void_p])
        self.hwnd=create(0x08000000,'STATIC','py-skia-canvas-owned-white-backdrop',0x90000006,180,180,260,180,None,None,None,None)
        if not self.hwnd:raise C.WinError(C.get_last_error())
        bind(u,'UpdateWindow',W.BOOL,[W.HWND])(self.hwnd);return self
    def pump(self):
        peek=bind(u,'PeekMessageW',W.BOOL,[C.POINTER(W.MSG),W.HWND,W.UINT,W.UINT,W.UINT]);translate_=bind(u,'TranslateMessage',W.BOOL,[C.POINTER(W.MSG)]);dispatch=bind(u,'DispatchMessageW',C.c_ssize_t,[C.POINTER(W.MSG)]);msg=W.MSG()
        while peek(C.byref(msg),None,0,0,1):translate_(C.byref(msg));dispatch(C.byref(msg))
    def __exit__(self,*args):
        bind(u,'DestroyWindow',W.BOOL,[W.HWND])(self.hwnd)

def main():
    """Own test HWND only. Pixel sizes physical; RGBA is opaque DWM/GDI client RGB.

    No whole-desktop capture or input to other applications. Raises on mismatched
    PID, empty frames or API failure. Win32 messages are synthetic OS test input.
    Sources: Win32 GetClientRect/BitBlt/CreateDIBSection/PostMessage interfaces.
    """
    title,pid,action,dest=sys.argv[1:];dest=Path(dest)
    if hasattr(u,'SetProcessDpiAwarenessContext'):
        bind(u,'SetProcessDpiAwarenessContext',W.BOOL,[C.c_void_p])(C.c_void_p(-4))
    hwnd=u.FindWindowW(None,title);actual=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(actual));assert hwnd and owned_process(actual.value,int(pid)),'Not the owned test HWND'
    if action=='resize':
        assert u.SetWindowPos(hwnd,None,0,0,200,120,0x0002|0x0004);time.sleep(.12)
    elif action=='input':
        point=20|(30<<16)
        for msg,w,l in [(0x200,0,point),(0x201,1,point),(0x202,0,point),(0x100,0x41,1|(0x1e<<16)),(0x102,ord('a'),1),(0x101,0x41,1|(0x1e<<16)|(3<<30))]:assert u.PostMessageW(hwnd,msg,w,l)
        time.sleep(.12)
    elif action!='capture':raise ValueError(action)
    rect=W.RECT();assert u.GetClientRect(hwnd,C.byref(rect));width,height=rect.right,rect.bottom;assert width>0 and height>0
    source=u.GetDC(hwnd);target=g.CreateCompatibleDC(source);bits=C.c_void_p();header=Header(C.sizeof(Header),width,-height,1,32,0,width*height*4,0,0,0,0);bitmap=g.CreateDIBSection(source,C.byref(header),0,C.byref(bits),None,0);assert bitmap and bits.value
    old=g.SelectObject(target,bitmap)
    try:
        assert g.BitBlt(target,0,0,width,height,source,0,0,0x00cc0020)
        bgra=C.string_at(bits,width*height*4);rgba=bytearray(len(bgra));rgba[0::4]=bgra[2::4];rgba[1::4]=bgra[1::4];rgba[2::4]=bgra[0::4];rgba[3::4]=b'\xff'*(width*height)
        colors=len({bytes(rgba[i:i+3]) for i in range(0,len(rgba),4)})
        assert colors>20,'Blank/unpresented native client frame'
        dest.with_suffix('.rgba').write_bytes(rgba);dest.with_suffix('.json').write_text(json.dumps(dict(title=title,pid=actual.value,width=width,height=height,colors=colors,format='Opaque RGBA8 from exact client GDI RGB; no desktop crop'))+'\n')
    finally:g.SelectObject(target,old);g.DeleteObject(bitmap);g.DeleteDC(target);u.ReleaseDC(hwnd,source)
if __name__=='__main__':main()
