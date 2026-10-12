"""Actual autonomous business evaluations through Bokkio, with independent judges.

No business solution code is supplied to the tested callers. Raw outputs stay
private. This macOS runner does not claim customer or official benchmark scores.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs,urlparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evals.runtime_business import TASKS,FIRST,prepare,business_checks,snapshot_matches,sha,rtf_text,rendered_text_matches
from scripts.verify_harness_clients import glm_config,dsh_script
from bokkio.runtime import Runtime
from bokkio.sdk import Client
from bokkio.windows_capture import CaptureError

CATALOG=[{'id':'P01','name':'Axle','group':'Hardware','stock':'9'},{'id':'P02','name':'Bolt','group':'Hardware','stock':'3'},{'id':'P03','name':'Paper','group':'Office','stock':'2'},{'id':'P04','name':'Clamp','group':'Hardware','stock':'1'}]


def web_server(kind):
    state={'selected':None,'draft':None,'sent':False};lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            q=parse_qs(urlparse(self.path).query)
            if kind=='catalog':
                group=q.get('group',[''])[0];stock=q.get('stock',[''])[0]
                try:limit=int(stock)
                except ValueError:limit=1000
                selected=[r for r in CATALOG if (not group or r['group']==group) and int(r['stock'])<limit]
                if q:
                    with lock:state['selected']=[r['id'] for r in selected]
                rows=''.join('<tr>'+''.join('<td>'+html.escape(r[k])+'</td>' for k in ['id','name','group','stock'])+'</tr>' for r in selected)
                body=f'<h1>Inventory catalog</h1><form><label>Group <input name="group" value="{html.escape(group)}"></label><label>Stock below <input name="stock" value="{html.escape(stock)}"></label><button>Search</button></form><table><tr><th>id</th><th>name</th><th>group</th><th>stock</th></tr>{rows}</table>'
            else:
                draft=state['draft'];message='Saved draft' if draft else 'Quantity must be greater than zero'
                data=draft or {'name':'','project':'','quantity':'0','note':''}
                body='<h1>Internal draft form</h1><p>'+message+'</p><form method="POST">'+''.join(f'<label>{k}<input name="{k}" value="{html.escape(v)}"></label>' for k,v in data.items())+'<button>Save draft</button></form>'
            payload=('<!doctype html><meta charset="utf-8"><title>Bokkio disposable business</title>'+body).encode()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
        def do_POST(self):
            fields=parse_qs(self.rfile.read(int(self.headers.get('Content-Length','0'))).decode())
            data={k:fields.get(k,[''])[0] for k in ('name','project','quantity','note')}
            try:valid=int(data['quantity'])>0
            except ValueError:valid=False
            if kind=='draft' and valid:
                with lock:state['draft']=data
            self.send_response(303);self.send_header('Location','/');self.end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return server,state,f'http://127.0.0.1:{server.server_port}'


def preflight(case,folder,track='any-tool'):
    apps=[a['name'] for a in case['apps']]
    for app in case['apps']:
        if track=='gui' and app['name']!='Finder' and not app.get('gui_process_started'):
            old=ps_app(app['name']);subprocess.run(['open','-n','-a',app['name'],app['input'],'--args','-ApplePersistenceIgnoreState','YES'],capture_output=True,timeout=10)
            deadline=time.monotonic()+12
            while not ps_app(app['name'])-old and time.monotonic()<deadline:time.sleep(.1)
            new=ps_app(app['name'])-old
            if len(new)!=1:return {'ready':False,'reason':'dedicated_gui_process_unavailable','windows_verified':[]}
            app['pid']=next(iter(new));app['gui_owned_process']=True
        elif not app.get('gui_process_started'):
            subprocess.run(['open','-a',app['name'],app['input']],capture_output=True,timeout=10)
    if not apps:return {'ready':True,'windows_verified':[]}
    # A name may resolve to older instances before the new owned process has
    # registered with NSWorkspace. Bind its PID so open retries registration.
    selectors=[str(a['pid']) if a.get('gui_owned_process') else a['name'] for a in case['apps']]
    runtime=Runtime(folder/'preflight-state',{'apps':selectors,'write':False})
    client=Client(runtime);deadline=time.monotonic()+15
    while True:
        try:client.open();break
        except RuntimeError:
            if time.monotonic()>=deadline:return {'ready':False,'windows_verified':[],'reason':'application_registry_startup_timeout'}
            time.sleep(.2)
    confirmed=[];errors={}
    try:
        while time.monotonic()<deadline:
            confirmed=[]
            for app in case['apps']:
                for pid in ([app['pid']] if app.get('gui_owned_process') else sorted(ps_app(app['name']))):
                    obs=client.call('desktop.observe',{'app':str(pid),'window':app['windows'][0],'max_nodes':500})
                    if obs['status']=='completed' and any(n['role']=='window' and n.get('name')==app['windows'][0] for n in obs['result']['nodes']):
                        app['pid']=pid;confirmed.append(app['name']);break
                    error=obs.get('error',{})
                    errors[app['name']]=error if isinstance(error,str) else error.get('message',obs['status'])
            if len(confirmed)==len(apps):break
            time.sleep(.2)
    finally:client.call('session.close')
    return {'ready':len(confirmed)==len(apps),'windows_verified':confirmed,'last_errors':{k:v for k,v in errors.items() if k not in confirmed}}


def prompt(case,url,track):
    resources=[{'app':a['name'],'app_selector':str(a['pid']),'initial_and_output_windows':a['windows'],'scope':'dedicated_owned_process_including_menus_and_dialogs' if a.get('gui_owned_process') else 'exact_listed_windows'} for a in case['apps']]
    paths={'inputs':case['inputs'],'outputs':case['out']}
    return f'''This is an authorized disposable business task. Use ONLY Bokkio tools to perform it. Do not use external shell/file/browser/CUA tools to do business work. Your client may offer tool schema discovery; that is permitted.
Goal: {case['goal']}
Resources: {json.dumps(resources,ensure_ascii=False)}
Workspace: {case['work']}; paths: {json.dumps(paths)}
Web page: {url or 'not used'}
Track: {track}. {'Native GUI and screenshot/pixel only. No generated code, processes, Browser DOM or business file reads. Independent judge reads output files.' if track=='gui' else 'You may choose native, visual, Browser and generated code/scripts through Bokkio. Generated code must run through code.run/process.run, not external shell. Python jobs may use the public Client.from_environment() delegated SDK. No solution script is supplied.'}
The local administrator pre-granted only these disposable resources; approval is not required in this business batch. This is not a human approval test. Do not access unrelated documents/accounts/configuration, credentials or evaluator files. Do not overwrite input files. Only operate authorized resources. Dedicated GUI processes contain only owned documents and permit their menus/dialogs; other apps remain restricted to listed windows. Do not close or kill applications with unrelated documents. Leave displayed output windows and session available to the independent judge.
Use capabilities and session.open with task_id="business-{case['task']}-{case['client']}" and the administrator defaults (no additional apps/paths/origins required). For native calls use the numeric app_selector in Resources; app names may have multiple running processes. MCP envelope: business fields inside arguments; session_id and operation_id are top-level siblings. Subsequent calls need the opened session_id. Get fresh observations and actual refs; never invent refs. Native observations expire after 15 seconds. For an explicitly zero-dispatch stale failure you may re-observe with a new operation ID at most twice; never repeat completion_unknown. Poll generated jobs to completion. Finish with a concise final JSON status and output paths; the independent judge, not your statement, determines success.
General interface notes: job.get's envelope status is separate from result.status; terminal output is in result.result.stdout/stderr. Use artifact_id from the returned artifact descriptor, never a filesystem path as an artifact ID. The Python delegated SDK exposes Client.from_environment(), call(tool, arguments, operation_id=None), and wait_job(job_id, timeout=60). desktop.observe is read-only and does not require activating the application. Screenshot dimensions describe a window capture, not a document's intrinsic image dimensions. Read the authorized inputs before deriving facts; do not substitute remembered values. Operate using existing OS permissions; new system permission grants are outside this disposable task. End once the requested business evidence is verified; repeated optional probes consume the same budget.
'''


def command_for(client,args,folder,policy,case,model):
    env=os.environ.copy();python=Path(sys.executable).absolute()
    if client=='codex-current':return None,env
    if client=='deepseek':
        env['BOKKIO_GLM_KEY']=model['api_key']
        cmd=dsh_script(folder,args.dsh_python,python,policy,folder/'state',Path(case['work']))
        f=folder/'run_dsh.py';f.write_text(f.read_text().replace('request_timeout_seconds=240',f'request_timeout_seconds={case["budget"]}'))
        return cmd,env
    # A shared private profile avoids rebuilding dependencies per case. Every
    # invocation is a fresh oneshot conversation, with no prior chat loaded.
    home=(args.hermes_runtime or args.output/'hermes-runtime')/'profiles'/'acceptance';home.mkdir(parents=True,exist_ok=True,mode=0o700)
    config={'model':{k:v for k,v in model.items() if k!='api_key'},'toolsets':['bokkio'],'agent':{'max_turns':40,'api_max_retries':1},'mcp_servers':{'bokkio':{'command':str(python),'args':['-m','bokkio.runtime_cli','--state',str(folder/'state'),'--policy',str(policy),'serve'],'enabled':True}},'checkpoints':{'enabled':False}}
    path=home/'config.yaml';path.write_text(json.dumps(config));path.chmod(0o600)
    env.update(HERMES_HOME=str(home),OPENROUTER_API_KEY=model['api_key'])
    return [str(args.hermes),'chat','--query-file',str(folder/'prompt.txt'),'--oneshot','--ignore-rules','-t','bokkio','--max-turns','40','--run-budget',str(case['budget']),'--format','stream-json','--reasoning','low'],env


def budget_stop(folder,runtime):
    with runtime.store.connect() as db:
        writes=sum(json.loads(row[0]).get('tool') in {'desktop.act','desktop.pixel','desktop.activate','browser.act','browser.open','code.run','process.run'} for row in db.execute("SELECT data FROM events WHERE kind='request.received'"))
    if writes>60:return 'core_dispatch_budget'
    sessions=folder/'dsh-home'/'sessions'
    steps=0
    if sessions.exists():
        for log in sessions.rglob('*.jsonl'):
            for line in log.read_text().splitlines():
                try:r=json.loads(line)
                except ValueError:continue
                steps+=r.get('type')=='step/start'
    return 'model_turn_budget' if steps>40 else None


def supervise(cmd,env,folder,runtime,budget):
    started=time.monotonic();process=None;reason=None
    if cmd is not None:
        out=(folder/'client.stdout').open('w');err=(folder/'client.stderr').open('w')
        process=subprocess.Popen(cmd,env=env,cwd=folder/'workspace',stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
        (folder/'client-process.json').write_text(json.dumps({'pid':process.pid}))
    while time.monotonic()-started<budget:
        reason=budget_stop(folder,runtime)
        if reason:break
        if process and process.poll() is not None:break
        if not process and (folder/'complete.json').exists():break
        time.sleep(.1)
    else:reason='wall_clock_budget'
    if reason and process and process.poll() is None:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
    code=(process.wait() if process else 0 if (folder/'complete.json').exists() else 124)
    # A fast final turn can end between the last poll and exit. Score its
    # final counters too; caller completion must not hide a budget overrun.
    reason=reason or budget_stop(folder,runtime)
    if process:out.close();err.close()
    return code,reason,round(time.monotonic()-started,3)


def target_matches(target,nodes,pid,folder=None):
    if Path(target['file']).suffix!='.rtf':
        return snapshot_matches(target,nodes),{'channel':'native'}
    file=Path(target['file']);title=file.stem
    if not any(n['role']=='window' and n.get('name')==title for n in nodes):
        return False,{'channel':'local_ocr','reason':'owned_window_unavailable'}
    from bokkio.macos_capture import capture_window
    meta,png=capture_window(int(pid),title=title,ocr=True)
    text='\n'.join(r['text'] for r in meta['ocr']['observations'])
    bound=meta['pid']==int(pid) and meta['window_title']==title
    correct=bound and rendered_text_matches(rtf_text(file),text)
    if folder:
        folder.mkdir(exist_ok=True)
        (folder/'owned-window.png').write_bytes(png)
        (folder/'capture.json').write_text(json.dumps(meta))
    return correct,{'channel':'local_ocr','capture_scope_verified':bound,'image_sha256':meta['image_sha256'],'ocr_engine':meta['ocr']['engine']}


def judge_ui(case,runtime,sid):
    results=[]
    for target in case['ui_outputs']:
        file=Path(target['file']);title=file.stem if target['app'] in {'Numbers','Pages'} else file.name
        selector=str(next(a['pid'] for a in case['apps'] if a['name']==target['app']))
        response=runtime.call('desktop.observe',{'app':selector,'window':title,'max_nodes':2000,'max_bytes':1000000},session_id=sid,operation_id='independent-judge-'+target['app']+'-'+file.name)
        facts={}
        try:
            valid=False
            if response['status']=='completed':valid,facts=target_matches(target,response['result']['nodes'],selector,runtime.store.root.parent/('judge-'+target['app']))
        except (OSError,ValueError,RuntimeError,CaptureError,subprocess.SubprocessError) as e:valid=False;facts={'judge_error_type':type(e).__name__}
        results.append({'app':target['app'],'kind':target['kind'],'correct':valid,'observation_status':response['status'],**facts})
    if not case['ui_outputs'] and case['apps']:
        for app in case['apps']:
            with runtime.store.connect() as db:
                observations=db.execute('SELECT payload FROM observations WHERE session_id=?',(sid,)).fetchall()
            observed=source_window_observed([json.loads(r[0]) for r in observations],app['name'],app['windows'][0])
            results.append({'app':app['name'],'kind':'source_observed','correct':observed})
    if case.get('web_kind') and case.get('track')=='gui':
        app=next(a for a in case['apps'] if a.get('gui_browser'))
        response=runtime.call('desktop.observe',{'app':str(app['pid']),'window':app['windows'][0],'max_nodes':2000},session_id=sid,operation_id='independent-judge-gui-browser')
        pool='\n'.join(str(n.get('name') or '')+' '+str(n.get('value') or '') for n in response.get('result',{}).get('nodes',[]))
        valid=response['status']=='completed' and all(v in pool for v in ['P02','P04']) and all(v not in pool for v in ['P01','P03'])
        results.append({'app':'owned_gui_browser','kind':'business_page','correct':valid,'observation_status':response['status']})
    elif case.get('web_kind'):
        response=runtime.call('browser.observe',session_id=sid,operation_id='independent-judge-browser')
        text=response.get('result',{}).get('text','')
        if case['task']=='T07':valid=response['status']=='completed' and 'P02' in text and 'P04' in text and 'P01' not in text and 'P03' not in text
        else:
            pool=text+json.dumps(response.get('result',{}).get('fields',[]),ensure_ascii=False)
            valid=response['status']=='completed' and all(v in pool for v in ['Saved draft','林安','Beacon','内部测试草稿'])
        with runtime.store.connect() as db:
            used=db.execute("SELECT count(*) FROM operations WHERE tool='browser.act' AND status IN ('executed','verified','completed')").fetchone()[0]
        results.append({'app':'isolated_browser','kind':'business_page','correct':valid and used>0,'observation_status':response['status']})
    return results


def source_window_observed(observations,app,window):
    # Captures and native snapshots share the observation store. A screenshot
    # has no native snapshot; it is not this source-inspection evidence.
    return any(p.get('window')==window and p.get('snapshot',{}).get('app',{}).get('name')==app
               for p in observations)


def ps_app(name):
    rows=subprocess.check_output(['ps','-axo','pid=,comm='],text=True).splitlines();suffix='/Contents/MacOS/'+name
    return {int(line.strip().split(None,1)[0]) for line in rows if line.strip().split(None,1)[-1].endswith(suffix)}


def reopen_check(case,folder):
    if not case['requires_reopen']:return {'required':False,'correct':None}
    target=case['ui_outputs'][0];app=target['app'];old=ps_app(app);born=None;passed=False;reason=None;owned=False;stamp=None
    try:
        subprocess.run(['open','-n','-a',app,target['file'],'--args','-ApplePersistenceIgnoreState','YES'],capture_output=True,timeout=10)
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            fresh=ps_app(app)-old
            if len(fresh)==1:
                pid=next(iter(fresh));born=pid
                from bokkio.runtime import process_birth
                stamp=process_birth(pid)
                c=Client(Runtime(folder/'reopen-state',{'apps':[str(pid)],'write':False}))
                try:c.open()
                except RuntimeError:
                    time.sleep(.2);continue
                title=Path(target['file']).stem if app=='Pages' else Path(target['file']).name
                observed=c.call('desktop.observe',{'app':str(pid),'window':title,'max_nodes':2000,'max_bytes':1000000})
                c.call('session.close')
                if observed['status']=='completed':
                    owned=True
                    passed,verification=target_matches(target,observed['result']['nodes'],pid,folder/'reopen-visual');break
            time.sleep(.2)
        if not born:reason='application_did_not_create_fresh_process'
    except Exception as e:reason=type(e).__name__
    finally:
        if born and born not in old and owned:
            try:
                from bokkio.runtime import process_birth
                if process_birth(born)==stamp:
                    probe=Client(Runtime(folder/'cleanup-state',{'apps':[str(born)],'write':False}));probe.open()
                    read=probe.call('desktop.observe',{'app':str(born),'max_nodes':100});probe.call('session.close')
                    windows=[n for n in read.get('result',{}).get('nodes',[]) if n['role']=='window']
                    if len(windows)==1 and windows[0].get('name')==title:os.kill(born,signal.SIGTERM)
            except (ValueError,ProcessLookupError):pass
    return {'required':True,'correct':passed,'new_process_verified':bool(born),'reason':reason,'original_process_terminated':False}


def protocol_complete(code,stop,sessions,open_sessions,jobs,unknown):
    # Recovered terminal failures are attempts, not unfinished work. Unknown
    # dispatches still fail the contract even if the final output is correct.
    return (code==0 and not stop and bool(sessions) and bool(open_sessions)
            and all(j in {'completed','failed','cancelled','timed_out'} for j in jobs)
            and unknown==0)


def caller_finished(folder,client):
    if client=='codex-current':
        file=folder/'complete.json'
        if not file.exists():return False,'missing_completion_signal'
        status=json.loads(file.read_text()).get('status')
        return status=='completed',status
    if client!='deepseek':return True,None
    file=folder/'dsh-result.json'
    if not file.exists():return False,'missing_sdk_result'
    data=json.loads(file.read_text());reason=data.get('finish_reason')
    return reason=='completed' and bool(data.get('final')),reason


def gui_browser(case,folder,url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:executable=p.chromium.executable_path
    name='Google Chrome for Testing'
    process=subprocess.Popen([executable,'--user-data-dir='+str(folder/'gui-browser-profile'),'--app='+url,'--force-renderer-accessibility','--disable-background-networking','--no-first-run','--no-default-browser-check'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    case['apps'].append({'name':name,'pid':process.pid,'input':url,'windows':['Bokkio disposable business'],'gui_browser':True,'gui_owned_process':True,'gui_process_started':True})
    blank=folder/'gui-blank.txt';blank.write_text('')
    case['apps'].append({'name':'TextEdit','input':str(blank),'windows':[blank.name,case['prefix']+'-result.csv']})
    case['ui_outputs'].append({'app':'TextEdit','file':str(Path(case['out'])/(case['prefix']+'-result.csv')),'kind':'csv_text'})
    return process


def evaluate_one(args,task,client,model):
    folder=args.output/(task+'-'+client);folder.mkdir(mode=0o700)
    case=prepare(folder/'workspace',task,client,args.variant);case['budget']=480 if task in {'T09','T10'} else args.budget
    case['track']=args.track
    server=None;web=None;url=None
    if case.get('web_kind'):server,web,url=web_server(case['web_kind'])
    browser_process=gui_browser(case,folder,url) if case.get('web_kind') and args.track=='gui' else None
    pf=preflight(case,folder,args.track)
    policy={'apps':[str(a['pid']) for a in case['apps'] if 'pid' in a],'windows':{str(a['pid']):a['windows'] for a in case['apps'] if 'pid' in a and not a.get('gui_owned_process')},'paths':[case['work']] if args.track=='any-tool' else [],'origins':[url] if url and args.track=='any-tool' else [],'write':True,'trusted_host':args.track=='any-tool','require_approval':False}
    runtime=Runtime(folder/'state',policy)
    policy_path=folder/'policy.json';policy_path.write_text(json.dumps(policy));(folder/'case.json').write_text(json.dumps(case))
    if not pf['ready']:
        if server:server.shutdown();server.server_close()
        if browser_process:browser_process.terminate();browser_process.wait(timeout=5)
        return {'task':task,'client':client,'status':'blocked','started':False,'passed':False,'preflight':pf,'reason':'owned_application_window_unavailable'}
    (folder/'prompt.txt').write_text(prompt(case,url,args.track))
    cmd,env=command_for(client,args,folder,policy_path,case,model)
    (folder/'ready.json').write_text(json.dumps({'folder':str(folder),'case':case,'url':url,'track':args.track}))
    print(json.dumps({'event':'ready','task':task,'client':client,'folder':str(folder) if client=='codex-current' else None}),flush=True)
    try:
        code,stop,elapsed=supervise(cmd,env,folder,runtime,case['budget'])
        with runtime.store.connect() as db:
            sessions=[r[0] for r in db.execute('SELECT id FROM sessions')]
            open_sessions=[r[0] for r in db.execute("SELECT id FROM sessions WHERE status='open'")]
            jobs=[r[0] for r in db.execute('SELECT status FROM jobs')] if db.execute("SELECT 1 FROM sqlite_master WHERE name='jobs'").fetchone() else []
            tools=[r[0] for r in db.execute('SELECT DISTINCT tool FROM operations')]
            unknown=db.execute("SELECT count(*) FROM operations WHERE status='completion_unknown'").fetchone()[0]
        checks=business_checks(case,web);ui=judge_ui(case,runtime,open_sessions[-1]) if open_sessions else []
        protocol=protocol_complete(code,stop,sessions,open_sessions,jobs,unknown)
        finished,finish_reason=caller_finished(folder,client);protocol=protocol and finished
        for sid in open_sessions:runtime.call('session.close',session_id=sid)
        persistence=reopen_check(case,folder) if checks['outputs_exist'] and ui and all(v['correct'] for v in ui) else {'required':case['requires_reopen'],'correct':False if case['requires_reopen'] else None,'reason':'business_ui_not_ready'}
        passed=checks['business_correct'] and checks['source_unchanged'] and bool(ui) and all(v['correct'] for v in ui) and protocol and (not persistence['required'] or persistence['correct'])
        result={'task':task,'client':client,'track':args.track,'variant':args.variant,'status':'passed' if passed else 'failed','started':bool(sessions),'passed':bool(passed),'client_exit_code':code,'termination':stop,'duration_seconds':elapsed,'business_checks':checks,'ui_checks':ui,'persistence':persistence,'protocol_completed':protocol,'tools':sorted(tools),'preflight':pf,'approval_mode':'administrator_pregranted_disposable_resources','conversation_context':'retained_and_evaluator_author' if client=='codex-current' else 'fresh_oneshot','model':'current_conversation' if client=='codex-current' else 'z-ai/glm-5.3-flash','raw_traces_public':False}
        result.update(job_statuses=jobs,unknown_operations=unknown,caller_finish_reason=finish_reason)
        with runtime.store.connect() as db:
            result['audit_events']=db.execute('SELECT count(*) FROM events').fetchone()[0]
            result['logical_operations']=db.execute('SELECT count(*) FROM operations').fetchone()[0]
            result['generated_code_parent_links']=sum(bool(json.loads(r[0]).get('parent_operation')) for r in db.execute("SELECT data FROM events WHERE kind='request.received'"))
        result['output_sha256']={str(f.relative_to(case['out'])):sha(f) for f in Path(case['out']).rglob('*') if f.is_file()}
        (folder/'judge.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        return result
    finally:
        with runtime.store.connect() as db:remaining=[r[0] for r in db.execute("SELECT id FROM sessions WHERE status='open'")]
        for sid in remaining:runtime.call('session.close',session_id=sid)
        if server:server.shutdown();server.server_close()
        if browser_process and browser_process.poll() is None:browser_process.terminate();browser_process.wait(timeout=5)


def main(args):
    args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    model=glm_config(args.hermes_python,args.hermes_home)
    selected=[(t,c) for c in args.clients for t in args.tasks]
    files=[Path(__file__).relative_to(Path.cwd()),Path('evals/runtime_business.py'),Path('scripts/verify_harness_clients.py')]+[p for p in sorted(Path('src/bokkio').rglob('*')) if p.is_file() and p.suffix in {'.py','.swift'}]
    sources={str(p):sha(p) for p in files}
    report={'scope':'autonomous_synthetic_business_any_tool_internal_eval_not_official_benchmark','base_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_sha256':sources,'track':args.track,'planned':len(selected),'results':[],'limits':['current_Codex_retained_context_and_authored_evaluator_not_blind','trusted_host_not_OS_sandbox','customer_and_Windows_not_tested']}
    (args.output/'frozen-run.json').write_text(json.dumps({'tasks':args.tasks,'clients':args.clients,'variant':args.variant,'sources':sources,'budgets':{'short':args.budget,'long':480},'suite_catalog_sha256':sha('fixtures/runtime-business-eval/suite.json')},indent=2))
    for task,client in selected:
        try:result=evaluate_one(args,task,client,model)
        except Exception as e:result={'task':task,'client':client,'status':'runner_error','passed':False,'started':None,'error_type':type(e).__name__}
        report['results'].append(result);report['passed']=sum(bool(r['passed']) for r in report['results']);report['started']=sum(r.get('started') is True for r in report['results'])
        report['not_run']=report['planned']-len(report['results'])
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(json.dumps({'event':'judged',**result},ensure_ascii=False),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--clients',nargs='+',choices=['codex-current','hermes','deepseek'],default=['codex-current','hermes','deepseek'])
    p.add_argument('--tasks',nargs='+',choices=[t[0] for t in TASKS],default=FIRST);p.add_argument('--track',choices=['any-tool','gui'],default='any-tool');p.add_argument('--variant',type=int,default=0);p.add_argument('--budget',type=int,default=240)
    p.add_argument('--hermes',type=Path,default=Path.home()/'.local/bin/hermes');p.add_argument('--hermes-python',type=Path,default=Path.home()/'.hermes/hermes-agent/venv/bin/python');p.add_argument('--hermes-home',type=Path,default=Path.home()/'.hermes');p.add_argument('--dsh-python',type=Path,default=Path('/tmp/bokkio-harness-20261012/dsh-venv/bin/python'))
    p.add_argument('--hermes-runtime',type=Path,help='Private prepared runtime data root; every task still starts a fresh conversation')
    p.add_argument('--pregranted-disposable-only',action='store_true')
    a=p.parse_args()
    if sys.platform!='darwin':p.error('This runner binds macOS applications; Windows business bindings are not implemented')
    if not a.pregranted_disposable_only:p.error('Explicit --pregranted-disposable-only required; not customer human approval')
    r=main(a);raise SystemExit(0 if len(r['results'])==r['planned'] and all(x['passed'] for x in r['results']) else 1)
