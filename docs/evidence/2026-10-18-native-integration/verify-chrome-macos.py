import json,subprocess,time,os,signal
from pathlib import Path
from bokkio.xa11y_backend import Xa11yBackend
from bokkio.web_view import select_web
from bokkio.selector import flatten
output=Path('docs/evidence/2026-10-18-native-integration/chrome-macos-live.json')
page=Path('fixtures/native-web/index.html').resolve().as_uri()
process=subprocess.Popen(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','--user-data-dir=/tmp/bokkio-native-web-profile','--no-first-run','--no-default-browser-check','--force-renderer-accessibility',page],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
r={'kind':'macos_chrome_owned_local_page','forced_accessibility':True,'required':['BK-2718','Blue pen','37','Red pen','19','REF-2026','Send order','Tuesday at 10:30.','aisle 4'],'screenshots':False,'dom_injection':False}
try:
    b=Xa11yBackend();time.sleep(2)
    s=b.snapshot(str(process.pid),'Bokkio Native Web Fixture');nodes,meta=select_web(s)
    texts=' '.join(str(n.get(k) or '') for n in nodes for k in ('name','value'))
    r.update(node_roles=sorted(set(n['role'] for n in nodes)),view=meta,read=s['read'],native_nodes=len(list(flatten(s['windows']))),web_nodes=len(nodes),checks={text:text in texts for text in r['required']},native_bytes=len(json.dumps([{k:v for k,v in n.items() if k!='children'} for n in flatten(s['windows'])]).encode()),web_bytes=len(json.dumps([{k:v for k,v in n.items() if k!='children'} for n in nodes]).encode()))
    from bokkio.runtime import Runtime
    from bokkio.sdk import Client
    import tempfile
    client=Client(Runtime(Path(tempfile.mkdtemp(prefix='bokkio-web-core-')),{'apps':[str(process.pid)],'write':False},b))
    client.open()
    exact_title=next(n['name'] for n in s['windows'] if n['role']=='window')
    r['core_window_title']=exact_title
    observed=client.call('desktop.observe',{'app':str(process.pid),'window':exact_title,'view':'web','max_nodes':2000,'max_bytes':2000000})
    r['core_status']=observed['status']
    if observed['status']=='completed':
        result=observed['result'];text=' '.join(str(n.get(k) or '') for n in result['nodes'] for k in ('name','value'))
        r['core_checks']={required:required in text for required in r['required']}
        r['core_truncated']=result['truncated'];r['core_returned_bytes']=result['returned_bytes']
    else:r['core_error']=observed.get('error')
    client.call('session.close')
except Exception as error:r['error']=type(error).__name__+': '+str(error)
finally:
    os.killpg(process.pid,signal.SIGTERM)
    process.wait(timeout=10)
    output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(r,ensure_ascii=False))
