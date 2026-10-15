"""Desktop IPC service. Electron owns desktop windows, global controls and credential storage."""
from __future__ import annotations
import argparse,json,os,secrets,subprocess,sys,threading,time,urllib.request,signal
from pathlib import Path
from .workflow_studio import Studio,create_server
from .workflow import save_json,selector_for
from .app_launch import installed_running_apps
from .runtime import Runtime
from .local_runtime import LocalRuntime
from .sdk import Client
from .audit import identifier
from .execution_log import ARCHITECTURE,ingest_choice,chat_trace,workflow_trace

class DesktopStudio(Studio):
    local_direct=True
    def __init__(self,state):
        super().__init__(state)
        self.config_path=self.state/'desktop-settings.json'
        self.settings={'provider':'openai-compatible','base_url':'https://openrouter.ai/api/v1','model':'z-ai/glm-5.3-flash','harness_python':os.environ.get('BOKKIO_HARNESS_PYTHON',sys.executable),'workspace':str(Path.home()/'Bokkio Workspace')}
        if self.config_path.exists():self.settings.update({k:v for k,v in json.loads(self.config_path.read_text()).items() if k in self.settings})
        self.api_key='';self.chats={};self.chat_processes={};self.chat_log_lock=threading.RLock()
        for path in (self.state/'workflow-drafts').glob('*.json'):
            value=json.loads(path.read_text())
            if value.get('status') in {'recording','paused'}:value.update(status='interrupted',error='操作录制中断，已保留捕获的步骤');save_json(path,value)
        for path in (self.state/'chats').glob('*.json'):
            value=json.loads(path.read_text())
            if value.get('status')=='running':value.update(status='interrupted',error='应用退出，任务已中断');save_json(path,value)
            self.chats[value['id']]=value
        for path in (self.state/'workflow-runs').glob('*.json'):
            value=json.loads(path.read_text())
            if value.get('status')=='running':value.update(status='paused',pause_reason='app_restarted');save_json(path,value)
        self.inspector=None
    def apps(self):
        owner=int(os.environ.get('BOKKIO_DESKTOP_PID','0'));return [a for a in super().apps() if a['pid']!=owner]
    def inspection_client(self):
        if self.inspector is None:
            self.inspector=Client(LocalRuntime(self.state));self.inspector.open(task_id='desktop-inspector')
        return self.inspector
    def save_workflow(self,document,expected_sha=None):
        value=self.library.save(document,expected_sha);(self.state/'workflow-drafts'/(value['id']+'.json')).unlink(missing_ok=True);return value
    def run_view(self,rid):
        value=super().run_view(rid);value['trace']=workflow_trace(value,self.state);return value
    def chat_view(self,value):
        with self.chat_log_lock:
            snapshot={**value,'events':list(value.get('events',[]))}
            if 'choices' in value:snapshot['choices']={k:dict(v) for k,v in value['choices'].items()}
        return {**snapshot,'trace':chat_trace(snapshot,self.state)}
    def start_run(self,wid,mode,pregranted=True,**controls):
        with self.lock:
            if self.busy() or self.record and self.record.state in {'recording','paused'} or any(p.poll() is None for p in self.chat_processes.values()):raise ValueError('Finish the current recording or task first')
            from .runtime_workflow import RuntimeWorkflowRunner
            doc=self.library.get(wid);runtime=LocalRuntime(self.state);runtime.policy['launch_apps']=doc['apps'];client=Client(runtime);client.open(apps=[],task_id='workflow-'+identifier())
            runner=RuntimeWorkflowRunner(client,self.state/'workflow-runs');run=runner.start(doc,mode,**controls);rid=run['id'];self.runners[rid]=runner;save_json(self.state/'workflow-run-policies'/(rid+'.json'),runtime.policy);self.spawn(rid);return {'id':rid,'status':'running'}
    def runner(self,rid):
        if rid not in self.runners:
            from .runtime_workflow import RuntimeWorkflowRunner
            r=json.loads((self.state/'workflow-runs'/(rid+'.json')).read_text());runtime=LocalRuntime(self.state);runtime.policy['launch_apps']=r['workflow']['apps'];self.runners[rid]=RuntimeWorkflowRunner(Client(runtime,r['session_id']),self.state/'workflow-runs')
        return self.runners[rid]
    def recorder_start(self,pids,name):
        if any(p.poll() is None for p in self.chat_processes.values()):raise ValueError('Stop the current task before recording')
        return super().recorder_start(pids,name)
    def route(self,method,path,data):
        def arg(key,default=None):return data.get(key,[default])[0] if method=='GET' else data.get(key,default)
        if path=='/api/drafts':return [{'id':v['document']['id'],'name':v['document']['name'],'steps':len(v['document']['steps'])} for v in [json.loads(p.read_text()) for p in (self.state/'workflow-drafts').glob('*.json')]]
        if path=='/api/draft':
            wid=arg('id')
            if not __import__('re').fullmatch('[a-f0-9]{32}',wid):raise ValueError('Invalid draft ID')
            return json.loads((self.state/'workflow-drafts'/(wid+'.json')).read_text())
        if path=='/api/archived':return self.library.archived()
        if path=='/api/workflows/restore':return self.library.restore(arg('id'),arg('expected_sha256'))
        if path=='/api/architecture':return ARCHITECTURE
        if path=='/api/status':
            return {'platform':sys.platform,'local_direct':True,'runtime_python':sys.executable,'state':str(self.state),'recording':self.record.state if self.record else 'idle','busy':self.busy(),'chat_busy':any(p.poll() is None for p in self.chat_processes.values())}
        if path=='/api/settings':
            if method=='POST':
                unknown=set(data)-set(self.settings)-{'api_key'}
                if unknown:raise ValueError('Unknown settings: '+','.join(unknown))
                self.settings.update({k:v for k,v in data.items() if k!='api_key'})
                if 'api_key' in data:self.api_key=data['api_key']
                save_json(self.config_path,self.settings)
            return {**self.settings,'has_api_key':bool(self.api_key)}
        if path=='/api/provider/test':
            request=urllib.request.Request(self.settings['base_url'].rstrip('/')+'/chat/completions',json.dumps({'model':self.settings['model'],'messages':[{'role':'user','content':'Respond with OK.'}],'max_tokens':32}).encode(),{'Content-Type':'application/json','Authorization':'Bearer '+self.api_key})
            with urllib.request.urlopen(request,timeout=30) as response:result=json.load(response)
            return {'status':'connected','model':result.get('model',self.settings['model'])}
        if path=='/api/windows':
            return self.inspection_client().call('desktop.windows',{'app':str(arg('pid'))})['result']
        if path=='/api/capture':
            client=self.inspection_client();r=client.call('desktop.capture',{'app':str(arg('pid')),'window':arg('window')})
            if r['status']!='completed':raise ValueError(r)
            a=client.call('artifact.read',{'artifact_id':r['result']['artifact']['artifact_id'],'max_bytes':10000000})
            if a['status']!='completed':raise ValueError(a)
            return {'png':a['result']['data_base64'],'metadata':r['result']['metadata']}
        if path=='/api/inspect':
            from .runtime_workflow import runtime_snapshot
            observed,snapshot=runtime_snapshot(self.inspection_client(),int(arg('pid')),arg('window'))
            from .runtime_workflow import window_identity
            roots=[n for n in snapshot['windows'] if n['role'] in {'window','dialog'} and n['name']==arg('window')]
            context={}
            if len(roots)==1:
                n=roots[0];native=n.get('platform_data',{});identity=window_identity(n);context={k:v for k,v in {'key':identity,'identity':identity,'role':n['role'],'class_name':native.get('class_name'),'subrole':native.get('ax_subrole')}.items() if v}
            return [{'window_context':context,'target':{**selector_for(snapshot,n),**({'identifier':n['platform_data'].get('ax_identifier') or n['platform_data'].get('automation_id')} if n.get('platform_data',{}).get('ax_identifier') or n.get('platform_data',{}).get('automation_id') else {})},'actions':n['actions'],'bounds':n.get('bounds'),'value':n.get('value'),'state':n.get('state')} for n in snapshot['windows'] if not n.get('platform_data',{}).get('is_password') and n.get('platform_data',{}).get('ax_subrole')!='AXSecureTextField']
        if path=='/api/run/repair':
            runner=self.runner(arg('id'));doc=self.library.get(arg('workflow_id'));runtime=runner.client.runtime
            runtime.policy['launch_apps']=doc['apps']
            with runtime.store.connect() as db:
                scope=runtime._session(runner.client.session_id);scope['launch_apps']=doc['apps'];db.execute('UPDATE sessions SET policy=? WHERE id=?',(json.dumps(scope),runner.client.session_id))
            return runner.repair(arg('id'),doc,arg('parameters',{}))
        if path=='/api/run/control':
            runner=self.runner(arg('id'));r=runner.load(arg('id'))
            if r['status']!='paused':raise ValueError('Pause the workflow before changing execution controls')
            r['single']=bool(arg('single',False));runner._save(r);return {'status':'updated'}
        if path=='/api/emergency-stop':
            if self.record and self.record.state in {'recording','paused'}:self.record.stop()
            for rid,t in self.threads.items():
                if t.is_alive():self.runner(rid).cancel(rid)
            from .audit import AuditStore
            from .runtime import close_session
            store=AuditStore(self.state);known=set(self.chats)|set(self.chat_processes);cancelling={cid for cid,job in self.chats.items() if job.get('status') in {'running','cancelling'}}
            for cid in cancelling:
                self.chats[cid].update(status='cancelling',error=None);save_json(self.state/'chats'/(cid+'.json'),self.chats[cid])
            folder=self.state/'task-cancellations';folder.mkdir(exist_ok=True)
            for cid in known:(folder/cid).touch()
            with store.connect() as db:sessions=[row['id'] for row in db.execute('SELECT id,policy FROM sessions') if json.loads(row['policy']).get('task_id') in known]
            for sid in sessions:close_session(store,sid)
            def active_jobs():
                with store.connect() as db:
                    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'").fetchone():return []
                    return [dict(row) for row in db.execute("SELECT id,session_id,status FROM jobs WHERE status IN ('queued','running')") if row['session_id'] in sessions]
            from .executor import get
            for job in active_jobs():get(store,job['id'],job['session_id'])
            # Give the owning workers time to kill code children and durably
            # finalize cancellation before tearing down the SDK process tree.
            deadline=time.monotonic()+5
            while active_jobs() and time.monotonic()<deadline:time.sleep(.05)
            outstanding=active_jobs()
            for cid,p in self.chat_processes.items():
                if p.poll() is None:
                    if os.name=='nt':subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    else:
                        from .executor import _terminate_pid
                        _terminate_pid(p.pid)
            for cid in cancelling:
                self.chats[cid].update(status='cancelled',error=None);save_json(self.state/'chats'/(cid+'.json'),self.chats[cid])
            if outstanding:raise RuntimeError('Agent stopped, but code-job cancellation has no final receipt; inspect the run before retrying')
            return {'status':'stopped'}
        if path=='/api/chat/start':
            if self.busy() or self.record and self.record.state in {'recording','paused'} or any(p.poll() is None for p in self.chat_processes.values()):raise ValueError('Finish the current recording, workflow or task first')
            prompt=arg('prompt','').strip()
            if not prompt:raise ValueError('Enter a task')
            if not self.api_key:raise ValueError('Configure your provider API key in Settings')
            cid=identifier();folder=self.state/'chats'/cid;folder.mkdir(parents=True,exist_ok=True,mode=0o700)
            workspace=Path(self.settings['workspace']).expanduser();workspace.mkdir(parents=True,exist_ok=True)
            payload={**self.settings,'state':str(self.state),'runtime_python':sys.executable,'runtime_cwd':str(Path(__file__).resolve().parents[2]),'folder':str(folder),'prompt':prompt,'task_id':cid}
            job={'id':cid,'prompt':prompt,'status':'running','events':[],'choices':{},'architecture':ARCHITECTURE,'response':'','created_at':time.time()};self.chats[cid]=job
            save_json(self.state/'chats'/(cid+'.json'),job)
            env={**os.environ,'BOKKIO_PROVIDER_KEY':self.api_key,'PYTHONPATH':str(Path(__file__).resolve().parents[1])+os.pathsep+os.environ.get('PYTHONPATH','')}
            process=subprocess.Popen([self.settings['harness_python'],'-m','bokkio.desktop_chat'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env,start_new_session=os.name!='nt')
            self.chat_processes[cid]=process;process.stdin.write(json.dumps(payload));process.stdin.close()
            def read():
                terminal_status=None
                def drain_stderr():
                    # Never persist raw SDK stderr, which may include provider request headers.
                    for _ in process.stderr:pass
                threading.Thread(target=drain_stderr,daemon=True).start()
                try:
                    for line in process.stdout:
                        try:event=json.loads(line)
                        except ValueError:continue
                        if event.get('kind')=='result':
                            terminal_status=event['status'];job.update(response=event.get('response',''),error=event.get('error'))
                        else:
                            with self.chat_log_lock:
                                ingest_choice(job,event);job['events'].append(event);job['events']=job['events'][-1000:]
                        save_json(self.state/'chats'/(cid+'.json'),job)
                        if terminal_status:break
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        from .executor import _terminate_pid
                        _terminate_pid(process.pid);process.wait(timeout=3)
                    if job['status']=='running':
                        if terminal_status:job['status']=terminal_status
                        else:job.update(status='failed',error='Harness exited before returning a result')
                finally:save_json(self.state/'chats'/(cid+'.json'),job)
            threading.Thread(target=read,daemon=True).start();return job
        if path=='/api/chat':
            cid=arg('id')
            if not cid or not __import__('re').fullmatch('[a-f0-9]{32}',cid):raise ValueError('Invalid task ID')
            return self.chat_view(self.chats.get(cid) or json.loads((self.state/'chats'/(cid+'.json')).read_text()))
        if path=='/api/chats':return sorted((json.loads(p.read_text()) for p in (self.state/'chats').glob('*.json')),key=lambda value:value.get('created_at',0),reverse=True)[:50]
        raise ValueError('Unknown desktop route')
    def close(self):
        self.route('POST','/api/emergency-stop',{});super().close()
        if self.inspector:self.inspector.call('session.close')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--state',required=True);args=parser.parse_args()
    state=Path(args.state).expanduser().resolve();state.mkdir(parents=True,exist_ok=True,mode=0o700)
    studio=DesktopStudio(state);token=secrets.token_urlsafe(32);server,url=create_server(studio,token=token)
    print(json.dumps({'ready':True,'url':url.split('/#')[0],'token':token}),flush=True)
    signal.signal(signal.SIGTERM,lambda *_:threading.Thread(target=server.shutdown,daemon=True).start())
    try:server.serve_forever()
    finally:studio.close();server.server_close()
if __name__=='__main__':main()
