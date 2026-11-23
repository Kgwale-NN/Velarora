"""Native evidence for supported app labels; no full process list is transmitted."""
import psutil


def normalize(rect,desktop):
    left,top,width,height=desktop
    x1,y1,x2,y2=rect
    x1=max(left,x1);y1=max(top,y1);x2=min(left+width,x2);y2=min(top+height,y2)
    if x2<=x1 or y2<=y1:return None
    return [(x1-left)/width,(y1-top)/height,(x2-left)/width,(y2-top)/height]


def window_boxes(all_screens=False,frame_shape=None):
    import ctypes
    from ctypes import wintypes
    import sys
    if sys.platform!='win32':return None
    previous=None
    try:
        user32=ctypes.windll.user32
        if hasattr(user32,'SetThreadDpiAwarenessContext'):
            user32.SetThreadDpiAwarenessContext.argtypes=[ctypes.c_void_p]
            user32.SetThreadDpiAwarenessContext.restype=ctypes.c_void_p
            previous=user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
        names={p.pid:(p.info.get('name') or '').casefold() for p in psutil.process_iter(['name'])}
        pids={pid for pid,name in names.items() if name=='notepad.exe'}
        if not pids:return []
        primary=(0,0,user32.GetSystemMetrics(0),user32.GetSystemMetrics(1))
        virtual=tuple(user32.GetSystemMetrics(i) for i in (76,77,78,79))
        if frame_shape:
            ratio=frame_shape[1]/frame_shape[0]
            all_screens=abs(ratio-virtual[2]/virtual[3])<abs(ratio-primary[2]/primary[3])-.01
        desktop=virtual if all_screens else primary
        user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
        callback=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
        found=[];boxes=[]
        def owner(hwnd):
            pid=wintypes.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid));return pid.value
        @callback
        def visit(hwnd,_):
            pid=owner(hwnd);matches=pid in pids
            if not matches and names.get(pid)=='applicationframehost.exe':
                children=[]
                @callback
                def child(handle,_):
                    if owner(handle) in pids:children.append(handle)
                    return True
                user32.EnumChildWindows(hwnd,child,0)
                matches=bool(children)
            if matches:
                found.append(hwnd)
                if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
                    rect=wintypes.RECT()
                    if user32.GetWindowRect(hwnd,ctypes.byref(rect)):
                        box=normalize((rect.left,rect.top,rect.right,rect.bottom),desktop)
                        if box is not None:boxes.append(box)
            return True
        user32.EnumWindows(visit,0)
        return boxes[:16] if found else None
    except (psutil.Error,OSError,AttributeError):
        return None
    finally:
        if previous:ctypes.windll.user32.SetThreadDpiAwarenessContext(previous)


def snapshot():
    try:
        names={(p.info.get('name') or '').casefold() for p in psutil.process_iter(['name'])}
        return {'notepad.exe':'notepad.exe' in names}
    except (psutil.Error,OSError):
        return None
