"""Microsoft Office native pilot runner, with fail-closed input preflight."""
from __future__ import annotations

import copy
import ctypes as c
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import time

from .model import BokkioError
from .office_benchmark import TASKS,digest,evaluate,load_bundle
from .workflow import save_json


def input_environment():
    if sys.platform!='darwin':return {'ready':False,'reason':'This pilot adaptation targets macOS'}
    cg=c.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
    cf=c.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    ax=c.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
    cg.CGSessionCopyCurrentDictionary.restype=c.c_void_p
    cg.CGPreflightScreenCaptureAccess.restype=c.c_bool
    cg.CGPreflightPostEventAccess.restype=c.c_bool
    ax.AXIsProcessTrusted.restype=c.c_bool
    cf.CFDictionaryGetValue.argtypes=[c.c_void_p,c.c_void_p];cf.CFDictionaryGetValue.restype=c.c_void_p
    cf.CFStringCreateWithCString.argtypes=[c.c_void_p,c.c_char_p,c.c_uint];cf.CFStringCreateWithCString.restype=c.c_void_p
    cf.CFBooleanGetValue.argtypes=[c.c_void_p];cf.CFBooleanGetValue.restype=c.c_bool
    cf.CFRelease.argtypes=[c.c_void_p]
    session=cg.CGSessionCopyCurrentDictionary();locked=None
    if session:
        key=cf.CFStringCreateWithCString(None,b'CGSSessionScreenIsLocked',0x08000100)
        value=cf.CFDictionaryGetValue(session,key);locked=cf.CFBooleanGetValue(value) if value else False
        cf.CFRelease(key);cf.CFRelease(session)
    permissions={'ax':ax.AXIsProcessTrusted(),'capture':cg.CGPreflightScreenCaptureAccess(),'events':cg.CGPreflightPostEventAccess()}
    return {'ready':bool(session) and locked is False and all(permissions.values()),'session_available':bool(session),
            'session_locked':locked,'permissions':permissions,
            'reason':'interactive_session_unavailable' if not session or locked is not False else 'permissions_required' if not all(permissions.values()) else None}


def _load(workspace):
    root=Path(workspace).resolve();state=json.loads((root/'prepared.json').read_text(encoding='utf-8'))
    if state.get('schema')!='bokkio.office_pilot.v1' or state.get('revision')!='fbccd464f94fec9e284e139f97bf96d0b192f580':
        raise BokkioError('Unrecognized Office pilot preparation')
    bundle=Path(state['bundle']);load_bundle(bundle)
    if digest(bundle/'manifest.json')!=state['bundle_manifest_sha256']:
        raise BokkioError('Office task manifest changed after preparation')
    if len(state.get('tasks',[]))!=3 or {t['task_id'] for t in state['tasks']}!=set(TASKS):
        raise BokkioError('Prepared Office selection changed')
    for task in state['tasks']:
        spec=TASKS[task['task_id']];folder=root/task['task_id']/'desktop'
        if Path(task['desktop']).resolve()!=folder or Path(task['artifact']).resolve()!=folder/spec['file'] or task['app']!=spec['app'] or task['max_steps']!=15:
            raise BokkioError('Office task scope or budget changed')
        for name,record in task['initial_inputs'].items():
            source=Path(task['source']).resolve()
            base=root/task['task_id']
            candidate=folder/name if (folder/name).is_file() else base/name
            if Path(name).name!=name or not source.is_relative_to(base) or candidate.resolve()!=source or digest(candidate)!=record['sha256']:
                raise BokkioError('Office input changed before execution')
    return root,state


def _native_run(task,trace_path):
    import xa11y
    from .agent import DesktopAgent
    from .planner import OpenRouterPlanner
    from .jev import JevProvider
    from .xa11y_backend import Xa11yBackend
    from .selector import flatten
    from .macos_activation import activate_window
    file=Path(task['artifact']);app_name=task['app']
    # Opening reviewed synthetic inputs belongs to initialization and is
    # separately reported. No output is generated through file libraries.
    command=['/usr/bin/open','-a',app_name]
    command.append(task['source'])
    subprocess.run(command,check=True,timeout=20)
    app=xa11y.App.by_name(app_name,timeout=15)
    time.sleep(.5)
    stems={file.stem.casefold(),Path(task['source']).stem.casefold()}
    class ScopedOffice(Xa11yBackend):
        supports_stale_refresh=True
        def _app_tree(self,app,live=None):
            root=super()._app_tree(app,live)
            def prune(node,in_window=False):
                node=copy.deepcopy(node)
                role=node['role'];name=(node.get('name') or '').casefold()
                if 'recent' in name or '最近' in name:return None
                if role in {'window','dialog'}:
                    allowed=in_window or any(stem in name for stem in stems) or name in {'font','paragraph','format cells','save as','save','open','styles','new presentation','new slide','slide layout','layout'}
                    if not allowed:return None
                    in_window=True
                if node['parent'] is not None and role not in {'window','dialog','menu','menu_bar','menu_item'} and not in_window:
                    return None
                node['children']=[p for child in node.get('children',[]) if (p:=prune(child,in_window)) is not None]
                return node
            scoped=prune(root)
            if not any(n['role'] in {'window','dialog'} for n in flatten([scoped])):
                raise BokkioError('No authorized benchmark document/window is open; no private startup context is sent to models')
            for node in flatten([scoped]):
                if node['role']=='combo_box' and node['platform_data'].get('ax_value_settable') and 'AXConfirm' in node['platform_data'].get('ax_original_actions',[]):
                    node['platform_data']['value_submission']='set_value_commits_via_bound_visual_input'
            return scoped
        def visual_value_replace(self,app,node,scope,value):
            if scope['role']!='window' or not any(stem in (scope['name'] or '').casefold() for stem in stems):
                raise BokkioError('Office visual field input requires the authorized document window')
            from .office_visual import replace_combo
            return replace_combo(bound_pid,scope['name'],node,value,backend=self)
        def perform(self,app,action,**arguments):
            if not str(app).isdigit() or int(app)!=bound_pid:raise BokkioError('Office action app is outside the task binding')
            snapshot=self.snapshot(app,arguments.get('window'))
            nodes={n['ref']:n for n in flatten(snapshot['windows'])}
            ref=arguments.get('ref');name=(nodes.get(ref,{}).get('name') or '').casefold()
            if any(term in name for term in ['share','send','publish','共享','发送']):raise BokkioError('External communication is outside this Office pilot')
            return super().perform(app,action,**arguments)
    bound_pid=app.pid
    backend=ScopedOffice()
    # Preflight precedes provider construction: inaccessible UI incurs no model
    # calls and is an environment result, not a model/task failure.
    backend.snapshot(str(bound_pid))
    owned_windows=[w for w in app.windows() if any(stem in (w.name or '').casefold() for stem in stems)]
    if len(owned_windows)!=1:raise BokkioError('Benchmark initialization requires one exact document window')
    activate_window(bound_pid,owned_windows[0].name)
    started=time.time_ns()
    def verify_artifact(trace):
        score=evaluate(task['task_id'],file)
        score['saved_after_start']=file.is_file() and file.stat().st_mtime_ns>started
        return score['passed'] and score['saved_after_start'], {'artifact':str(file),'score':score}
    agent=DesktopAgent(backend,OpenRouterPlanner(),JevProvider(),max_actions=15,max_replans=1,max_phases=8,final_verifier=verify_artifact)
    return agent.run(task['goal'],[str(bound_pid)],trace_path)


def run(workspace,*,environment=None,executor=None):
    root,state=_load(workspace);report_path=root/'run.json'
    if report_path.exists():raise BokkioError('Office run already exists; prepare a fresh workspace')
    environment=input_environment if environment is None else environment
    executor=_native_run if executor is None else executor
    env=environment()
    apps={}
    for spec in TASKS.values():
        plist=Path('/Applications')/(spec['app']+'.app')/'Contents/Info.plist'
        apps[spec['app']]={'installed':plist.is_file()}
        if plist.is_file():apps[spec['app']]['version']=plistlib.loads(plist.read_bytes()).get('CFBundleShortVersionString')
    report={'schema':'bokkio.office_pilot_run.v1','revision':state['revision'],'scope':state['scope'],
            'environment':env,'applications':apps,'planned':3,'started':0,'tasks':[],
            'official_score':False,'judge_status':'upstream_rubric_pinned_not_official_VLM_execution',
            'started_at_unix_ns':time.time_ns(),'setup_input_open_is_not_agent_action':True}
    if not env['ready']:
        report.update(status='blocked',blocked=3)
        report['tasks']=[{'task_id':t['task_id'],'status':'not_started','reason':env['reason'],'score':None} for t in state['tasks']]
        save_json(report_path,report);return report
    save_json(report_path,{**report,'status':'running'})
    for task in state['tasks']:
        if not environment()['ready']:
            report['tasks'].append({'task_id':task['task_id'],'status':'not_started','reason':'input_session_changed','score':None});continue
        report['started']+=1;started=time.time_ns();trace_path=root/task['task_id']/'agent.json'
        try:
            trace=executor(task,trace_path)
            row={'task_id':task['task_id'],'execution_status':trace['status'],'actions':trace.get('actions'),
                 'status':'executed','trace':str(trace_path.relative_to(root))}
        except Exception as error:
            row={'task_id':task['task_id'],'status':'environment_or_execution_error','reason':str(error),'score':None}
        if row['status']=='executed':
            score=evaluate(task['task_id'],task['artifact'])
            file=Path(task['artifact']);persisted_change=file.is_file() and file.stat().st_mtime_ns>started
            # The initial Word/Excel content must not be mistaken for a saved
            # solution merely because it already exists in the setup folder.
            score['saved_after_start']=persisted_change;score['passed']=score['passed'] and persisted_change
            row['score']=score
        report['tasks'].append(row);save_json(report_path,{**report,'status':'running'})
    report.update(status='completed' if report['started']==3 and all(t['status']=='executed' for t in report['tasks']) else 'incomplete',
                  passed=sum(bool(t.get('score') and t['score']['passed']) for t in report['tasks']))
    save_json(report_path,report);return report
