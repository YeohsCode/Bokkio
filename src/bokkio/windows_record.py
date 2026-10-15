"""Windows passive low-level hooks; UIA observations run outside callbacks."""
from __future__ import annotations
import ctypes,json,queue,sys,threading,time
from ctypes import wintypes

ROLES={50000:'button',50002:'check_box',50003:'combo_box',50004:'text_field',50005:'link',50006:'image',50007:'list_item',50008:'list',50009:'menu',50011:'menu_item',50012:'progress_bar',50013:'radio_button',50014:'scroll_bar',50015:'slider',50018:'tab',50019:'tab_item',50020:'text',50023:'tree',50024:'tree_item',50025:'custom',50026:'group',50028:'data_grid',50029:'data_item',50030:'text_area',50032:'window',50033:'pane',50036:'table'}

def main():
    permitted={int(p) for p in sys.argv[1:]};events=queue.Queue(maxsize=8192);ready=threading.Event();capture_started=threading.Event();stopped=threading.Event()
    def emit(body):
        print(json.dumps({'timestamp':time.time(),**body},ensure_ascii=False),flush=True)
    user=ctypes.WinDLL('user32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    def worker():
        sys.coinit_flags=0
        import comtypes
        comtypes.CoInitializeEx(0)
        from .windows_uia import WindowsUIA
        uia=WindowsUIA();api=uia.automation;types=uia.types;walker=api.ControlViewWalker;values={};down=None
        def describe(e):
            pid=e.CurrentProcessId
            if pid not in permitted or e.CurrentIsPassword:return None
            ancestors=[];p=e;window='';window_id=None
            for _ in range(32):
                p=walker.GetParentElement(p)
                if not p:break
                role=ROLES.get(p.CurrentControlType,'custom');name=p.CurrentName or ''
                if p.CurrentControlType==50032:window=name;window_id=p.CurrentNativeWindowHandle
                if p.CurrentProcessId!=pid:break
                ancestors.append({'role':role,'name':name})
            rect=e.GetCurrentPropertyValue(types.UIA_BoundingRectanglePropertyId)
            if not window and e.CurrentControlType==50032:window=e.CurrentName
            return {'window_identity':'hwnd:'+str(window_id) if window_id else '', 'pid':pid,'role':ROLES.get(e.CurrentControlType,'custom'),'name':e.CurrentName or '', 'identifier':e.CurrentAutomationId or '', 'window':window,'ancestors':ancestors,'bounds':dict(zip(('x','y','width','height'),rect))}
        def at(x,y):
            point=types.tagPOINT();point.x=x;point.y=y
            return api.ElementFromPoint(point)
        ready.set();capture_started.wait();last_poll=0
        while not stopped.is_set():
            try:
                try:event=events.get(timeout=.05)
                except queue.Empty:event=None
                if event:
                    kind,x,y,value,stamp=event
                    if kind in ('down','right_down'):
                        body=describe(at(x,y));down=(body,x,y,kind,stamp)
                    elif kind in ('up','right_up') and down:
                        body,sx,sy,button,start=down;down=None
                        if body:
                            drag=abs(x-sx)+abs(y-sy)>5
                            emit({**body,'timestamp':stamp,'kind':'drag' if drag else 'right_click' if button=='right_down' else 'click','x':sx,'y':sy,'end_x':x,'end_y':y,'duration':min(5,max(.05,stamp-start))})
                    elif kind=='scroll':
                        body=describe(at(x,y))
                        if body:emit({**body,'kind':'scroll','x':x,'y':y,'direction':'up' if value>0 else 'down','amount':min(100,max(1,abs(value)//120))})
                    elif kind=='key':
                        body=describe(api.GetFocusedElement())
                        if body:emit({**body,'kind':'key','key':value})
                if time.monotonic()-last_poll>.2:
                    last_poll=time.monotonic();e=api.GetFocusedElement();body=describe(e)
                    if body and body['role'] in {'text_field','text_area','combo_box'}:
                        value=e.GetCurrentPropertyValue(types.UIA_ValueValuePropertyId)
                        if not isinstance(value,str):
                            try:
                                pattern=e.GetCurrentPattern(types.UIA_TextPatternId).QueryInterface(types.IUIAutomationTextPattern);value=pattern.DocumentRange.GetText(32000)
                            except Exception:value=None
                        if isinstance(value,str) and len(value)<=32000:
                            identity=json.dumps({k:body[k] for k in ('pid','role','name','identifier','ancestors')},sort_keys=True)
                            if identity in values and values[identity]!=value:emit({**body,'kind':'edit','value':value})
                            values[identity]=value
            except Exception as error:emit({'kind':'unsupported','pid':next(iter(permitted),0),'reason':str(error)})
    threading.Thread(target=worker,daemon=True).start()
    if not ready.wait(15):emit({'error':'Windows UI Automation could not initialize'});return 1
    ULONG_PTR=ctypes.c_size_t
    class Mouse(ctypes.Structure):_fields_=[('pt',wintypes.POINT),('mouseData',wintypes.DWORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ULONG_PTR)]
    class Keyboard(ctypes.Structure):_fields_=[('vkCode',wintypes.DWORD),('scanCode',wintypes.DWORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ULONG_PTR)]
    CALLBACK=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM)
    user.CallNextHookEx.argtypes=[wintypes.HHOOK,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM];user.CallNextHookEx.restype=ctypes.c_ssize_t
    user.SetWindowsHookExW.argtypes=[ctypes.c_int,CALLBACK,wintypes.HINSTANCE,wintypes.DWORD];user.SetWindowsHookExW.restype=wintypes.HHOOK
    kernel.GetModuleHandleW.argtypes=[wintypes.LPCWSTR];kernel.GetModuleHandleW.restype=wintypes.HMODULE
    user.GetAsyncKeyState.argtypes=[ctypes.c_int];user.GetAsyncKeyState.restype=ctypes.c_short
    def put(event):
        try:events.put_nowait(event)
        except queue.Full:emit({'error':'Recording event queue overflowed; stop and inspect the incomplete recording'});stopped.set()
    @CALLBACK
    def mouse(code,message,data):
        if code>=0:
            e=ctypes.cast(data,ctypes.POINTER(Mouse)).contents
            kind={0x201:'down',0x202:'up',0x204:'right_down',0x205:'right_up',0x20a:'scroll'}.get(message)
            if kind:put((kind,e.pt.x,e.pt.y,ctypes.c_short(e.mouseData>>16).value,time.time()))
        return user.CallNextHookEx(None,code,message,data)
    pressed={vk for vk in range(256) if user.GetAsyncKeyState(vk)&0x8000}
    @CALLBACK
    def keyboard(code,message,data):
        if code>=0 and message in (0x100,0x104,0x101,0x105):
            e=ctypes.cast(data,ctypes.POINTER(Keyboard)).contents;vk=e.vkCode
            if message in (0x101,0x105):pressed.discard(vk);return user.CallNextHookEx(None,code,message,data)
            if vk in pressed:return user.CallNextHookEx(None,code,message,data)
            pressed.add(vk)
            mods=[name for key,name in ((0x11,'Ctrl'),(0x12,'Alt'),(0x5b,'Win'),(0x10,'Shift')) if user.GetAsyncKeyState(key)&0x8000]
            if 'Ctrl' in mods and 'Shift' in mods and vk in (80,82,123):return user.CallNextHookEx(None,code,message,data)
            named={13:'Enter',9:'Tab',27:'Escape',37:'Left',38:'Up',39:'Right',40:'Down',36:'Home',35:'End',33:'PageUp',34:'PageDown'}
            key=named.get(vk) or (chr(vk) if 48<=vk<=90 and any(m in mods for m in ('Ctrl','Alt','Win')) else 'F'+str(vk-111) if 112<=vk<=135 else None)
            if key:put(('key',0,0,'+'.join(mods+[key]),time.time()))
        return user.CallNextHookEx(None,code,message,data)
    hooks=[user.SetWindowsHookExW(14,mouse,kernel.GetModuleHandleW(None),0),user.SetWindowsHookExW(13,keyboard,kernel.GetModuleHandleW(None),0)]
    if not all(hooks):emit({'error':'Windows input hooks could not be installed'});return 1
    emit({'status':'recording','pids':sorted(permitted)});capture_started.set()
    try:
        msg=wintypes.MSG()
        while user.GetMessageW(ctypes.byref(msg),None,0,0)>0 and not stopped.is_set():user.TranslateMessage(ctypes.byref(msg));user.DispatchMessageW(ctypes.byref(msg))
    finally:
        stopped.set()
        for hook in hooks:user.UnhookWindowsHookEx(hook)
    return 0
if __name__=='__main__':raise SystemExit(main())
