"""Human-recorded, versioned workflows executed exclusively through enterprise Runtime."""
from __future__ import annotations
import copy,json,re,threading,time
from contextlib import contextmanager
from pathlib import Path
from .audit import digest,identifier,summarize
from .execution_context import workflow_step
from .workflow import save_json,selector_for,resolve,validate_checks
from .agent import verify_conditions

SCHEMA='bokkio.runtime-workflow.v1'
SCHEMA_V2='bokkio.runtime-workflow.v2'
KINDS={'native','input','wait','check','browser.open','browser.act','code.run'}

@contextmanager
def library_lock(root):
    # Serialize revisions across CLI, MCP and multiple Studio processes.
    with (Path(root)/'.library.lock').open('a+b') as stream:
        if stream.seek(0,2)==0:stream.write(b'0');stream.flush()
        if __import__('os').name=='nt':
            import msvcrt
            stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_LOCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
        try:yield
        finally:
            if __import__('os').name=='nt':stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)

def validate_document(doc):
    if not isinstance(doc,dict) or doc.get('schema') not in {SCHEMA,SCHEMA_V2}:raise ValueError('Unsupported workflow schema')
    if set(doc)-{'schema','id','name','revision','parent_sha256','sha256','apps','steps','description','resources','parameters','recording','platform','group'}:raise ValueError('Unknown workflow fields')
    extended=doc['schema']==SCHEMA_V2
    if not extended and set(doc)&{'parameters','recording','platform','group'}:raise ValueError('Extended fields require Workflow v2')
    declarations=doc.get('parameters',{})
    if not isinstance(declarations,dict) or any(not re.fullmatch(r'[\w-]{1,80}',k) or not isinstance(v,dict) or set(v)-{'type','default','description'} or v.get('type','string')!='string' or not isinstance(v.get('default',''),str) for k,v in declarations.items()):raise ValueError('Invalid parameter declarations')
    recording=doc.get('recording',{})
    if not isinstance(recording,dict) or set(recording)-{'started_at'}:raise ValueError('Invalid recording metadata')
    if 'started_at' in recording and (type(recording['started_at']) not in {int,float} or not __import__('math').isfinite(recording['started_at']) or recording['started_at']<0):raise ValueError('Invalid recording start time')
    resources=doc.get('resources',{})
    if not isinstance(resources,dict) or set(resources)-{'paths','origins'}:raise ValueError('Invalid workflow resources')
    for key in ['paths','origins']:
        if not isinstance(resources.get(key,[]),list) or any(not isinstance(v,str) for v in resources.get(key,[])):raise ValueError('Invalid resource list')
    if not re.fullmatch('[a-f0-9]{32}',doc.get('id','')):raise ValueError('Invalid workflow ID')
    if not isinstance(doc.get('name'),str) or not doc['name'].strip() or len(doc['name'])>200:raise ValueError('Workflow name is required')
    if not isinstance(doc.get('apps'),dict) or len(doc['apps'])>20:raise ValueError('Invalid application identities')
    if type(doc.get('revision')) is not int or doc['revision']<1:raise ValueError('Invalid revision')
    for alias,g in doc['apps'].items():
        if not re.fullmatch('[A-Za-z0-9_-]{1,64}',alias) or not isinstance(g,dict) or set(g)-{'name','path','bundle_id'} or not isinstance(g.get('name'),str) or not isinstance(g.get('path'),str) or not Path(g['path']).is_absolute():raise ValueError('Applications require exact installed identities')
    steps=doc.get('steps')
    if not isinstance(steps,list) or len(steps)>200:raise ValueError('Workflow supports at most 200 steps')
    ids=set()
    for s in steps:
        if not isinstance(s,dict) or s.get('kind') not in KINDS or set(s)-{'id','kind','app','window','target','action','arguments','verify','wait','timeout','label','enabled','breakpoint','recorded_at','window_context'}:raise ValueError('Invalid workflow step')
        if not isinstance(s.get('id'),str) or s['id'] in ids:raise ValueError('Steps need unique IDs')
        ids.add(s['id'])
        if 'label' in s and (not isinstance(s['label'],str) or len(s['label'])>200):raise ValueError('Invalid step label')
        if 'recorded_at' in s and (type(s['recorded_at']) not in {int,float} or not __import__('math').isfinite(s['recorded_at']) or s['recorded_at']<0):raise ValueError('Invalid step timestamp')
        if type(s.get('timeout',10)) not in {int,float} or not 0<s.get('timeout',10)<=30:raise ValueError('Step timeout must be 0..30 seconds')
        args=s.get('arguments',{})
        if not isinstance(args,dict):raise ValueError('Step arguments must be an object')
        if not extended and (s['kind'] in {'input','wait','check'} or set(s)&{'enabled','breakpoint','recorded_at','window_context'}):raise ValueError('Extended steps require Workflow v2')
        for flag in ('enabled','breakpoint'):
            if flag in s and type(s[flag]) is not bool:raise ValueError('Step flags require booleans')
        if s['kind'] in {'native','input','wait','check'}:
            if s.get('app') not in doc['apps'] or not isinstance(s.get('window'),str) or not s['window']:raise ValueError('Native steps need an application and exact window')
            from .xa11y_backend import ACTION_METHODS
            if 'window_context' in s and (not isinstance(s['window_context'],dict) or set(s['window_context'])-{'key','identity','role','class_name','subrole'} or not isinstance(s['window_context'].get('key'),str)):raise ValueError('Invalid window context')
            if s['kind']=='native' and s.get('action') not in ACTION_METHODS:raise ValueError('Unsupported native action')
            target=s.get('target')
            if not isinstance(target,dict) or set(target)-{'ref','role','name','ancestors','fallback','identifier','bounds','point','end_target','image'} or not isinstance(target.get('role'),str) or not isinstance(target.get('ancestors'),list):raise ValueError('Native step needs a semantic selector')
            if 'name' not in target or target['name'] is not None and not isinstance(target['name'],str):raise ValueError('Invalid target name')
            if set(args)-{'value','expected_value','direction','amount','key','button','x','y','end_x','end_y','duration'}:raise ValueError('Action arguments cannot override application or target bindings')
            if target.get('image'):
                image=target['image']
                if not isinstance(image,dict) or set(image)-{'png','threshold'} or not isinstance(image.get('png'),str) or len(image['png'])>400000 or s['kind']=='native':raise ValueError('Image anchors require bounded PNG input/wait/check steps')
            for a in target['ancestors']:
                if not isinstance(a,dict) or set(a)!={'role','name'} or not isinstance(a['role'],str):raise ValueError('Invalid selector context')
            validate_checks(s.get('verify',[]));validate_checks(s.get('wait',[]))
            if not extended and not s.get('verify'):raise ValueError('Native steps need a completion check')
            if s['kind'] in {'wait','check'} and not (s.get('verify') or s.get('wait') or target.get('image')):raise ValueError('Condition steps require checks')
            from .tool_schema import validate
            if s['kind'] in {'native','input'}:
                validate('desktop.input' if s['kind']=='input' else 'desktop.act',{'app':'0','observation_id':'0','ref':'0','action':s['action'],**args})
        else:
            from .tool_schema import validate
            validate(s['kind'],args)
            if 'verify' in s or 'wait' in s:raise ValueError('Use native conditions only on native steps')
    return doc


class WorkflowLibrary:
    def __init__(self,root):self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True,mode=0o700);self.lock=threading.RLock()
    def folder(self,wid):
        if not isinstance(wid,str) or not re.fullmatch('[a-f0-9]{32}',wid):raise ValueError('Invalid workflow ID')
        return self.root/wid
    def list(self):
        rows=[]
        for path in sorted(self.root.glob('*/head.json')):
            doc=json.loads(path.read_text())
            if not doc.get('archived'):rows.append({k:doc[k] for k in ['id','name','revision','sha256']})
        return rows
    def get(self,wid,revision=None):
        folder=self.folder(wid)
        head=json.loads((folder/'head.json').read_text())
        if head.get('archived') and revision is None:raise ValueError('Workflow is archived')
        version=head['revision'] if revision is None else revision
        if type(version) is not int or version<1:raise ValueError('Invalid revision')
        doc=json.loads((folder/(str(version)+'.json')).read_text());validate_document(doc)
        if digest({k:v for k,v in doc.items() if k!='sha256'})!=doc['sha256']:raise ValueError('Workflow was modified outside versioned storage')
        return doc
    def save(self,doc,expected_sha=None):
        with self.lock,library_lock(self.root):
            value=copy.deepcopy(doc);folder=self.folder(value['id']);previous=None
            if (folder/'head.json').exists():
                previous=self.get(value['id'])
                if expected_sha!=previous['sha256']:raise ValueError('Workflow changed; reload before editing')
            elif expected_sha:raise ValueError('Workflow does not exist')
            value.update(schema=value.get('schema',SCHEMA),revision=previous['revision']+1 if previous else 1,parent_sha256=previous['sha256'] if previous else None)
            value.pop('sha256',None);validate_document(value);value['sha256']=digest(value)
            save_json(folder/(str(value['revision'])+'.json'),value)
            save_json(folder/'head.json',{k:value[k] for k in ['id','name','revision','sha256']})
            return value
    def archive(self,wid,expected_sha):
        with self.lock,library_lock(self.root):
            value=self.get(wid)
            if expected_sha!=value['sha256']:raise ValueError('Workflow changed; reload before archiving')
            save_json(self.folder(wid)/'head.json',{**{k:value[k]for k in ['id','name','revision','sha256']},'archived':True})
    def archived(self):
        return [json.loads(p.read_text()) for p in self.root.glob('*/head.json') if json.loads(p.read_text()).get('archived')]
    def restore(self,wid,expected_sha):
        with self.lock,library_lock(self.root):
            folder=self.folder(wid);head=json.loads((folder/'head.json').read_text())
            if not head.get('archived') or head['sha256']!=expected_sha:raise ValueError('Archived workflow changed; reload the library')
            head.pop('archived');save_json(folder/'head.json',head);return self.get(wid)
    def revisions(self,wid):return sorted(int(p.stem) for p in self.folder(wid).glob('*.json') if p.stem.isdigit())


def window_identity(node):
    data=node.get('platform_data',{})
    if data.get('ax_native_identity') is not None:return 'ax:'+str(data['ax_native_identity'])
    stable=data.get('native_stable_id') or ''
    if stable.startswith('hwnd:'):
        try:return 'hwnd:'+str(int(stable[5:],0))
        except ValueError:return stable
    hwnd=data.get('hwnd') or data.get('native_window_handle')
    return 'hwnd:'+str(hwnd) if hwnd else stable or node['ref']

def runtime_snapshot(client,pid,window):
    r=client.call('desktop.observe',{'app':str(pid),'window':window,'max_nodes':2000,'max_bytes':2000000})
    if r['status']!='completed':raise RuntimeError(r)
    if r['result']['truncated']:raise ValueError('Target observation exceeded budget; narrow the window')
    return r,{'windows':r['result']['nodes']}


def find_target(snapshot,target,action):
    selector={k:v for k,v in target.items() if k not in {'identifier','bounds','point','end_target','image'}};selector.setdefault('ref','recorded')
    if target.get('identifier'):
        # Narrow by identity first, retain parent nodes for ancestry checks.
        wanted=target['identifier'];nodes=snapshot['windows'];matches=[]
        for n in nodes:
            data=n.get('platform_data',{})
            if wanted in {data.get('ax_identifier'),data.get('automation_id')}:matches.append(n['ref'])
        if not matches:raise ValueError('Recorded control identifier is missing or ambiguous')
        snapshot={'windows':[n if n['ref'] in matches else {**n,'actions':[]} for n in nodes]}
    if action=='__input__':
        nodes=snapshot['windows'];matches=[]
        for n in nodes:
            if n.get('role')==selector['role'] and n.get('name')==selector['name'] and selector_for(snapshot,n)['ancestors']==selector['ancestors']:
                if not target.get('identifier') or n['ref'] in {x['ref'] for x in nodes if target['identifier'] in {x.get('platform_data',{}).get('ax_identifier'),x.get('platform_data',{}).get('automation_id')}}:matches.append(n)
        if len(matches)!=1:raise ValueError('Input target is unavailable or ambiguous')
        return matches[0]
    return resolve(snapshot,selector,action)[0]


class RuntimeWorkflowRunner:
    """Durable exact-operation checkpointing. Unknown completion never retries."""
    def __init__(self,client,root):self.client=client;self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True,mode=0o700);self.lock=threading.Lock()
    def path(self,rid):
        if not re.fullmatch('[a-f0-9]{32}',rid):raise ValueError('Invalid run ID')
        return self.root/(rid+'.json')
    def load(self,rid):
        r=json.loads(self.path(rid).read_text())
        if self.path(rid).with_suffix('.cancel').exists() and r['status'] in {'ready','paused','waiting_approval'}:r['status']='cancelled'
        return r
    def cancel(self,rid):
        save_json(self.path(rid).with_suffix('.cancel'),{'cancel':True})
        r=self.load(rid)
        if r.get('approval_id'):
            try:self.client.runtime.store.decide(r['approval_id'],'denied','Workflow cancelled before dispatch')
            except ValueError:pass
        if r['status']=='cancelled':self._save(r)
        if r.get('job_id'):self.client.call('job.cancel',{'job_id':r['job_id']})
        self.client.call('session.close')
    def pause(self,rid):save_json(self.path(rid).with_suffix('.pause'),{'pause':True})
    def resume(self,rid):self.path(rid).with_suffix('.pause').unlink(missing_ok=True);return self.run(rid)
    def start(self,doc,mode='headed',parameters=None,repeat=1,speed=1,single=False):
        validate_document(doc)
        if type(repeat) is not int or not 1<=repeat<=100 or type(speed) not in {int,float} or not .1<=speed<=10:raise ValueError('Invalid replay controls')
        values={k:v.get('default','') for k,v in doc.get('parameters',{}).items()}
        if parameters is not None:
            if not isinstance(parameters,dict) or set(parameters)-set(values) or any(not isinstance(v,str) for v in parameters.values()):raise ValueError('Invalid workflow parameter values')
            values.update(parameters)
        original_sha=doc['sha256']
        def bind(value):
            if isinstance(value,str):
                def replace(m):
                    if m[1] not in values:raise ValueError('Missing workflow parameter: '+m[1])
                    return values[m[1]]
                return re.sub(r'\$\{([\w-]+)\}',replace,value)
            if isinstance(value,list):return [bind(v) for v in value]
            if isinstance(value,dict):return {k:bind(v) for k,v in value.items()}
            return value
        doc=copy.deepcopy(doc);doc['steps']=bind(doc['steps'])
        validate_document(doc)
        if not doc['steps']:raise ValueError('Add or record steps before running')
        if mode not in {'headed','headless'}:raise ValueError('Invalid replay mode')
        if mode=='headless' and any(s['kind']=='input' or s['kind']=='native' and s['action'] in {'type','select_text'} for s in doc['steps']):raise ValueError('Background desktop replay requires deterministic native value writes; replace type/select_text with set_value')
        rid=identifier();run={'id':rid,'workflow':copy.deepcopy(doc),'workflow_sha256':original_sha,'bound_sha256':digest(doc),'parameters':values,'repeat':repeat,'cycle':1,'speed':speed,'single':single,'session_id':self.client.session_id,'mode':mode,'status':'ready','index':0,'steps':[],'bindings':{},'pending':None}
        save_json(self.path(rid),run);return run
    def repair(self,rid,doc,parameters=None):
        validate_document(doc);r=self.load(rid)
        if r['status'] not in {'failed','paused'}:raise ValueError('Pause the run or inspect its failure before applying a repair')
        if r.get('job_id'):raise ValueError('This code job already ran; inspect its output before starting another run')
        current=r['workflow']['steps'][r['index']]
        candidates=[i for i,s in enumerate(doc['steps']) if s['id']==current['id']]
        if len(candidates)!=1:raise ValueError('Keep the current step ID when repairing; re-record its replacement into this step')
        values={k:v.get('default','') for k,v in doc.get('parameters',{}).items()};values.update({k:v for k,v in r.get('parameters',{}).items() if k in values})
        if parameters:
            if set(parameters)-set(values) or any(not isinstance(v,str) for v in parameters.values()):raise ValueError('Invalid repaired parameters')
            values.update(parameters)
        def bind(value):
            if isinstance(value,str):
                def replace(m):
                    if m[1] not in values:raise ValueError('Missing workflow parameter: '+m[1])
                    return values[m[1]]
                return re.sub(r'\$\{([\w-]+)\}',replace,value)
            if isinstance(value,list):return [bind(v) for v in value]
            if isinstance(value,dict):return {k:bind(v) for k,v in value.items()}
            return value
        future=bind(copy.deepcopy(doc['steps'][candidates[0]:]));after_action=bool(r.get('verification_pending'))
        if after_action:
            # The original receipt is retrieved, then only the completion check
            # is rerun. A repair cannot mutate an already dispatched operation.
            if any(future[0].get(k)!=current.get(k) for k in ('kind','app','window','target','action','arguments')):raise ValueError('The action already ran; change only its completion checks or timeout')
            if doc['apps'].get(current.get('app'))!=r['workflow']['apps'].get(current.get('app')):raise ValueError('The action already ran; keep its original application identity')
            if not future[0].get('verify'):raise ValueError('Keep a completion check for the action that already ran')
        elif r.get('pending') and r.get('last_receipt',{}).get('dispatched') is not False:
            raise ValueError('The previous action may have run; inspect the application before starting another run')
        old_sha=r['bound_sha256'];original_apps=copy.deepcopy(r['workflow']['apps']);apps=copy.deepcopy(original_apps);apps.update(doc['apps']);r['workflow']['apps']=apps
        if not after_action:
            for alias in list(r['bindings']):
                original=original_apps.get(alias)
                if alias in doc['apps'] and original!=doc['apps'][alias]:r['bindings'].pop(alias,None);r['window_bindings']={k:v for k,v in r.get('window_bindings',{}).items() if not k.startswith(alias+':')}
            r['pending']=None;r.pop('error',None);r.pop('timed_step',None)
        r['workflow']['steps']=r['workflow']['steps'][:r['index']]+future;r['parameters']=values
        validate_document(r['workflow']);r['bound_sha256']=digest(r['workflow']);r.setdefault('repairs',[]).append({'source_sha256':doc['sha256'],'step_id':current['id'],'previous_bound_sha256':old_sha,'mode':'verify' if after_action else 'continue'})
        r.update(status='paused',pause_reason='repaired');self._save(r)
        self.client.runtime.store.emit('workflow.repaired',session_id=self.client.session_id,data={'run_id':rid,'step_id':current['id'],'source_sha256':doc['sha256'],'after_dispatch':after_action})
        return r
    def _save(self,r):save_json(self.path(r['id']),r)
    def _call(self,r,tool,args,phase):
        if self.path(r['id']).with_suffix('.cancel').exists():
            r['status']='cancelled';self._save(r);return None
        if self.path(r['id']).with_suffix('.pause').exists():
            r['status']='paused';self._save(r);return None
        pending=r['pending']
        if not pending:
            pending={'tool':tool,'arguments':args,'operation_id':identifier(),'phase':phase};r['pending']=pending;self._save(r)
        result=self.client.call(pending['tool'],pending['arguments'],pending['operation_id'])
        r['last_receipt']=result;self._save(r)
        if result['status']=='approval_required':
            r.update(status='waiting_approval',approval_id=result['approval_id']);self._save(r);return None
        if result['status'] not in {'completed','executed','verified','queued'}:
            # Fresh observations after approved-but-expired native requests require a NEW approval.
            if result.get('error_code')=='stale_snapshot' or result.get('error_type')=='BokkioStaleSnapshot':
                if result.get('dispatched') is False and r.get('stale_refreshes',0)<2:
                    r['pending']=None;r['stale_refreshes']=r.get('stale_refreshes',0)+1;r['status']='running';self._save(r);return 'refresh'
            r.update(status='completion_unknown' if result['status']=='completion_unknown' else 'failed',error=result);self._save(r);return None
        # Keep the exact operation until its checkpoint is committed. A crash
        # before verification/advancement must retrieve this cached receipt.
        r.pop('approval_id',None);r['stale_refreshes']=0;self._save(r)
        return result
    def run(self,rid):
        with library_lock(self.root):return self._run(rid)
    def _run(self,rid):
        if not self.lock.acquire(blocking=False):raise ValueError('A replay is already active')
        context_token=workflow_step.set(None)
        try:
            r=self.load(rid)
            if r['session_id']!=self.client.session_id:raise ValueError('Resume requires the original live Runtime session')
            if r['status'] in {'completed','failed','completion_unknown','cancelled'}:return r
            r['status']='running';self._save(r)
            self.client.runtime.store.emit('workflow.resumed',session_id=self.client.session_id,data={'run_id':rid,'workflow_sha256':r['workflow_sha256'],'next_step':r['index']})
            while r['index']<len(r['workflow']['steps']):
                if self.path(rid).with_suffix('.cancel').exists():r['status']='cancelled';break
                if self.path(rid).with_suffix('.pause').exists():r['status']='paused';break
                s=r['workflow']['steps'][r['index']];workflow_step.set({'run_id':rid,'step_id':s['id'],'cycle':r.get('cycle',1)});phase=r['pending']['phase'] if r['pending'] else None
                if s.get('enabled') is False:
                    r['steps'].append({'step_id':s['id'],'status':'skipped','cycle':r.get('cycle',1)});self._advance(r);
                    if r['status']=='paused':return r
                    continue
                if not r['pending'] and r.get('timed_step')!=(str(r.get('cycle',1))+':'+s['id']):
                    previous=r['workflow']['steps'][r['index']-1] if r['index'] else s
                    delay=max(0,min(30,s.get('recorded_at',0)-previous.get('recorded_at',0)))/r.get('speed',1)
                    deadline=time.monotonic()+delay
                    while time.monotonic()<deadline:
                        if self.path(rid).with_suffix('.cancel').exists() or self.path(rid).with_suffix('.pause').exists():break
                        time.sleep(min(.05,max(0,deadline-time.monotonic())))
                    r['timed_step']=str(r.get('cycle',1))+':'+s['id']
                    if self.path(rid).with_suffix('.cancel').exists() or self.path(rid).with_suffix('.pause').exists():continue
                if not r['pending'] and s.get('breakpoint') and r.get('breakpoint_seen')!=s['id']:
                    r.update(status='paused',breakpoint_seen=s['id'],pause_reason='breakpoint');self._save(r);return r
                if s['kind'] in {'native','input','wait','check'}:
                    alias=s['app']
                    if alias in r['bindings'] and not r['pending']:
                        scope=self.client.runtime._session(self.client.session_id)
                        pid=str(r['bindings'][alias]);expected=scope['bindings'].get(pid,{}).get('birth')
                        try:alive=self.client.runtime.birth_probe(int(pid))==expected
                        except (ValueError,OSError):alive=False
                        if not alive:
                            del r['bindings'][alias];r['window_bindings']={k:v for k,v in r.get('window_bindings',{}).items() if not k.startswith(alias+':')};self._save(r)
                    if alias not in r['bindings']:
                        result=self._call(r,'desktop.launch',{'app':alias,**({'background':True} if r['mode']=='headless' else {})},'launch')
                        if result is None:return r
                        r['bindings'][alias]=result['result']['pid'];self._save(r)
                        r['pending']=None;self._save(r)
                    if phase=='launch':phase=None
                    if not r['pending']:
                        deadline=time.monotonic()+s.get('timeout',10)
                        while True:
                            try:
                                s=self._context_step(r,r['workflow']['steps'][r['index']])
                                observed,snapshot=runtime_snapshot(self.client,r['bindings'][alias],s['window'])
                                target=find_target(snapshot,s['target'],'__input__' if s['kind']!='native' else s['action'])
                                if s['target'].get('image'):
                                    from .visual_target import capture_match
                                    point,match=capture_match(self.client,r['bindings'][alias],s['window'],s['target']['image']);b=target['bounds'];s['target']['point']={'x':(point['x']-b['x'])/b['width'],'y':(point['y']-b['y'])/b['height']}
                                    r['last_image_match']=match
                                if s.get('wait') and not verify_conditions(snapshot,s['wait'])[0]:raise ValueError('Wait conditions not satisfied')
                                break
                            except Exception:
                                if time.monotonic()>=deadline:raise
                                time.sleep(.15)
                        args={'app':str(r['bindings'][alias]),'window':s['window'],'observation_id':observed['result']['observation_id'],'ref':target['ref'],'action':s.get('action','check'),**s.get('arguments',{})}
                        if r['mode']=='headless':args['background']=True
                    else:args=r['pending']['arguments']
                    if s['kind'] in {'wait','check'}:
                        self._verify(r,{**s,'verify':s.get('verify') or s.get('wait')}) if s.get('verify') or s.get('wait') else None;r['steps'].append({'step_id':s['id'],'status':'completed','verification':'passed','cycle':r.get('cycle',1)});self._advance(r);
                        if r['status']=='paused':return r
                        continue
                    if s['kind']=='input' and not r['pending']:
                        point=s['target'].get('point',{});args.update({k:point[k] for k in ['x','y'] if k in point})
                    result=self._call(r,'desktop.input' if s['kind']=='input' else 'desktop.act',args,'action')
                    if result=='refresh':continue
                    if result is None:return r
                    # A separate verification checkpoint prevents a crash here from replaying an already dispatched action.
                    r['verification_pending']={'step_id':s['id'],'operation_id':result['operation_id']};self._save(r)
                    if s.get('verify'):self._verify(r,s)
                else:
                    if r.get('job_id'):
                        result=self._wait_job(r)
                        if result is None:return r
                    else:
                        args=copy.deepcopy(s.get('arguments',{}))
                        if s['kind']=='browser.open':args['headless']=r['mode']=='headless'
                        result=self._call(r,s['kind'],args,'action')
                        if result is None:return r
                    if result['status']=='queued':
                        r['job_id']=result['result']['job_id'];self._save(r)
                        result=self._wait_job(r)
                        if result is None:return r
                    if r.get('job_id'):
                        if result.get('result',{}).get('status')!='completed':raise RuntimeError('Workflow code job failed or did not complete')
                        r.pop('job_id',None)
                action_id=r['pending']['operation_id'] if r['pending'] else result['operation_id']
                r['steps'].append({'step_id':s['id'],'operation_id':action_id,'status':'completed','verification':'passed' if s.get('verify') else 'not_configured','cycle':r.get('cycle',1)})
                self.client.runtime.store.emit('workflow.step_completed',session_id=self.client.session_id,operation_id=action_id,data={'run_id':rid,'workflow_sha256':r['workflow_sha256'],'step_id':s['id'],'step_index':r['index']})
                self._advance(r)
                if r['status']=='paused':return r
            if r['status']=='running':r['status']='completed'
        except Exception as e:
            if 'r' not in locals():raise
            r.update(status='failed',error={'type':type(e).__name__,'message':str(e)} )
        finally:
            if 'r' in locals():
                self._save(r);self.client.runtime.store.emit('workflow.checkpoint',session_id=self.client.session_id,data={'run_id':rid,'status':r['status'],'next_step':r['index']})
            workflow_step.reset(context_token)
            self.lock.release()
        return r
    def _context_step(self,r,source):
        context=source.get('window_context')
        if not context:return source
        s=copy.deepcopy(source);pid=r['bindings'][s['app']]
        response=self.client.call('desktop.windows',{'app':str(pid),'window':source['window']})
        if response['status']!='completed':raise ValueError(response)
        candidates=[n for n in response['result'] if n['role']==context.get('role','window') and (not context.get('class_name') or n.get('platform_data',{}).get('class_name')==context['class_name']) and (not context.get('subrole') or n.get('platform_data',{}).get('ax_subrole')==context['subrole'])]
        bindings=r.setdefault('window_bindings',{});key=s['app']+':'+context['key'];bound=bindings.get(key)
        exact=[n for n in candidates if window_identity(n)==bound['identity']] if bound and bound['pid']==pid else []
        if bound and not exact:raise ValueError('The bound window closed; rebind this workflow before continuing')
        if not bound:
            exact=[n for n in candidates if window_identity(n)==context.get('identity')] or [n for n in candidates if n['name']==source['window']]
            if not exact and len(candidates)==1:exact=candidates
        if len(exact)!=1:raise ValueError('Workflow window is unavailable or ambiguous; pick the intended window')
        window=exact[0];bindings[key]={'pid':pid,'identity':window_identity(window)}
        old=s['window'];s['window']=window['name']
        for ancestor in s.get('target',{}).get('ancestors',[]):
            if ancestor['role'] in {'window','dialog'} and ancestor['name']==old:ancestor['name']=s['window']
        if s.get('target',{}).get('role') in {'window','dialog'} and s['target'].get('name')==old:s['target']['name']=s['window']
        self._save(r);return s
    def _advance(self,r):
        r['index']+=1;r['pending']=None;r.pop('verification_pending',None);r.pop('breakpoint_seen',None)
        if r['index']==len(r['workflow']['steps']) and r.get('cycle',1)<r.get('repeat',1):r['cycle']+=1;r['index']=0
        if r.get('single') and r['index']<len(r['workflow']['steps']):r.update(status='paused',pause_reason='single_step')
        self._save(r)
    def _wait_job(self,r):
        while True:
            if self.path(r['id']).with_suffix('.cancel').exists():r['status']='cancelled';return None
            if self.path(r['id']).with_suffix('.pause').exists():r['status']='paused';return None
            response=self.client.call('job.get',{'job_id':r['job_id']})
            if response['status']!='completed' or response.get('result',{}).get('status') not in {'queued','running'}:return response
            time.sleep(.15)
    def _verify(self,r,s):
        deadline=time.monotonic()+s.get('timeout',10)
        while True:
            current=self._context_step(r,s)
            _,snapshot=runtime_snapshot(self.client,r['bindings'][s['app']],current['window'])
            if verify_conditions(snapshot,s['verify'])[0]:return
            if time.monotonic()>=deadline:raise ValueError('Step completion check did not match')
            time.sleep(.15)
