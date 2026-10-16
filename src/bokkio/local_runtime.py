"""Same-user desktop execution; explicit enterprise policy remains separate."""
from pathlib import Path
import json, os
from .runtime import Runtime
from .audit import canonical

class LocalRuntime(Runtime):
    def __init__(self,state_dir,backend=None,birth_probe=None):
        roots=[str(Path('/').resolve())] if os.name!='nt' else [chr(c)+':\\' for c in range(65,91) if Path(chr(c)+':\\').exists()]
        super().__init__(state_dir,{'apps':[],'paths':roots,'origins':[],'write':True,'trusted_host':True,'require_approval':False,'ttl':86400,'launch_apps':{},'modules':['office.xlsx'],'outlook':True},backend,birth_probe)
    def call(self,tool,args=None,session_id=None,operation_id=None):
        args=args or {}
        task_id=os.environ.get('BOKKIO_DESKTOP_TASK_ID')
        if tool=='session.open' and task_id and (self.store.root/'task-cancellations'/task_id).is_file():
            self.store.emit('desktop.task.blocked',data={'task_id':task_id,'dispatched':False})
            return {'status':'denied','session_id':None,'operation_id':operation_id,'error':'Task has been stopped','dispatched':False}
        if tool=='session.open' and os.environ.get('BOKKIO_DESKTOP_TASK_ID'):args={**args,'task_id':os.environ['BOKKIO_DESKTOP_TASK_ID']}
        if tool=='session.open' or session_id:
            native=tool.startswith(('desktop.','workflow.')) or tool=='session.open' and bool(args.get('apps'))
            rows=self._native_call('apps') if native else []
            if native:self.policy['apps']=[str(a['pid']) for a in rows]+[a['name'] for a in rows]+[a['name'] for a in self.policy.get('launch_apps',{}).values()]
            if tool=='session.open' and 'apps' not in args:args={**args,'apps':[]}
            if tool=='session.open' and isinstance(args.get('apps'),list):
                names={a['name'].casefold():a['name'] for a in rows}
                args={**args,'apps':[names.get(value.casefold(),value) if isinstance(value,str) else value for value in args['apps']]}
            if session_id:
                scope=self._session(session_id)
                # Bind new explicitly addressed processes; never replace an existing birth identity.
                for a in rows:
                    pid=str(a['pid'])
                    if pid not in scope['bindings']:
                        try:scope['bindings'][pid]={'name':a['name'],'birth':self.birth_probe(a['pid']),'windows':[]}
                        except (OSError,ValueError):continue
                if tool in {'browser.open','browser.act'}:
                    from .browser_driver import origin
                    url=args.get('url') or args.get('expected_url')
                    if url:
                        value=origin(url)
                        if value not in scope['origins']:scope['origins'].append(value)
                self.policy['origins']=scope['origins']
                if tool=='workflow.run':
                    from .runtime_workflow import WorkflowLibrary
                    doc=WorkflowLibrary(self.store.root/'workflows').get(args['workflow_id'])
                    self.policy['launch_apps'].update(doc['apps'])
                    self.policy['apps']+= [a['name'] for a in doc['apps'].values()]
                    scope['launch_apps']=self.policy['launch_apps']
                self.policy['workflows']=[p.parent.name for p in (self.store.root/'workflows').glob('*/head.json')]
                scope['workflows']=self.policy['workflows']
                with self.store.connect() as db:db.execute('UPDATE sessions SET policy=? WHERE id=?',(canonical(scope),session_id))
        return super().call(tool,args,session_id=session_id,operation_id=operation_id)
