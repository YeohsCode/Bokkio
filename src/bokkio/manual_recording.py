"""Scoped passive macOS input capture -> semantic workflow draft, never dispatches."""
from __future__ import annotations
import copy,json,subprocess,threading,time
from .app_launch import recorder_helper
from .audit import identifier,summarize
from .runtime_workflow import SCHEMA,runtime_snapshot
from .workflow import selector_for

class ManualRecorder:
    def __init__(self,client,apps,name='新 Workflow',excluded_window_prefixes=()):
        self.client=client;self.apps={f'app{i+1}':{k:a.get(k,'') for k in ['name','path','bundle_id']}for i,a in enumerate(apps)}
        self.pids={a['pid']:f'app{i+1}'for i,a in enumerate(apps)}
        self.excluded_window_prefixes=tuple(excluded_window_prefixes)
        self.doc={'schema':SCHEMA,'id':identifier(),'name':name,'revision':1,'parent_sha256':None,'apps':self.apps,'steps':[]}
        self.issues=[];self.state='ready';self.lock=threading.RLock();self.process=None;self.error=None;self._merge_allowed=True
    def start(self):
        if self.state not in {'ready','paused'}:raise ValueError('Recorder is already active or stopped')
        process=subprocess.Popen([str(recorder_helper()),*[str(p)for p in self.pids]],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        # Helper emits readiness before installing any capture loop.
        line=process.stdout.readline()
        try:ready=json.loads(line)
        except ValueError:process.terminate();raise RuntimeError('Recorder did not become ready')
        if ready.get('status')!='recording':process.wait(timeout=2);raise RuntimeError(ready.get('error','Recorder failed'))
        self.process=process;self.state='recording';self.error=None
        self.client.runtime.store.emit('recording.started',session_id=self.client.session_id,data={'workflow_id':self.doc['id'],'apps':list(self.pids)})
        threading.Thread(target=self._read,args=(process,),daemon=True).start()
    def _read(self,process):
        for line in process.stdout:
            try:
                event=json.loads(line)
                with self.lock:
                    if self.process is not process or self.state!='recording':continue
                    if 'error' in event:self.error=event['error'];self.state='failed';continue
                    self.ingest(event)
            except Exception as e:
                with self.lock:self.issues.append({'id':identifier(),'reason':str(e),'resolved':False})
        with self.lock:
            if self.process is process and self.state=='recording':self.state='failed';self.error='Recorder exited unexpectedly; inspect captured steps'
    def ingest(self,event):
        if event.get('pid') not in self.pids:return
        if any((event.get('window') or '').startswith(p) for p in self.excluded_window_prefixes):return
        if event.get('kind')=='unsupported':
            self.issues.append({'id':identifier(),'reason':event.get('reason','Unsupported gesture'),'resolved':False});return
        alias=self.pids[event['pid']];window=event.get('window') or next((a['name']for a in event.get('ancestors',[])if a['role'] in {'AXWindow','AXDialog'}),None)
        if not window:raise ValueError('No exact window identity was captured')
        _,snapshot=runtime_snapshot(self.client,event['pid'],window)
        nodes=snapshot['windows'];wanted=event.get('identifier');rawrole=event.get('role')
        matches=[n for n in nodes if n.get('platform_data',{}).get('ax_role')==rawrole and (n.get('platform_data',{}).get('ax_identifier')==wanted if wanted else (n.get('name') or '')==event.get('name',''))]
        if len(matches)!=1:raise ValueError('Manual target is unavailable or ambiguous; review the step')
        node=matches[0]
        if event['kind']=='click' and node['role'] in {'window','application'}:
            raise ValueError('Click has no semantic control target; add a reviewed alternative step')
        if node.get('platform_data',{}).get('ax_subrole')=='AXSecureTextField':return
        actions=node['actions']
        if event['kind']=='edit':
            if 'set_value' not in actions:raise ValueError('This field has no deterministic value write; add a reviewed alternative step')
            action='set_value';args={'value':event['value']};verify=[{'role':node['role'],'name':node['name'],'field':'value','equals':event['value']}]
        else:
            preferred=['focus'] if node['role'] in {'text_field','text_area','combo_box'} else []
            action=next((a for a in preferred+(['open'] if event.get('double_click') else [])+['click','select','focus']if a in actions),None)
            if not action:raise ValueError('Manual target has no supported semantic action')
            args={};field='selected' if action=='select' else 'focused' if action=='focus' else 'present'
            verify=[{'role':node['role'],'name':node['name'],'field':field,'equals':True}]
        target=selector_for(snapshot,node)
        if wanted:target['identifier']=wanted
        step={'id':identifier(),'kind':'native','app':alias,'window':window,'target':target,'action':action,'arguments':args,'wait':[],'verify':verify,'timeout':10,'label':(node.get('name') or node['role'])}
        if action=='set_value' and self._merge_allowed and self.doc['steps'] and all(self.doc['steps'][-1].get(k)==step[k] for k in ['app','window','target','action']):
            step['id']=self.doc['steps'][-1]['id'];self.doc['steps'][-1]=step
        else:
            if len(self.doc['steps'])>=200:raise ValueError('Recording reached 200 steps; stop and split the workflow')
            self.doc['steps'].append(step)
        self._merge_allowed=True
        self.client.runtime.store.emit('recording.step',session_id=self.client.session_id,data={'workflow_id':self.doc['id'],'step_id':step['id'],'action':action,'target':summarize(target),'arguments':summarize(args),'source':'passive_manual_input','business_verified':False})
    def pause(self):
        with self.lock:
            if self.state!='recording':raise ValueError('Recorder is not active')
            self.state='paused';p=self.process;self.process=None;self._merge_allowed=False
        p.terminate();p.wait(timeout=3)
        self.client.runtime.store.emit('recording.paused',session_id=self.client.session_id,data={'workflow_id':self.doc['id']})
    def stop(self):
        with self.lock:
            p=self.process;self.process=None;self.state='stopped'
        if p and p.poll() is None:p.terminate();p.wait(timeout=3)
        self.client.call('session.close')
        return self.preview()
    def preview(self):
        with self.lock:return {'status':self.state,'document':copy.deepcopy(self.doc),'issues':copy.deepcopy(self.issues),'error':self.error}
