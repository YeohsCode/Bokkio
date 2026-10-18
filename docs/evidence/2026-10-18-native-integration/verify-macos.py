import ctypes as c,json,os,subprocess,time,plistlib
from pathlib import Path
from bokkio.xa11y_backend import Xa11yBackend
from bokkio.selector import flatten
from bokkio.desktop_control import InputMonitor,ControlState,EVENT_TAG
root=Path('/tmp/bokkio-native-live');root.mkdir(exist_ok=True)
os.environ['BOKKIO_CONTROL_DIR']=str(root/'control')
report={'kind':'macos_owned_fixture_development_build','checks':[], 'not_tested':['physical_hardware_input','IME','sleep_wake','installed_bundle_permissions','Windows','Microsoft Edge']}
PROJECT=Path(__file__).resolve().parents[3]
output=PROJECT/'docs/evidence/2026-10-18-native-integration/macos-live.json'
def save():output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
def record(name,passed,**details):report['checks'].append({'name':name,'passed':passed,**details});save()
app=root/'BokkioIntegration.app';contents=app/'Contents';(contents/'MacOS').mkdir(parents=True,exist_ok=True)
(contents/'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'local.bokkio.integration','CFBundleName':'BokkioIntegration','CFBundleExecutable':'BokkioIntegration','CFBundlePackageType':'APPL','NSPrincipalClass':'NSApplication'}))
subprocess.run(['xcrun','swiftc','-module-cache-path','/tmp/bokkio-swift-module-cache','-framework','Cocoa','fixtures/cocoa-runtime/main.swift','-o',str(contents/'MacOS/BokkioIntegration')],check=True,capture_output=True)
fixture=subprocess.Popen([str(contents/'MacOS/BokkioIntegration')],env={**os.environ,'BOKKIO_NATIVE_RESULT':str(root/'business.json')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
monitor=None
try:
    for _ in range(100):
        if (root/'business.json').exists():break
        time.sleep(.05)
    b=Xa11yBackend();s=b.snapshot(str(fixture.pid));record('complete_native_read',s['read']['complete'],node_count=len(list(flatten(s['windows']))),read=s['read'])
    partial=b.snapshot(str(fixture.pid),read_nodes=3);record('bounded_native_read',not partial['read']['complete'] and partial['read']['visited_nodes']<=3,read=partial['read'])
    field=next(n for n in flatten(s['windows']) if n['role']=='text_field' and n['name']=='Search')
    from bokkio.desktop_input import require_input_session
    try:
        require_input_session()
        r=b.perform(str(fixture.pid),'set_value',ref=field['ref'],value='Bokkio integration readback')
        time.sleep(.15);actual=json.loads((root/'business.json').read_text())['input']
        record('native_value_independent_fixture_readback',actual=='Bokkio integration readback',receipt=r.get('verification'))
    except Exception as error:
        record('native_value_independent_fixture_readback',False,error=type(error).__name__+': '+str(error))
    monitor=InputMonitor();status=monitor.start()
    for _ in range(200):
        status=monitor.state.status()
        if status.get('healthy'):break
        time.sleep(.05)
    report['monitor_status']={k:status.get(k) for k in ('state','healthy','error')};save()
    if status.get('healthy') and not status.get('error'):
        monitor.resume();time.sleep(.1)
        ag=c.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
        ag.CGEventCreateMouseEvent.argtypes=[c.c_void_p,c.c_uint32,c.c_double*2,c.c_uint32];ag.CGEventCreateMouseEvent.restype=c.c_void_p
        ag.CGEventSetIntegerValueField.argtypes=[c.c_void_p,c.c_uint32,c.c_int64];ag.CGEventPost.argtypes=[c.c_uint32,c.c_void_p]
        cf=c.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation');cf.CFRelease.argtypes=[c.c_void_p]
        def move(x,tag):
            event=ag.CGEventCreateMouseEvent(None,5,(c.c_double*2)(x,400),0)
            ag.CGEventSetIntegerValueField(event,42,tag);ag.CGEventPost(0,event);cf.CFRelease(event)
        generation=monitor.state.status()['generation'];move(350,EVENT_TAG);time.sleep(.15)
        record('tagged_own_event_not_paused',monitor.state.status()['generation']==generation)
        started=time.monotonic();move(380,0);move(410,0)
        for _ in range(100):
            if monitor.state.status()['state']=='paused_by_user':break
            time.sleep(.005)
        record('foreign_injected_event_pauses',monitor.state.status()['state']=='paused_by_user',post_to_state_ms=(time.monotonic()-started)*1000,source='CGEvent synthetic untagged; not physical input')
        time.sleep(.1);monitor.resume();time.sleep(.1)
        record('explicit_resume',monitor.state.status()['state']=='ready')
    else:record('native_monitor_available',False,reason=status.get('error') or status['state'])
except Exception as error:
    report['error']=type(error).__name__+': '+str(error);save()
finally:
    if monitor:monitor.disable()
    fixture.terminate();fixture.wait(timeout=5)
    save()
print(json.dumps(report,ensure_ascii=False))
