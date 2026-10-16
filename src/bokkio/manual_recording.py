"""Scoped passive macOS input capture -> semantic workflow draft, never dispatches."""
from __future__ import annotations
import copy,json,subprocess,threading,time,sys,os
from pathlib import Path
from .app_launch import recorder_helper
from .audit import identifier,summarize
from .runtime_workflow import SCHEMA_V2,runtime_snapshot,window_identity
from .workflow import selector_for,save_json

class ManualRecorder:
    def __init__(self,client,apps,name='新 Workflow',excluded_window_prefixes=(),all_apps=False,excluded_pids=()):
        self.client=client;self.apps={f'app{i+1}':{k:a.get(k,'') for k in ['name','path','bundle_id']}for i,a in enumerate(apps)}
        self.pids={a['pid']:f'app{i+1}'for i,a in enumerate(apps)}
        self.all_apps=all_apps;self.excluded_pids=set(excluded_pids)
        self.excluded_window_prefixes=tuple(excluded_window_prefixes)
        self.doc={'schema':SCHEMA_V2,'id':identifier(),'name':name,'revision':1,'parent_sha256':None,'apps':self.apps,'steps':[]}
        self.paused_at=None;self.paused_duration=0;self.started_at=time.time();self.doc['platform']=sys.platform;self.doc['recording']={'started_at':self.started_at};self.issues=[];self.state='ready';self.lock=threading.RLock();self.lifecycle_lock=threading.RLock();self.process=None;self.error=None;self._merge_allowed=True;self._closing=False;self.reader_thread=None;self.stderr_tail=''
        self.draft_path=self.client.runtime.store.root/'workflow-drafts'/(self.doc['id']+'.json')
    def start(self):
        with self.lifecycle_lock:return self._start()
    def _start(self):
        if self.state not in {'ready','paused'}:raise ValueError('Recorder is already active or stopped')
        self.stop_file=self.draft_path.with_suffix('.stop');self.stop_file.unlink(missing_ok=True)
        command=[sys.executable,'-m','bokkio.windows_record'] if sys.platform=='win32' else [str(recorder_helper())]
        if sys.platform=='win32':command.append('--stop-file='+str(self.stop_file))
        if self.paused_at is not None:self.paused_duration+=time.time()-self.paused_at;self.paused_at=None
        process=subprocess.Popen([*command,*(['--all',*[f'--exclude={p}' for p in self.excluded_pids]] if self.all_apps else [str(p)for p in self.pids])],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1])+os.pathsep+os.environ.get('PYTHONPATH',''),'PYTHONUTF8':'1'})
        # Helper emits readiness before installing any capture loop.
        line=process.stdout.readline()
        try:ready=json.loads(line)
        except ValueError:
            process.terminate();process.wait(timeout=3);detail=process.stderr.read()[-2000:];raise RuntimeError('Recorder did not become ready: '+detail)
        if ready.get('status')!='recording':process.wait(timeout=2);raise RuntimeError(ready.get('error','Recorder failed'))
        def drain_stderr():
            for line in process.stderr:self.stderr_tail=(self.stderr_tail+line)[-2000:]
        threading.Thread(target=drain_stderr,daemon=True).start()
        self.process=process;self.state='recording';self.error=None;self._closing=False;self._persist()
        self.client.runtime.store.emit('recording.started',session_id=self.client.session_id,data={'workflow_id':self.doc['id'],'apps':list(self.pids)})
        self.reader_thread=threading.Thread(target=self._read,args=(process,),daemon=True);self.reader_thread.start()
    def _read(self,process):
        for line in process.stdout:
            try:
                event=json.loads(line)
                with self.lock:
                    if self.process is not process or self.state!='recording':continue
                    if 'error' in event:self.error=event['error'];self.state='failed';self._persist();continue
                    self.ingest(event)
            except Exception as e:
                with self.lock:
                    if len(self.issues)<200:self.issues.append({'id':identifier(),'reason':str(e),'resolved':False})
                    if len(self.doc['steps'])>=200:self.state='failed';self.error='Recording reached 200 steps; split this workflow';process.terminate()
                    self._persist()
        with self.lock:
            if self.process is process and self.state=='recording' and not self._closing:self.state='failed';self.error='Recorder exited unexpectedly; inspect captured steps';self._persist()
    def ingest(self,event):
        if event.get('pid') in self.excluded_pids:return
        if event.get('pid') not in self.pids:
            if not self.all_apps:return
            app=event.get('app',{})
            if not app.get('path') or not app.get('name'):return
            alias=next((k for k,a in self.apps.items() if a['path']==app['path']),None) or f'app{len(self.apps)+1}'
            self.apps[alias]={k:app.get(k,'') for k in ('name','path','bundle_id')};self.pids[event['pid']]=alias
        if any((event.get('window') or '').startswith(p) for p in self.excluded_window_prefixes):return
        if event.get('captured'):
            return self._captured(event)
        if event.get('kind')=='unsupported':
            if len(self.issues)<200:self.issues.append({'id':identifier(),'reason':event.get('reason','Unsupported gesture'),'resolved':False})
            self._persist();return
        alias=self.pids[event['pid']];window=event.get('window') or next((a['name']for a in event.get('ancestors',[])if a['role'] in {'AXWindow','AXDialog'}),None)
        if not window:raise ValueError('No exact window identity was captured')
        try:_,snapshot=runtime_snapshot(self.client,event['pid'],window)
        except (ValueError,RuntimeError):
            response=self.client.call('desktop.windows',{'app':str(event['pid'])});candidates=response.get('result',[]) if response['status']=='completed' else []
            matches=[n for n in candidates if window_identity(n)==event.get('window_identity')]
            if len(matches)!=1:raise
            window=matches[0]['name'];_,snapshot=runtime_snapshot(self.client,event['pid'],window)
        nodes=snapshot['windows'];wanted=event.get('identifier');rawrole=event.get('role')
        matches=[n for n in nodes if (n.get('platform_data',{}).get('ax_role')==rawrole or n.get('role')==rawrole) and (wanted in {n.get('platform_data',{}).get('ax_identifier'),n.get('platform_data',{}).get('automation_id')} if wanted else (n.get('name') or '')==event.get('name',''))]
        if not matches and event.get('bounds'):
            matches=[n for n in nodes if (n.get('platform_data',{}).get('ax_role')==rawrole or n.get('role')==rawrole) and n.get('bounds')==event['bounds']]
        if len(matches)>1 and event.get('bounds'):
            b=event['bounds'];matches=[n for n in matches if n.get('bounds')==b]
        if len(matches)!=1:raise ValueError('Manual target is unavailable or ambiguous; review the step')
        node=matches[0]
        if node.get('platform_data',{}).get('ax_subrole')=='AXSecureTextField' or node.get('platform_data',{}).get('is_password'):return
        if event['kind']=='drag':
            windows=[n for n in nodes if n['role']=='window' and n.get('name')==window]
            if len(windows)!=1:raise ValueError('Drag needs an unambiguous window anchor')
            node=windows[0];wanted=None
        actions=node['actions']
        kind='native'
        if event['kind']=='edit':
            if 'set_value' not in actions and 'focus' not in actions and node.get('state',{}).get('focused') is not True:raise ValueError('Editable target cannot receive focus')
            action='set_value' if 'set_value' in actions else 'replace_text';kind='native' if action=='set_value' else 'input';args={'value':event['value']};verify=[{'role':node['role'],'name':node['name'],'field':'value','equals':event['value']}]
        elif event['kind'] in {'key','scroll','right_click','drag'}:
            kind='input';action=event['kind'];args={k:event[k] for k in ['key','direction','amount','duration'] if k in event};verify=[]
        else:
            preferred=['focus'] if node['role'] in {'text_field','text_area','combo_box'} else []
            action=next((a for a in preferred+(['open'] if event.get('double_click') else [])+['click','select']if a in actions),None)
            if not action:kind='input';action='double_click' if event.get('double_click') else 'click'
            args={};field='selected' if action=='select' else 'focused' if action=='focus' else 'present'
            verify=[{'role':node['role'],'name':node['name'],'field':field,'equals':True}] if field in {'selected','focused'} else []
        target=selector_for(snapshot,node)
        if wanted:target['identifier']=wanted
        if node.get('bounds'):target['bounds']=node['bounds']
        if kind=='input' and 'x' in event:
            b=node.get('bounds') or event.get('bounds');
            if not b or not b['width'] or not b['height']:raise ValueError('Input target has no bounds')
            target['point']={'x':max(0,min(1,(event['x']-b['x'])/b['width'])),'y':max(0,min(1,(event['y']-b['y'])/b['height']))}
            if action=='drag':
                args.update(end_x=(event['end_x']-b['x'])/b['width'],end_y=(event['end_y']-b['y'])/b['height'])
                if not 0<=args['end_x']<=1 or not 0<=args['end_y']<=1:raise ValueError('Drag destination lies outside the captured anchor; choose a container anchor in the editor')
        step={'id':identifier(),'kind':kind,'recorded_at':round(max(0,event.get('timestamp',time.time())-self.started_at-self.paused_duration),3),'app':alias,'window':window,'target':target,'action':action,'arguments':args,'wait':[],'verify':verify,'timeout':10,'label':(node.get('name') or wanted or node['role'])[:200]}
        if action in {'set_value','replace_text'} and self.doc['steps'] and self.doc['steps'][-1].get('target',{}).get('identifier')==target.get('identifier') and self.doc['steps'][-1].get('target',{}).get('name')==target.get('name') and self._merge_allowed and self.doc['steps'] and all(self.doc['steps'][-1].get(k)==step[k] for k in ['app','window','action']):
            step['id']=self.doc['steps'][-1]['id'];self.doc['steps'][-1]=step
        else:
            if len(self.doc['steps'])>=200:raise ValueError('Recording reached 200 steps; stop and split the workflow')
            self.doc['steps'].append(step)
        windows=[n for n in nodes if n['role'] in {'window','dialog'} and n.get('name')==window]
        if len(windows)==1:
            win=windows[0];data=win.get('platform_data',{});identity=window_identity(win)
            step['window_context']={k:v for k,v in {'key':identity,'identity':identity,'role':win['role'],'class_name':data.get('class_name'),'subrole':data.get('ax_subrole')}.items() if v}
        self._merge_allowed=True;self._persist()
        self.client.runtime.store.emit('recording.step',session_id=self.client.session_id,data={'workflow_id':self.doc['id'],'step_id':step['id'],'action':action,'target':summarize(target),'arguments':summarize(args),'source':'passive_manual_input','business_verified':False})
    def _captured(self,event):
        # Use the target observed at input time. A click can close its dialog before Python reads the event.
        import re
        if event.get('kind')=='unsupported':
            self.issues.append({'id':identifier(),'reason':event.get('reason','Unsupported input'),'resolved':False});self._persist();return
        if event.get('secure'):return
        if event['kind']=='drag' and event.get('window_target'):event={**event,**event['window_target']}
        def role(value):
            if not value.startswith('AX'):return value
            aliases={'AXScrollArea':'group','AXSplitGroup':'group','AXRadioGroup':'group','AXPopUpButton':'combo_box','AXMenuButton':'combo_box','AXMenuBarItem':'menu_item','AXColorWell':'unknown','AXRuler':'unknown','AXRulerMarker':'unknown'}
            return aliases.get(value,re.sub(r'(?<=[a-z0-9])(?=[A-Z])','_',value[2:]).lower())
        name=lambda v:v or None
        window=event.get('window')
        if not window:raise ValueError('Captured action has no window context')
        target={'ref':'captured','role':role(event['role']),'name':name(event.get('name')),
                'ancestors':[{'role':role(a['role']),'name':name(a.get('name'))} for a in event.get('ancestors',[]) if role(a['role'])!='application']}
        if event['role'].startswith('AX'):
            target['native_selector']={'role':event['role'],'ancestors':[{'role':a['role'],'name':name(a.get('name'))} for a in event.get('ancestors',[]) if a['role']!='AXApplication']}
        if event.get('identifier'):target['identifier']=event['identifier']
        if event.get('bounds'):target['bounds']=event['bounds']
        action={'edit':'replace_text'}.get(event['kind'],event['kind'])
        if action=='click' and event.get('double_click'):action='double_click'
        if action not in {'replace_text','click','double_click','right_click','key','scroll','drag'}:return
        args={k:event[k] for k in ('key','value','direction','amount','duration') if k in event}
        if action=='key' and event.get('key') in {'Command+Tab','Command+Shift+Tab','Alt+Tab','Alt+Shift+Tab','Win+Tab','Win+R','Command+Space'}:return
        bounds=event.get('bounds',{})
        if action in {'click','double_click','right_click','scroll','drag'}:
            if not bounds.get('width') or not bounds.get('height'):raise ValueError('Captured input has no usable bounds')
            target['point']={k:max(0,min(1,(event[k]-bounds[k])/bounds[dimension])) for k,dimension in [('x','width'),('y','height')]}
            if action=='drag':
                args.update(end_x=(event['end_x']-bounds['x'])/bounds['width'],end_y=(event['end_y']-bounds['y'])/bounds['height'])
                if not 0<=args['end_x']<=1 or not 0<=args['end_y']<=1:raise ValueError('Drag ends outside its captured window; choose a container anchor in the editor')
        step={'id':identifier(),'kind':'input','app':self.pids[event['pid']],'window':window,'target':target,'action':action,'arguments':args,
              'recorded_at':round(max(0,event.get('timestamp',time.time())-self.started_at-self.paused_duration),3),
              'wait':[],'verify':[{'role':target['role'],'name':target['name'],'field':'value','equals':event['value']}] if action=='replace_text' else [],
              'timeout':10,'label':(target['name'] or target['role'])[:200]}
        identity=event.get('window_identity')
        if identity:step['window_context']={'key':identity,'identity':identity,'role':event.get('window_role','window')}
        previous=self.doc['steps'][-1] if self.doc['steps'] else None
        if previous and self._merge_allowed and action=='replace_text' and all(previous.get(k)==step.get(k) for k in ('app','window','action','target')):
            step['id']=previous['id'];self.doc['steps'][-1]=step
        else:
            if len(self.doc['steps'])>=200:raise ValueError('Recording reached 200 steps; stop and split the workflow')
            self.doc['steps'].append(step)
        self._merge_allowed=True;self._persist()
        self.client.runtime.store.emit('recording.step',session_id=self.client.session_id,data={'workflow_id':self.doc['id'],'step_id':step['id'],'action':action,'source':'input_time_native_target','business_verified':False})
    def _persist(self):save_json(self.draft_path,self.preview())
    def _finish_capture(self):
        p=self.process;self._closing=True
        if p and p.poll() is None:
            if sys.platform=='win32':self.stop_file.touch()
            else:p.terminate()
            try:p.wait(timeout=3)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2)
        if self.reader_thread:self.reader_thread.join(timeout=3)
        if hasattr(self,'stop_file'):self.stop_file.unlink(missing_ok=True)
        with self.lock:self.process=None
    def pause(self):
        with self.lifecycle_lock:return self._pause()
    def _pause(self):
        if self.state!='recording':raise ValueError('Recorder is not active')
        self.paused_at=time.time();self._finish_capture()
        with self.lock:self.state='paused';self._merge_allowed=False;self._persist()
        self.client.runtime.store.emit('recording.paused',session_id=self.client.session_id,data={'workflow_id':self.doc['id']})
    def stop(self):
        with self.lifecycle_lock:return self._stop()
    def _stop(self):
        self._finish_capture()
        with self.lock:self.state='stopped';self._persist()
        self.client.call('session.close')
        return self.preview()
    def preview(self):
        with self.lock:return {'status':self.state,'document':copy.deepcopy(self.doc),'issues':copy.deepcopy(self.issues),'error':self.error}
