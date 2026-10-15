"""Windows passive low-level hooks; UIA observations run outside callbacks."""
from __future__ import annotations
import ctypes,json,queue,sys,threading,time,os
from pathlib import Path
from ctypes import wintypes

ROLES={50000:'button',50002:'check_box',50003:'combo_box',50004:'text_field',50005:'link',50006:'image',50007:'list_item',50008:'list',50009:'menu',50011:'menu_item',50012:'progress_bar',50013:'radio_button',50014:'scroll_bar',50015:'slider',50018:'tab',50019:'tab_item',50020:'text',50023:'tree',50024:'tree_item',50025:'custom',50026:'group',50028:'data_grid',50029:'data_item',50030:'text_area',50032:'window',50033:'pane',50036:'table'}

def main():
    all_apps='--all' in sys.argv;permitted={int(p) for p in sys.argv[1:] if p.isdecimal()};excluded={int(p.split('=',1)[1]) for p in sys.argv[1:] if p.startswith('--exclude=')};stop_file=next((p.split('=',1)[1] for p in sys.argv[1:] if p.startswith('--stop-file=')),None);events=queue.Queue(maxsize=8192);ready=threading.Event();capture_started=threading.Event();stopped=threading.Event()
    def emit(body):
        print(json.dumps({'timestamp':time.time(),**body},ensure_ascii=False),flush=True)
    user=ctypes.WinDLL('user32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    user.GetForegroundWindow.restype=wintypes.HWND
    user.GetWindowLongPtrW.argtypes=[wintypes.HWND,ctypes.c_int];user.GetWindowLongPtrW.restype=ctypes.c_ssize_t
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    app_cache={}
    def application(pid):
        if pid in app_cache:return app_cache[pid]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:return None
        try:
            buf=ctypes.create_unicode_buffer(32768);size=wintypes.DWORD(len(buf))
            if not kernel.QueryFullProcessImageNameW(handle,0,buf,ctypes.byref(size)):return None
            path=buf.value
            if Path(path).name.lower() in {'explorer.exe','searchhost.exe','startmenuexperiencehost.exe','shellexperiencehost.exe'}:return None
            app_cache[pid]={'pid':pid,'name':Path(path).stem,'path':path,'bundle_id':''}
            return app_cache[pid]
        finally:kernel.CloseHandle(handle)
    def worker():
        sys.coinit_flags=0
        import comtypes
        comtypes.CoInitializeEx(0)
        from .windows_uia import WindowsUIA
        uia=WindowsUIA();api=uia.automation;types=uia.types;walker=api.ControlViewWalker;values={};down=None;dirty=set();last_editor=None
        def role_of(e):
            role=ROLES.get(e.CurrentControlType,'custom')
            return 'dialog' if role=='window' and e.CurrentClassName=='#32770' else role
        def describe(e):
            pid=e.CurrentProcessId
            if pid in excluded or (not all_apps and pid not in permitted) or e.CurrentIsPassword:return None
            app=application(pid)
            if not app:return None
            ancestors=[];p=e;window='';window_id=None;window_element=None
            for _ in range(32):
                p=walker.GetParentElement(p)
                if not p:break
                role=role_of(p);name=p.CurrentName or ''
                if p.CurrentControlType==50032:window=name;window_id=p.CurrentNativeWindowHandle;window_element=p
                if p.CurrentProcessId!=pid:break
                ancestors.append({'role':role,'name':name})
            rect=e.GetCurrentPropertyValue(types.UIA_BoundingRectanglePropertyId)
            if not window and e.CurrentControlType==50032:window=e.CurrentName;window_id=e.CurrentNativeWindowHandle;window_element=e
            anchor={'role':role_of(window_element),'name':window,'identifier':window_element.CurrentAutomationId or '', 'ancestors':[],'bounds':dict(zip(('x','y','width','height'),window_element.GetCurrentPropertyValue(types.UIA_BoundingRectanglePropertyId)))} if window_element else {}
            return {'window_role':role_of(window_element) if window_element else 'window','window_target':anchor,'captured':True,'app':app,'window_identity':'hwnd:'+str(window_id) if window_id else '', 'pid':pid,'role':role_of(e),'name':e.CurrentName or '', 'identifier':e.CurrentAutomationId or '', 'window':window,'ancestors':ancestors,'bounds':dict(zip(('x','y','width','height'),rect))}
        def at(x,y):
            point=types.tagPOINT();point.x=x;point.y=y
            target=api.ElementFromPoint(point)
            # Popup creation can finish before the UIA worker consumes mouseDown.
            # Bind a hit inside the closed combo's own box to that stable control,
            # rather than the newly opened list occupying the same point.
            current=target
            for _ in range(12):
                if not current:break
                if current.CurrentControlType==50003:
                    bx,by,bw,bh=current.GetCurrentPropertyValue(types.UIA_BoundingRectanglePropertyId)
                    if bx<=x<bx+bw and by<=y<by+bh:return current
                    break
                current=walker.GetParentElement(current)
            return target
        def editor_value(e,force=False):
            body=describe(e)
            if not body or body['role'] not in {'text_field','text_area','combo_box'}:return
            if body['role']=='combo_box':
                hwnd=e.CurrentNativeWindowHandle
                if hwnd and user.GetWindowLongPtrW(hwnd,-16)&3==3:return  # CBS_DROPDOWNLIST has no text editor.
                try:
                    pattern=e.GetCurrentPattern(types.UIA_ValuePatternId).QueryInterface(types.IUIAutomationValuePattern)
                    if pattern.CurrentIsReadOnly:return
                except Exception:return
            value=e.GetCurrentPropertyValue(types.UIA_ValueValuePropertyId)
            if not isinstance(value,str):
                try:value=e.GetCurrentPattern(types.UIA_TextPatternId).QueryInterface(types.IUIAutomationTextPattern).DocumentRange.GetText(32000)
                except Exception:return
            if not isinstance(value,str) or len(value)>32000:return
            identity=json.dumps([body['pid'],list(e.GetRuntimeId())])
            if ((body['role']!='combo_box' and identity in values and values[identity]!=value) or force):
                emit({**body,'kind':'edit','value':value})
            values[identity]=value
            return True
        def flush_previous():
            if last_editor:
                try:editor_value(last_editor)
                except Exception:pass  # Focus can leave a provider that has already closed.
        ready.set();capture_started.wait();last_poll=0
        while not stopped.is_set() or not events.empty():
            try:
                try:event=events.get(timeout=.05)
                except queue.Empty:event=None
                if event:
                    kind,x,y,value,stamp=event
                    if kind in ('down','right_down'):
                        hit=at(x,y)
                        if last_editor:
                            try:same=api.CompareElements(last_editor,hit)
                            except Exception:same=False
                            if not same:flush_previous()
                        body=describe(hit);down=(body,x,y,kind,stamp)
                        if isinstance(value,dict):value['ready'].set()
                    elif kind in ('up','right_up') and down:
                        body,sx,sy,button,start=down;down=None
                        if body:
                            drag=abs(x-sx)+abs(y-sy)>5
                            emit({**body,'timestamp':stamp,'kind':'drag' if drag else 'right_click' if button=='right_down' else 'click','x':sx,'y':sy,'end_x':x,'end_y':y,'duration':min(5,max(.05,stamp-start))})
                    elif kind=='scroll':
                        body=describe(at(x,y))
                        if body:emit({**body,'kind':'scroll','x':x,'y':y,'direction':'up' if value>0 else 'down','amount':min(100,max(1,abs(value)//120))})
                    elif kind=='key':
                        focused=api.GetFocusedElement()
                        if value in {'Enter','Tab','Escape'}:editor_value(focused,force=bool(dirty));dirty.clear()
                        body=describe(focused)
                        if body:emit({**body,'kind':'key','key':value})
                    elif kind=='text':dirty.add(True)
                if events.empty() and time.monotonic()-last_poll>.1:
                    last_poll=time.monotonic();e=api.GetFocusedElement()
                    if last_editor:
                        try:same=api.CompareElements(last_editor,e)
                        except Exception:same=False
                        if not same:flush_previous()
                    editable=editor_value(e,force=bool(dirty));dirty.clear();last_editor=e if editable else None
            except Exception as error:
                # UIA elements routinely disappear after clicks. Surface observations
                # that fail while a captured target still belongs to a recorded app.
                if event and kind in {'down','right_down','key','text'}:
                    pid=wintypes.DWORD();user.GetWindowThreadProcessId(user.GetForegroundWindow(),ctypes.byref(pid))
                    app=application(pid.value)
                    if app and pid.value not in excluded and (all_apps or pid.value in permitted):
                        emit({'captured':True,'kind':'unsupported','pid':pid.value,'app':app,'reason':'UI Automation observation failed: '+str(error)})
            finally:
                if event and kind in {'down','right_down'} and isinstance(value,dict):value['ready'].set()
        if last_editor:
            try:editor_value(last_editor,force=bool(dirty))
            except Exception:pass
        comtypes.CoUninitialize()
    worker_thread=threading.Thread(target=worker,daemon=True);worker_thread.start()
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
            if kind:
                value={'ready':threading.Event()} if kind in {'down','right_down'} else ctypes.c_short(e.mouseData>>16).value
                put((kind,e.pt.x,e.pt.y,value,time.time()))
                # Bound this handoff below Windows' hook timeout. The UIA worker
                # captures the target before the original click can open/close UI.
                if isinstance(value,dict):value['ready'].wait(.15)
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
            elif vk not in (16,17,18,91,92,160,161,162,163,164,165):put(('text',0,0,None,time.time()))
        return user.CallNextHookEx(None,code,message,data)
    hooks=[user.SetWindowsHookExW(14,mouse,kernel.GetModuleHandleW(None),0),user.SetWindowsHookExW(13,keyboard,kernel.GetModuleHandleW(None),0)]
    if not all(hooks):emit({'error':'Windows input hooks could not be installed'});return 1
    emit({'status':'recording','pids':sorted(permitted)});capture_started.set()
    thread_id=kernel.GetCurrentThreadId()
    # Create the thread message queue before the stopper can post WM_QUIT.
    pending=wintypes.MSG();user.PeekMessageW(ctypes.byref(pending),None,0,0,0)
    def stop_watch():
        while not stopped.wait(.05):
            if stop_file and Path(stop_file).exists():
                # Give the observer one last focused-value poll before draining its queue.
                time.sleep(.25);user.PostThreadMessageW(thread_id,0x12,0,0);return
    threading.Thread(target=stop_watch,daemon=True).start()
    try:
        msg=wintypes.MSG()
        while user.GetMessageW(ctypes.byref(msg),None,0,0)>0 and not stopped.is_set():user.TranslateMessage(ctypes.byref(msg));user.DispatchMessageW(ctypes.byref(msg))
    finally:
        stopped.set()
        for hook in hooks:user.UnhookWindowsHookEx(hook)
        worker_thread.join(timeout=2)
    return 0
if __name__=='__main__':raise SystemExit(main())
