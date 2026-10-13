"""Exact installed application identity, bounded startup, no shell or document reopening."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path


def recorder_helper():
    if sys.platform!='darwin':raise RuntimeError('Manual recording currently requires macOS')
    source=Path(__file__).parent/'native/macos_record.swift'
    cache=Path.home()/'Library/Caches/Bokkio/native/recording'/hashlib.sha256(source.read_bytes()).hexdigest()
    cache.mkdir(parents=True,exist_ok=True,mode=0o700);target=cache/'record'
    if not target.exists():
        fd,name=tempfile.mkstemp(dir=cache);os.close(fd)
        try:
            r=subprocess.run(['xcrun','swiftc','-framework','Cocoa',str(source),'-o',name],capture_output=True,timeout=60)
            if r.returncode:raise RuntimeError('Recorder compilation failed: '+r.stderr.decode()[-1800:])
            os.chmod(name,0o700);os.replace(name,target)
        finally:Path(name).unlink(missing_ok=True)
    return target


def installed_running_apps():
    if sys.platform=='darwin':
        r=subprocess.run([str(recorder_helper()),'--apps'],capture_output=True,timeout=5,check=True)
        return json.loads(r.stdout)['apps']
    if sys.platform=='win32':
        from .xa11y_backend import Xa11yBackend
        import ctypes as c
        from ctypes import wintypes as w
        k=c.WinDLL('kernel32',use_last_error=True)
        k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
        k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,c.POINTER(w.DWORD)]
        k.CloseHandle.argtypes=[w.HANDLE]
        result=[]
        for app in Xa11yBackend().apps():
            h=k.OpenProcess(0x1000,False,app['pid'])
            if not h:continue
            try:
                size=w.DWORD(32768);buf=c.create_unicode_buffer(size.value)
                if k.QueryFullProcessImageNameW(h,0,buf,c.byref(size)):result.append({**app,'path':buf.value,'bundle_id':''})
            finally:k.CloseHandle(h)
        return result
    raise RuntimeError('Native application identity requires macOS or Windows')


def launch_grant(policy,alias,scope):
    grants=policy.get('launch_apps',{})
    if not isinstance(grants,dict) or alias not in grants or scope.get('launch_apps',{}).get(alias)!=grants[alias]:
        raise ValueError('Application launch is outside administrator grants or was changed')
    g=grants[alias]
    if not isinstance(g,dict) or set(g)-{'name','path','bundle_id'} or not isinstance(g.get('name'),str) or g['name'] not in policy['apps']:
        raise ValueError('Launch identity must be an authorized application name')
    path=Path(g.get('path',''))
    if not path.is_absolute() or not path.exists() or path.resolve()!=path or (sys.platform=='darwin' and path.suffix!='.app') or (sys.platform=='win32' and path.suffix.lower()!='.exe'):
        raise ValueError('Launch requires an exact existing installed application path')
    return g


def matching_apps(grant,apps=None):
    matches=[a for a in (installed_running_apps() if apps is None else apps) if a['name']==grant['name'] and a['path']==grant['path'] and (not grant.get('bundle_id') or a.get('bundle_id')==grant['bundle_id'])]
    if len(matches)>1:raise ValueError('Multiple matching application instances; choose one explicitly')
    return matches


def desktop_environment():
    if sys.platform=='darwin':
        return json.loads(subprocess.run([str(recorder_helper()),'--environment'],capture_output=True,timeout=5,check=True).stdout)
    if sys.platform=='win32':
        import ctypes as c
        from ctypes import wintypes as w
        user=c.WinDLL('user32');user.GetForegroundWindow.restype=w.HWND
        pid=w.DWORD();user.GetWindowThreadProcessId(user.GetForegroundWindow(),c.byref(pid))
        point=w.POINT();user.GetCursorPos(c.byref(point))
        return {'foreground_pid':pid.value,'pointer':{'x':point.x,'y':point.y}}
    raise RuntimeError('A desktop session is required for background native actions')

def ensure_running(grant,*,inventory=None,launch=None,timeout=12,background=False):
    inventory=inventory or installed_running_apps
    rows=matching_apps(grant,inventory());started=False
    before=desktop_environment()['foreground_pid'] if background and not rows and launch is None else None
    if not rows:
        if launch:launch(grant)
        elif sys.platform=='darwin':subprocess.run(['open',*(['-g'] if background else []),'-a',grant['path']],capture_output=True,timeout=8,check=True)
        elif sys.platform=='win32':
            startup=None
            if background:startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=4
            subprocess.Popen([grant['path']],startupinfo=startup,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:raise RuntimeError('Unsupported launch platform')
        started=True;deadline=time.monotonic()+timeout
        while not rows and time.monotonic()<deadline:
            time.sleep(.1);rows=matching_apps(grant,inventory())
    if not rows:raise TimeoutError('Authorized application did not become ready')
    if before is not None and before!=rows[0]['pid'] and desktop_environment()['foreground_pid']==rows[0]['pid']:
        from .model import BokkioCompletionUnknown
        raise BokkioCompletionUnknown('Application activated itself despite background startup; inspect before continuing')
    return {'pid':rows[0]['pid'],'name':grant['name'],'launched':started,'path':grant['path'],'background_requested':background}
