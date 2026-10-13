"""Human-recorded, versioned workflows executed exclusively through enterprise Runtime."""
from __future__ import annotations
import copy,json,re,threading,time
from contextlib import contextmanager
from pathlib import Path
from .audit import digest,identifier,summarize
from .workflow import save_json,selector_for,resolve,validate_checks
from .agent import verify_conditions

SCHEMA='bokkio.runtime-workflow.v1'
KINDS={'native','browser.open','browser.act','code.run'}

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
    if not isinstance(doc,dict) or doc.get('schema')!=SCHEMA:raise ValueError('Unsupported workflow schema')
    if set(doc)-{'schema','id','name','revision','parent_sha256','sha256','apps','steps','description','resources'}:raise ValueError('Unknown workflow fields')
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
        if not isinstance(s,dict) or s.get('kind') not in KINDS or set(s)-{'id','kind','app','window','target','action','arguments','verify','wait','timeout','label'}:raise ValueError('Invalid workflow step')
        if not isinstance(s.get('id'),str) or s['id'] in ids:raise ValueError('Steps need unique IDs')
        ids.add(s['id'])
        if type(s.get('timeout',10)) not in {int,float} or not 0<s.get('timeout',10)<=30:raise ValueError('Step timeout must be 0..30 seconds')
        args=s.get('arguments',{})
        if not isinstance(args,dict):raise ValueError('Step arguments must be an object')
        if s['kind']=='native':
            if s.get('app') not in doc['apps'] or not isinstance(s.get('window'),str) or not s['window']:raise ValueError('Native steps need an application and exact window')
            from .xa11y_backend import ACTION_METHODS
            if s.get('action') not in ACTION_METHODS:raise ValueError('Unsupported native action')
            target=s.get('target')
            if not isinstance(target,dict) or set(target)-{'ref','role','name','ancestors','fallback','identifier'} or not isinstance(target.get('role'),str) or not isinstance(target.get('ancestors'),list):raise ValueError('Native step needs a semantic selector')
            if 'name' not in target or target['name'] is not None and not isinstance(target['name'],str):raise ValueError('Invalid target name')
            if set(args)-{'value','expected_value','direction','amount'}:raise ValueError('Action arguments cannot override application or target bindings')
            for a in target['ancestors']:
                if not isinstance(a,dict) or set(a)!={'role','name'} or not isinstance(a['role'],str):raise ValueError('Invalid selector context')
            validate_checks(s.get('verify',[]));validate_checks(s.get('wait',[]))
            if not s.get('verify'):raise ValueError('Native steps need a completion check')
            from .tool_schema import validate
            validate('desktop.act',{'app':'0','observation_id':'0','ref':'0','action':s['action'],**args})
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
            value.update(schema=SCHEMA,revision=previous['revision']+1 if previous else 1,parent_sha256=previous['sha256'] if previous else None)
            value.pop('sha256',None);validate_document(value);value['sha256']=digest(value)
            save_json(folder/(str(value['revision'])+'.json'),value)
            save_json(folder/'head.json',{k:value[k] for k in ['id','name','revision','sha256']})
            return value
    def archive(self,wid,expected_sha):
        with self.lock,library_lock(self.root):
            value=self.get(wid)
            if expected_sha!=value['sha256']:raise ValueError('Workflow changed; reload before archiving')
            save_json(self.folder(wid)/'head.json',{**{k:value[k]for k in ['id','name','revision','sha256']},'archived':True})
    def revisions(self,wid):return sorted(int(p.stem) for p in self.folder(wid).glob('*.json') if p.stem.isdigit())


def runtime_snapshot(client,pid,window):
    r=client.call('desktop.observe',{'app':str(pid),'window':window,'max_nodes':2000,'max_bytes':2000000})
    if r['status']!='completed':raise RuntimeError(r)
    if r['result']['truncated']:raise ValueError('Target observation exceeded budget; narrow the window')
    return r,{'windows':r['result']['nodes']}


def find_target(snapshot,target,action):
    selector={k:v for k,v in target.items() if k!='identifier'};selector.setdefault('ref','recorded')
    if target.get('identifier'):
        # Narrow by identity first, retain parent nodes for ancestry checks.
        wanted=target['identifier'];nodes=snapshot['windows'];matches=[]
        for n in nodes:
            data=n.get('platform_data',{})
            if wanted in {data.get('ax_identifier'),data.get('automation_id')}:matches.append(n['ref'])
        if len(matches)!=1:raise ValueError('Recorded control identifier is missing or ambiguous')
        snapshot={'windows':[n if n['ref'] in matches else {**n,'actions':[]} for n in nodes]}
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
    def pause(self,rid):save_json(self.path(rid).with_suffix('.pause'),{'pause':True})
    def resume(self,rid):self.path(rid).with_suffix('.pause').unlink(missing_ok=True);return self.run(rid)
    def start(self,doc,mode='headed'):
        validate_document(doc)
        if not doc['steps']:raise ValueError('Add or record steps before running')
        if mode not in {'headed','headless'}:raise ValueError('Invalid replay mode')
        if mode=='headless' and any(s['kind']=='native' and s['action'] in {'type','select_text'} for s in doc['steps']):raise ValueError('Background desktop replay requires deterministic native value writes; replace type/select_text with set_value')
        rid=identifier();run={'id':rid,'workflow':copy.deepcopy(doc),'workflow_sha256':doc['sha256'],'session_id':self.client.session_id,'mode':mode,'status':'ready','index':0,'steps':[],'bindings':{},'pending':None}
        save_json(self.path(rid),run);return run
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
        try:
            r=self.load(rid)
            if r['session_id']!=self.client.session_id:raise ValueError('Resume requires the original live Runtime session')
            if r['status'] in {'completed','failed','completion_unknown','cancelled'}:return r
            r['status']='running';self._save(r)
            self.client.runtime.store.emit('workflow.resumed',session_id=self.client.session_id,data={'run_id':rid,'workflow_sha256':r['workflow_sha256'],'next_step':r['index']})
            while r['index']<len(r['workflow']['steps']):
                if self.path(rid).with_suffix('.cancel').exists():r['status']='cancelled';break
                if self.path(rid).with_suffix('.pause').exists():r['status']='paused';break
                s=r['workflow']['steps'][r['index']];phase=r['pending']['phase'] if r['pending'] else None
                if s['kind']=='native':
                    alias=s['app']
                    if alias in r['bindings'] and not r['pending']:
                        scope=self.client.runtime._session(self.client.session_id)
                        pid=str(r['bindings'][alias]);expected=scope['bindings'].get(pid,{}).get('birth')
                        try:alive=self.client.runtime.birth_probe(int(pid))==expected
                        except (ValueError,OSError):alive=False
                        if not alive:del r['bindings'][alias];self._save(r)
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
                                observed,snapshot=runtime_snapshot(self.client,r['bindings'][alias],s['window'])
                                target=find_target(snapshot,s['target'],s['action'])
                                if s.get('wait') and not verify_conditions(snapshot,s['wait'])[0]:raise ValueError('Wait conditions not satisfied')
                                break
                            except Exception:
                                if time.monotonic()>=deadline:raise
                                time.sleep(.15)
                        args={'app':str(r['bindings'][alias]),'window':s['window'],'observation_id':observed['result']['observation_id'],'ref':target['ref'],'action':s['action'],**s.get('arguments',{})}
                        if r['mode']=='headless':args['background']=True
                    else:args=r['pending']['arguments']
                    result=self._call(r,'desktop.act',args,'action')
                    if result=='refresh':continue
                    if result is None:return r
                    # A separate verification checkpoint prevents a crash here from replaying an already dispatched action.
                    r['verification_pending']={'step_id':s['id'],'operation_id':result['operation_id']};self._save(r)
                    self._verify(r,s)
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
                r['steps'].append({'step_id':s['id'],'operation_id':action_id,'status':'completed'})
                self.client.runtime.store.emit('workflow.step_completed',session_id=self.client.session_id,operation_id=action_id,data={'run_id':rid,'workflow_sha256':r['workflow_sha256'],'step_id':s['id'],'step_index':r['index']})
                r['index']+=1;r['pending']=None;r.pop('verification_pending',None);self._save(r)
            if r['status']=='running':r['status']='completed'
        except Exception as e:
            if 'r' not in locals():raise
            r.update(status='failed',error={'type':type(e).__name__,'message':str(e)} )
        finally:
            if 'r' in locals():
                self._save(r);self.client.runtime.store.emit('workflow.checkpoint',session_id=self.client.session_id,data={'run_id':rid,'status':r['status'],'next_step':r['index']})
            self.lock.release()
        return r
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
            _,snapshot=runtime_snapshot(self.client,r['bindings'][s['app']],s['window'])
            if verify_conditions(snapshot,s['verify'])[0]:return
            if time.monotonic()>=deadline:raise ValueError('Step completion check did not match')
            time.sleep(.15)
