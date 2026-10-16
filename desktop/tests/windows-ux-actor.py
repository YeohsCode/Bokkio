"""UX benchmark actor: UIA only reads; all writes are real mouse/key input.

Never import Runtime, Client, a recorder, or invoke a UIA action/pattern setter.
The caller must provide an owned Notepad document. Character Map is opened
through the Windows Run UI after recording starts.
"""
from __future__ import annotations
import ctypes as c
from ctypes import wintypes as w
import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from bokkio.windows_uia import WindowsUIA

u=c.WinDLL('user32',use_last_error=True);u.SetProcessDpiAwarenessContext(c.c_void_p(-4))
u.GetForegroundWindow.restype=w.HWND
u.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
u.SetForegroundWindow.argtypes=[w.HWND]
u.AttachThreadInput.argtypes=[w.DWORD,w.DWORD,w.BOOL]
k=c.WinDLL('kernel32');k.GetCurrentThreadId.restype=w.DWORD
class Mouse(c.Structure):_fields_=[('x',w.LONG),('y',w.LONG),('data',w.DWORD),('flags',w.DWORD),('time',w.DWORD),('extra',c.c_size_t)]
class Keyboard(c.Structure):_fields_=[('vk',w.WORD),('scan',w.WORD),('flags',w.DWORD),('time',w.DWORD),('extra',c.c_size_t)]
class Union(c.Union):_fields_=[('mouse',Mouse),('key',Keyboard)]
class Input(c.Structure):_fields_=[('kind',w.DWORD),('data',Union)]
u.SendInput.argtypes=[w.UINT,c.POINTER(Input),c.c_int];u.SendInput.restype=w.UINT

def send(events):
    array=(Input*len(events))(*events)
    if u.SendInput(len(events),array,c.sizeof(Input))!=len(events):raise RuntimeError('Partial SendInput in UX benchmark')
def key(vk,up=False):return Input(1,Union(key=Keyboard(vk,0,2 if up else 0,0,0)))
def combo(*keys):send([key(v) for v in keys]+[key(v,True) for v in reversed(keys)])
def text(value):
    encoded=value.encode('utf-16-le')
    for i in range(0,len(encoded),2):
        scan=int.from_bytes(encoded[i:i+2],'little')
        send([Input(1,Union(key=Keyboard(0,scan,4,0,0))),Input(1,Union(key=Keyboard(0,scan,6,0,0)))])
def click(e):
    x,y,width,height=e.GetCurrentPropertyValue(t.UIA_BoundingRectanglePropertyId)
    if width<=0 or height<=0:raise RuntimeError('UX target is not visible')
    u.SetCursorPos(round(x+width/2),round(y+height/2))
    send([Input(0,Union(mouse=Mouse(0,0,0,2,0,0))),Input(0,Union(mouse=Mouse(0,0,0,4,0,0)))])

a=WindowsUIA();api=a.automation;t=a.types

def windows():
    collection=api.GetRootElement().FindAll(t.TreeScope_Children,api.CreateTrueCondition())
    return [collection.GetElement(i) for i in range(collection.Length)]
def window(kind):
    matches=[e for e in windows() if (e.CurrentClassName=='Notepad' if kind=='editor' else e.CurrentName=='Character Map')]
    if len(matches)!=1:raise RuntimeError('Expected one owned '+kind+' window, found '+str(len(matches)))
    return matches[0]
def foreground(e):
    hwnd=e.CurrentNativeWindowHandle;front=u.GetForegroundWindow();thread=u.GetWindowThreadProcessId(front,None);current=k.GetCurrentThreadId()
    attached=bool(u.AttachThreadInput(current,thread,True)) if thread!=current else False
    try:u.ShowWindow(hwnd,9);u.SetForegroundWindow(hwnd);u.BringWindowToTop(hwnd)
    finally:
        if attached:u.AttachThreadInput(current,thread,False)
    time.sleep(.15)
    if u.GetForegroundWindow()!=hwnd:raise RuntimeError('UX window activation failed')
def descendants(e,kind):
    matches=e.FindAll(t.TreeScope_Descendants,api.CreatePropertyCondition(t.UIA_ControlTypePropertyId,kind))
    return [matches.GetElement(i) for i in range(matches.Length)]
def editor():
    root=window('editor');fields=descendants(root,50004)+descendants(root,50030)
    if len(fields)!=1:raise RuntimeError('Owned Notepad editor is ambiguous')
    return root,fields[0]
def font():
    root=window('font');fields=descendants(root,50003)
    labeled=[e for e in fields if e.CurrentName.replace('&','').strip().lower() in {'font:','font'}]
    fields=labeled or fields
    if len(fields)!=1:raise RuntimeError('Character Map font field is ambiguous')
    return root,fields[0]
def value(e):
    v=e.GetCurrentPropertyValue(t.UIA_ValueValuePropertyId)
    if isinstance(v,str):return v
    return e.GetCurrentPattern(t.UIA_TextPatternId).QueryInterface(t.IUIAutomationTextPattern).DocumentRange.GetText(32000)
def read():
    result={'editor':value(editor()[1])}
    try:result['font']=value(font()[1])
    except RuntimeError:result['font']=None
    return result

request=json.loads(sys.argv[1]);command=request['command']
if command in {'editor','font'}:
    root,e=editor() if command=='editor' else font();foreground(root);click(e)
    if command=='editor':
        combo(17,65)
        if request['value']:text(request['value'])
        else:combo(8)
    else:
        # Character Map uses a selection-only combo: Unicode text injection is
        # not a user selection. Traverse its actual keyboard UI from Home.
        combo(27);time.sleep(.08)  # Close the list after exercising its actual opening click.
        for _ in range(20):
            if api.CompareElements(api.GetFocusedElement(),e):break
            combo(9)
        else:raise RuntimeError('Font combo did not receive keyboard focus')
        combo(36);time.sleep(.03)
        for _ in range(180):
            if value(e)==request['value']:break
            combo(40);time.sleep(.02)
        else:raise RuntimeError('Font is not available in Character Map')
    time.sleep(.3)
elif command=='close-second':
    matches=[e for e in windows() if e.CurrentName=='Character Map']
    if matches:foreground(matches[0]);combo(18,115);time.sleep(.2)
elif command=='open-second':
    if any(e.CurrentName=='Character Map' for e in windows()):raise RuntimeError('Close Character Map before the newly-opened-app benchmark')
    combo(91,82);time.sleep(.35);text('charmap.exe');combo(13)
    until=time.monotonic()+10
    while True:
        try:window('font');break
        except RuntimeError:
            if time.monotonic()>until:raise
            time.sleep(.1)
elif command!='read':raise RuntimeError('Unknown UX benchmark command')
print(json.dumps(read(),ensure_ascii=False))
